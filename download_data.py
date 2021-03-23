#
# Download result files from s3 to specified directory.
# Already exists local file is ignore.
#
# How to use:
#    $ python3 download_data.py /var/tmp/path-to-dir example-backet-name prefix/
#
# Example:
#    $ python3 download_data.py /var/tmp/phoronix example-backet-name phoronix/
#    $ python3 download_data.py /var/tmp/openssl  example-backet-name openssl/
#
import boto3
import os
import sys

#
# option
#
DATA_DIR  = sys.argv[1] if len(sys.argv) >= 2 else None
S3_BUCKET = sys.argv[2] if len(sys.argv) >= 3 else None
S3_PREFIX = sys.argv[3] if len(sys.argv) >= 4 else None
if S3_PREFIX[-1] != '/':
    S3_PREFIX += '/'

#
# List instance types
#
s3 = boto3.client('s3')
params = {
    "Bucket": S3_BUCKET,
    "Prefix": S3_PREFIX,
    "Delimiter": "/",
}
res = s3.list_objects_v2(**params)
prefixes = res.get("CommonPrefixes")
if not prefixes:
    print("Not found objects")
    quit()

instance_type_prefixes = [y["Prefix"] for y in sorted(prefixes, key=lambda x:x['Prefix'])]

#
# List files
#
instance_types = {}
for instance_type_prefix in instance_type_prefixes:
    instance_type = os.path.basename(os.path.dirname(instance_type_prefix))
    params = {
        "Bucket": S3_BUCKET,
        "Prefix": instance_type_prefix,
    }
    res = s3.list_objects_v2(**params)
    files = [y["Key"] for y in sorted(res['Contents'], key=lambda x:x['Key'])]

    instance_types[instance_type] = files

#
# Download files
#
for instance_type,files in list(instance_types.items()):
    save_dir  = "%s/%s" % (DATA_DIR, instance_type)

    for file_key in files:
        file_name = os.path.basename(file_key)
        save_file = "%s/%s" % (save_dir, file_name)

        if os.path.exists(save_file):
            print("Already exists %s" % save_file)
            continue

        os.makedirs(save_dir, exist_ok=True)
        print("s3://%s/%s saved to %s" % (S3_BUCKET, file_key, save_file))
        with open(save_file, 'wb') as data:
            s3.download_fileobj(S3_BUCKET, file_key, data)

