#
# Organize result data.
#
import boto3
import os
import sys
import re

DATA_DIR  = "/var/tmp/phoronix"
DATA_FILE = "/var/tmp/phoronix.result"

LESS_BETTER_UNITS = [
    "sec", "Seconds", "ms", "Milliseconds", "ns", "Nanoseconds",
    "Nanoseconds/Operation", "Encode Time",
]

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

pattern_average = r' +Average: ([\d.]+) ([^\n]+)'

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

    type_results = {}
    for instance_type,log_file in list(type_files.items()):
        f = open(log_file, "r")
        log = f.read()
        f.close()

        match = re.search(pattern_average, log, re.S)
        if not match:
            print("%s: Not found Average" % (log_file))
            break

        type_results[instance_type] = {
            "value": float(match.group(1)),
            "unit" : match.group(2)
        }

    if len(type_results) < type_count:
        continue

    test_name          = os.path.splitext(file_name)[0].replace('_', '/')
    results[test_name] = type_results

#
# Output result
#
output = "Name\tUnit\tBetter"

for instance_type in instance_types:
    output += "\t%s" % instance_type

output += "\n"
for test_name,type_results in list(results.items()):
    unit    = type_results[main_type]["unit"]
    better  = "less" if unit in LESS_BETTER_UNITS else "more"
    output += "%s\t%s\t%s" % (test_name, unit, better)

    for instance_type,type_result in list(type_results.items()):
        output += "\t%s" % type_result["value"]

    output += "\n"

f = open(DATA_FILE, "w")
f.write(output)
f.close()

print("Output to %s" % DATA_FILE)
