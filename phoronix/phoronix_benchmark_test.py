#
# Benchmark test, and save result to s3.
#
# How to use:
#    $ python3 this.py pts/example-test c6g.2xlarge example-bucket-name example-prefix
#
# Reason why specify instance type:
#    When you launch instances in succession,
#    metadata may return incorrect instance type.
#
import boto3
import os
import sys
import re
import json
import requests
import pexpect

TOP_DIR     = "/opt/phoronix"
BIN_DIR     = "%s/bin" % TOP_DIR
LOG_DIR     = "%s/log" % TOP_DIR
PHORONIX    = "%s/phoronix-test-suite" % BIN_DIR

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

#
# option
#
BENCHMARK_NAME = sys.argv[1] if len(sys.argv) >= 2 else None
INSTANCE_TYPE  = sys.argv[2] if len(sys.argv) >= 3 else None
S3_BUCKET      = sys.argv[3] if len(sys.argv) >= 4 else None
S3_PREFIX      = sys.argv[4] if len(sys.argv) >= 5 else None

S3_KEY = "%s/%s/%s.log" % (S3_PREFIX, INSTANCE_TYPE, BENCHMARK_NAME.replace('/', '_'))
S3_URL = "s3://%s/%s" % (S3_BUCKET, S3_KEY)
print("Log will be saved to %s" % S3_URL)

#
# check exist data
#
s3 = boto3.client('s3')
res = s3.list_objects_v2(
    Bucket = S3_BUCKET,
    Prefix = S3_KEY,
)
if 'Contents' in res:
    print("Already exists data %s" % S3_URL)
    quit()

#
# Benchmark test
#
command = "%s benchmark %s" % (PHORONIX, BENCHMARK_NAME)
pattern_question = r'\n + ([^@\+\n]+\D:) ?[^ \n]*$'
pattern_last     = r'\(Y/n\)'
pattern_select   = r' 1: '

print("Execute: %s" % command)
print()

p = pexpect.spawn(command, timeout=None)
while True:
    p.expect(pattern_question)
    question = ansi_escape.sub('', p.match.group(1).decode('utf-8'))
    print("Question: %s" % question)

    if not re.search(pattern_last, question):
        stdout = ansi_escape.sub('', p.before.decode('utf-8'))
        if not re.search(pattern_select, stdout):
            print("Not found number select, exit it")
            quit()

        print("Answer: 1")
        p.sendline('1')
        continue

    print("Found Y/n")
    break

print("Answer: n")
p.sendline('n')
res = ansi_escape.sub('', p.read().decode('utf-8'))
p.expect(pexpect.EOF, timeout=None)
p.close()
print("Finish: %s" % command)

s3.put_object(
    Bucket      = S3_BUCKET,
    Key         = S3_KEY,
    Body        = res,
    ContentType = 'text/plain',
    ACL         = 'bucket-owner-full-control',
)
print("Save result to %s" % (S3_URL))

