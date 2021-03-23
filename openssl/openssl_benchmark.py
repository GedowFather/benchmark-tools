#
# Benchmark all tests, and save result to s3.
#
# How to use:
#    $ python3 this.py example-bucket-name example-prefix
#
import boto3
import sys
import requests
import subprocess

#
# Config
#
EVPS = [
    'md4', 'md5', 'sha1', 'sha256', 'sha512',
    'idea-cbc', 'seed-cbc', 'rc2-cbc', 'rc5-cbc', 'bf-cbc',
    'des-cbc', 'des-ede3',
    'aes-128-cbc', 'aes-192-cbc', 'aes-256-cbc',
    'aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm',
    'camellia-128-cbc', 'camellia-192-cbc', 'rc4',
]

MULTIS = ["1", "2", "4", "8"]

#
# option
#
S3_BUCKET = sys.argv[1] if len(sys.argv) >= 2 else None
S3_PREFIX = sys.argv[2] if len(sys.argv) >= 3 else None

#
# Metadata
#
METADATA_BASE_URL = "http://169.254.169.254/latest/meta-data"

INSTANCE_TYPE_URL = "%s/instance-type" % (METADATA_BASE_URL)
res = requests.get(INSTANCE_TYPE_URL)
INSTANCE_TYPE = res.text

#
# Execute
#
s3 = boto3.client('s3')

for evp in EVPS:
    for endecrypt in ['encrypt', 'decrypt']:
        for multi in MULTIS:
            s3_key = "%s/%s/%s_%s_%s.log" % (S3_PREFIX, INSTANCE_TYPE, evp, endecrypt, multi)
            s3_url =  "s3://%s/%s" % (S3_BUCKET, s3_key)
            res = s3.list_objects_v2(
                Bucket = S3_BUCKET,
                Prefix = s3_key,
            )
            if 'Contents' in res:
                print("Already exists data %s" % s3_url)
                continue

            command = ["openssl", "speed", "-elapsed", "-evp", evp, "-multi", multi]
            if endecrypt == "decrypt":
                command.append("-decrypt")

            res     = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result  = res.stdout.decode('utf-8')

            s3.put_object(
                Bucket      = S3_BUCKET,
                Key         = s3_key,
                Body        = result,
                ContentType = 'text/plain',
                ACL         = 'bucket-owner-full-control',
            )
            print("Save result to s3://%s/%s" % (S3_BUCKET, s3_key))

print("Finished")

