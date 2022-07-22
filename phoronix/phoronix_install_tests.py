#
# Install based on JSON data.
#
# You can specify a test name or upper limit to ignore.
#
import os
import re
import json
import subprocess
from datetime import datetime, timedelta, timezone

TOP_DIR       = "/opt/phoronix"
BIN_DIR       = "%s/bin" % TOP_DIR
LOG_DIR       = "%s/log" % TOP_DIR
PHORONIX      = "%s/phoronix-test-suite" % BIN_DIR

INFO_LOG_FILE      = "%s/info.json" % LOG_DIR
INSTALL_CACHE_FILE = "%s/install.json" % LOG_DIR

DOWNLOAD_LOWER_LIMIT = 2000
DISK_LOWER_LIMIT     = 5000
TIME_LOWER_LIMIT     = 1800

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
JST         = timezone(timedelta(hours=+9), 'JST')

IGNORE_TESTS = [
    'pts/perl-benchmark', 'pts/qmlbench', 'system/blender', 'system/mpv',
    'pts/brl-cad', 'pts/onednn', 'pts/blender', 'pts/build-wasmer', 'pts/intel-mlc',
    'pts/onnx', 'pts/clickhouse', 'pts/ecp-candle', 'pts/hammerdb-mariadb',
    'pts/spec-cpu2017', 'pts/gnupg', 'pts/perf-bench', 'pts/pgbench', 'pts/pjsip',
    'pts/quantlib', 'pts/redis', 'pts/redshift', 'pts/renaissance', 'pts/rust-mandel', 'pts/rust-prime',
    'pts/sockperf', 'pts/sqlite', 'pts/sqlite-speedtest', 'pts/tensorflow-lite', 'pts/tnn', 'pts/toktx',
    'pts/tungsten',
    'system/apache', 'system/compress-zstd', 'system/gnupg', 'system/libreoffice', 'system/nginx',
]

#
# filter tests
#
f = open(INFO_LOG_FILE, "r")
info = json.loads(f.read())
f.close()

for name in IGNORE_TESTS:
        del info[name]

install_tests = []
giveup_tests  = []
for name,values in list(info.items()):
    download_size = values['download']
    disk_size     = values['disk']
    time          = values['time']
    if download_size > DOWNLOAD_LOWER_LIMIT or disk_size > DISK_LOWER_LIMIT or time > TIME_LOWER_LIMIT:
        giveup_tests.append(name)
    else:
        install_tests.append(name)

if giveup_tests:
    print("Give up installing tests.")
for name in giveup_tests:
    print("    %s: download = %s MB, disk = %s MB, time = %s seconds" % (name, info[name]['download'], info[name]['disk'], info[name]['time']))
if giveup_tests:
    print()

download_total = 0
disk_total     = 0
time_total     = 0
for name in install_tests:
    download_total += info[name]['download']
    disk_total     += info[name]['disk']
    time_total     += info[name]['time']

print("Total info")
print("    download: %s MB" % download_total)
print("    disk: %s MB" % disk_total)
print("    time: %s Seconds" % time_total)
print()

#
# Install tests
#
print("Install tests")
command       = "install"
pattern_error = r"  ERROR: ([^\n]+)\n"
pattern_log   = r"  LOG: ([^\n]+)\n"

install_cache = {}
if os.path.isfile(INSTALL_CACHE_FILE):
    f = open(INSTALL_CACHE_FILE, "r")
    install_cache = json.loads(f.read())
    f.close()

for name in install_tests:
    if name in install_cache:
        state = install_cache[name]['state']
        log   = install_cache[name]['log']
        if state == 'error':
            print("    (cache) %s: Error log is %s" % (name, log))
        else:
            print("    (cache) %s: Installed" % name)
        continue

    download_size = info[name]['download']
    disk_size     = info[name]['disk']
    time          = info[name]['time']

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    print("    %s %s: download = %s MB, disk = %s MB, time = %s seconds" % (now, name, download_size, disk_size, time))
    res    = subprocess.run([PHORONIX, command, name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = ansi_escape.sub('', res.stdout.decode('utf-8'))

    match = re.search(pattern_error, result, re.S)
    error = match.group(1) if match else None

    match = re.search(pattern_log, result, re.S)
    log   = match.group(1) if match else None

    state = 'error' if error else 'installed'
    if state == 'error':
        print("    (result) %s: Error log is %s" % (name, log))
    else:
        print("    (result) %s: Installed" % name)

    install_cache[name] = {
        'state': state,
        'log'  : log,
    }
    f = open(INSTALL_CACHE_FILE, "w")
    f.write(json.dumps(install_cache))
    f.close()

print("Finished install tests")

