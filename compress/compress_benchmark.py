#
# Benchmark all tests, and save result to s3.
#
# 1. Install packages
#    $ amazon-linux-extras install epel -y
#    $ yum -y install pigz pbzip2 pxz
#
# 2. create 1GB file
#    $ base64 /dev/urandom | head -c 1024m > /var/tmp/1gb.data
#
# 3. python3 this.py s3-bucket-name s3-prefix
#
import boto3
import sys
import time
import requests
import subprocess

#
# Config
#
COMPRESSES= {
    "pigz"     : "pigz -c%s -p%s %s",
    "pigz zlib": "pigz -z -c%s -p%s %s",
    "pbzip2"   : "pbzip2 -c%s -p%s %s",
    "pxz"      : "pxz -c%s -T%s %s",
}
MULTIS = ["1", "2", "4", "8"]

SOURCE_FILE = "/var/tmp/1gb.data"
OUTPUT_FILE = "/var/tmp/output.compressed"

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

for test_name,command_string in list(COMPRESSES.items()):
    for multi in MULTIS:
        for endecompress in ['compress', 'decompress']:
            s3_key = "%s/%s/%s_%s_%s.log" % (S3_PREFIX, INSTANCE_TYPE, test_name, endecompress, multi)
            s3_url =  "s3://%s/%s" % (S3_BUCKET, s3_key)
            res = s3.list_objects_v2(
                Bucket = S3_BUCKET,
                Prefix = s3_key,
            )
            if 'Contents' in res:
                print("Already exists data %s" % s3_url)
                continue

            if endecompress == 'compress':
                decompress = ""
                use_file   = SOURCE_FILE
            else:
                decompress = "d"
                use_file   = OUTPUT_FILE

            dst_file = '/dev/null'
            replace  = command_string % (decompress, multi, use_file)
            command  = replace.split()
            start    = time.time()
            with open(dst_file, 'w') as f:
                subprocess.run(command, stdout=f, stderr=subprocess.PIPE)
            command_time = str(round(time.time() - start, 2))
            print("Execute (%ss): %s > %s" % (command_time, ' '.join(command), dst_file))

            s3.put_object(
                Bucket      = S3_BUCKET,
                Key         = s3_key,
                Body        = command_time,
                ContentType = 'text/plain',
                ACL         = 'bucket-owner-full-control',
            )
            print("Save result to s3://%s/%s" % (S3_BUCKET, s3_key))

            # file for decompress #
            if endecompress == 'compress':
                print("Make compress file to %s" % OUTPUT_FILE)
                with open(OUTPUT_FILE, 'w') as f:
                    subprocess.run(command, stdout=f, stderr=subprocess.PIPE)

print("Finished")

