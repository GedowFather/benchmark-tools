#
# Organize result data.
#
import boto3
import os
import sys
import re

DATA_DIR  = "/var/tmp/compress"
DATA_FILE = "/var/tmp/compress.result"

#
# list instance types and files
#
log_files = {}
for instance_type in sorted(os.listdir(DATA_DIR)):
    log_files[instance_type] = []
    instance_data_dir        = "%s/%s" % (DATA_DIR, instance_type)

    for file_name in sorted(os.listdir(instance_data_dir)):
        log_files[instance_type].append(file_name)

#
# Read result
#
results        = {}
instance_types = list(log_files.keys())
type_count     = len(instance_types)
main_type      = instance_types[0]
other_types    = [i for i in instance_types if i != main_type]

for file_name in log_files[main_type]:
    type_files = {}
    for instance_type in [main_type] + other_types:
        type_files[instance_type] = "%s/%s/%s" % (DATA_DIR, instance_type, file_name)

    all_file_exists = True
    for instance_type,log_file in list(type_files.items()):
        if not os.path.exists(log_file):
            all_file_exists = False
            print("%s: Not found %s" % (file_name, log_file))
            break

    if not all_file_exists:
        continue

    print("%s: All log exists" % file_name)

    log_name       = os.path.splitext(file_name)[0]
    log_name_split = log_name.split("_")
    test_name      = log_name_split[0]
    endecompress   = log_name_split[1]
    multi          = log_name_split[2]

    type_results   = {}
    for instance_type,log_file in list(type_files.items()):
        f = open(log_file, "r")
        log = f.read()
        f.close()

        type_results[instance_type] = float(log)

    if len(type_results) < type_count:
        continue

    if test_name not in results: results[test_name] = {'compress': {}, 'decompress': {}}
    results[test_name][endecompress][multi] = type_results

#
# Output result
#
output = "Name\t(de)compress\tMulti"

for instance_type in instance_types:
    output += "\t%s" % instance_type

output += "\n"
prev_test_name    = ""
prev_endecompress = ""

for test_name,endecompresss in list(results.items()):
    for endecompress,multis in list(endecompresss.items()):
        multis_sorted = {k:multis[k] for k in sorted(multis, key=int)}
        for multi,type_results in list(multis_sorted.items()):
            output_test_name    = test_name    if test_name != prev_test_name else ""
            output_endecompress = endecompress if endecompress != prev_endecompress else ""
            output += "%s\t%s\t%s" % (output_test_name, output_endecompress, multi)

            for instance_type,value in list(type_results.items()):
                output += "\t%s" % value

            output += "\n"
            prev_test_name    = test_name
            prev_endecompress = endecompress

f = open(DATA_FILE, "w")
f.write(output)
f.close()

print("Output to %s" % DATA_FILE)
