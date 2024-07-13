#
# Run the tests on separate instances.
#
# How to use:
#    $ python3 this.py $ami_id $instance_type $partitioning_num $s3_bucket $s3_prefix
#
import boto3
import os
import sys
import re
import json
import requests
import subprocess

TOP_DIR   = "/opt/phoronix"
BIN_DIR   = "%s/bin" % TOP_DIR
PHORONIX  = "%s/phoronix-test-suite" % BIN_DIR
BENCHMARK = "%s/phoronix_benchmark_test.py" % BIN_DIR

VOLUME_SIZE = 60

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

#
# option
#
AMI_ID        = sys.argv[1]      if len(sys.argv) >= 2 else None
INSTANCE_TYPE = sys.argv[2]      if len(sys.argv) >= 3 else None
PARTITIONED   = int(sys.argv[3]) if len(sys.argv) >= 4 else None
S3_BUCKET     = sys.argv[4]      if len(sys.argv) >= 5 else None
S3_PREFIX     = sys.argv[5]      if len(sys.argv) >= 6 else None

if S3_PREFIX is None:
    print("Input S3_BUCKET and S3_PREFIX")
    quit()

#
# metadata
#
METADATA_BASE_URL = "http://169.254.169.254/latest"

TOKEN_URL = "%s/api/token" % (METADATA_BASE_URL)
headers   = {'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
res       = requests.put(TOKEN_URL, data=None, headers=headers)
TOKEN     = res.text

AZ_URL    = "%s/meta-data/placement/availability-zone" % (METADATA_BASE_URL)
headers   = {'X-aws-ec2-metadata-token': TOKEN}
res       = requests.get(AZ_URL, headers=headers)
REGION    = res.text[:-1]

PROFILE_INFO_URL = "%s/iam/info" % (METADATA_BASE_URL)
res = requests.get(PROFILE_INFO_URL)
PROFILE_INFO = json.loads(res.text)
PROFILE_ARN  = PROFILE_INFO['InstanceProfileArn']

MACS_URL = "%s/network/interfaces/macs" % (METADATA_BASE_URL)
res = requests.get(MACS_URL)
MAC = res.text
MAC_URL = "%s/%s" % (MACS_URL, MAC)
SUBNET_ID_URL = "%ssubnet-id" % (MAC_URL)
res       = requests.get(SUBNET_ID_URL)
SUBNET_ID = res.text

SECURITY_GROUP_IDS_URL = "%ssecurity-group-ids" % (MAC_URL)
res = requests.get(SECURITY_GROUP_IDS_URL)
SECURITY_GROUP_IDS = res.text.split("\n")

#
# list installed
#
command = "list-installed-tests"
res     = subprocess.run([PHORONIX, command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result  = ansi_escape.sub('', res.stdout.decode('utf-8'))
pattern = r'^([a-z]+/.+)-([\d\.]+) .*$'

installeds = []
for match in re.finditer(pattern, result, re.MULTILINE):
    name    = match.group(1)
    version = match.group(2)
    installeds.append(name)

print("Installed tests is %s" % len(installeds))

#
# part tests
#
parted_tests = [installeds[i:i+PARTITIONED] for i in range(0, len(installeds), PARTITIONED)]
print("Partitioned tests is %s" % len(parted_tests))

ec2 = boto3.client('ec2', region_name=REGION)

parted_count = 0
for tests in parted_tests:
    parted_count += 1
    user_data = "#!/bin/bash\n"
    for name in tests:
        user_data += "python3 %s %s %s %s %s\n" % (BENCHMARK, name, INSTANCE_TYPE, S3_BUCKET, S3_PREFIX)

    name_tag   = "%s-%s" % (INSTANCE_TYPE, parted_count)
    user_data += "shutdown -h now\n"
    params = {
        "ImageId"     : AMI_ID,
        "MinCount"    : 1,
        "MaxCount"    : 1,
        "InstanceType": INSTANCE_TYPE,
        "UserData"    : user_data,
        "SubnetId"    : SUBNET_ID,
        "SecurityGroupIds": SECURITY_GROUP_IDS,
        "BlockDeviceMappings": [{
            "DeviceName":"/dev/xvda",
            "Ebs": {
                "VolumeSize"         : VOLUME_SIZE,
                "VolumeType"         : "gp2",
                "DeleteOnTermination": True,
            },
        }],
        "InstanceMarketOptions": {
            'MarketType'      : 'spot',
            'SpotOptions': {
                'SpotInstanceType': 'one-time',
                'InstanceInterruptionBehavior': 'terminate',
            },
        },
        "IamInstanceProfile": {'Arn': PROFILE_ARN},
        "InstanceInitiatedShutdownBehavior": 'terminate',
        "TagSpecifications": [{
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name', 'Value': name_tag},
            ],
        }],
    }
    print("Run %s" % INSTANCE_TYPE)
    print("UserData:")
    print(user_data)
    print()
    ec2.run_instances(**params)

print("Finish")
