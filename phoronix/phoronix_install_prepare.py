#
# Determine which package you need,
# and the test to install.
#
# First run once,
# check the list of packages to install.
#
# After installing those packages,
# run again,
# save test list that are determined to be installed in JSON.
#
# You will need these packages:
# (about 2.1GB)
#
#   yum install \
#       cmake vulkan-devel gmp-devel boost-devel taglib-devel snappy-devel opencv-devel \
#       libxml2-devel blas-devel swig patch pcre-devel maven nasm libaio-devel libtool \
#       gcc perl-Digest-MD5 libevent-devel ncurses-devel numactl-devel blas SDL2 \
#       qt5-qtbase-devel boost-thread atlas-devel autoconf flex make SDL-devel \
#       openmpi-devel libvorbis-devel git ruby gcc-c++ httpd libpng-devel uuid-devel expat \
#       suitesparse-devel popt-devel smartmontools libuuid-devel openssl-devel \
#       freeglut-devel libtiff-devel golang gcc-gfortran expat-devel openmpi freetype-devel \
#       automake bzip2-devel bison SDL2-devel lapack-devel
#
import os
import re
import math
import json
import subprocess

TOP_DIR       = "/opt/phoronix"
BIN_DIR       = "%s/bin" % TOP_DIR
LOG_DIR       = "%s/log" % TOP_DIR
PHORONIX      = "%s/phoronix-test-suite" % BIN_DIR
INFO_LOG_FILE = "%s/info.json" % LOG_DIR

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

#
# unsuppported
#
command = "list-unsupported-tests"
res     = subprocess.run([PHORONIX, command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result  = ansi_escape.sub('', res.stdout.decode('utf-8'))
pattern = r'^.* ([a-z]+/.+)-([\d\.]+) .*$'

unsupported = {}
for match in re.finditer(pattern, result, re.MULTILINE):
    name    = match.group(1)
    version = match.group(2)
    unsupported[name] = version

#
# supported
#
command = "list-all-tests"
res     = subprocess.run([PHORONIX, command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result  = ansi_escape.sub('', res.stdout.decode('utf-8'))
pattern = r'^([a-z]+/[^ ]+) .*$'

supported = {}
for match in re.finditer(pattern, result, re.MULTILINE):
    name = match.group(1)
    if name in unsupported: continue
    supported[name] = {
        'packages': [],
        'download': 0,
        'disk'    : 0,
        'time'    : 0,
    }

#
# yum needed
#
yum_needs = []
count = 0

command = "install"
pattern_packages = r'^- (.+)$'
pattern_download = r'To Download \[([\d.]+)(\w+)\]'
pattern_disk     = r' (\d+)(\w+) Of Disk Space Is Needed'
pattern_time     = r' ((\d+) Minutes?, )?(\d+) Seconds? '
for name,values in list(supported.items()):
    res      = subprocess.run(['timeout', '1', PHORONIX, command, name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result   = ansi_escape.sub('', res.stdout.decode('utf-8'))
    packages = []
    for match in re.finditer(pattern_packages, result, re.MULTILINE):
       packages.append(match.group(1))

    match         = re.search(pattern_download, result, re.S)
    download_size = float(match.group(1)) if match else None
    download_unit = match.group(2)        if match else None

    match     = re.search(pattern_disk, result, re.S)
    disk_size = int(match.group(1)) if match else None
    disk_unit = match.group(2)      if match else None

    match   = re.search(pattern_time, result, re.S)
    minutes = int(match.group(2)) if match and match.group(2) is not None else 0
    seconds = int(match.group(3)) if match else None

    yum_needs += packages
    supported[name]['packages'] = packages
    if download_size and download_unit:
        supported[name]['download'] = download_size if download_unit == "MB" else download_size * 1024
        supported[name]['download'] = math.ceil(supported[name]['download'])
    if disk_size and disk_unit:
        supported[name]['disk'] = disk_size if disk_unit == "MB" else disk_size * 1024
    if seconds:
        supported[name]['time'] = minutes * 60 + seconds

    count += 1
    #if count >= 10: break

#
# yum exists?
#
yum_uniques = list(set(yum_needs))
res         = subprocess.run(['yum', 'list'] + yum_uniques, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result      = res.stdout.decode('utf-8')

yum_package_exists   = []
yum_package_unfounds = []

for package in yum_uniques:
    package_exists = False
    for match in re.finditer(r"^%s\." % package.replace('+', '\+'), result, re.MULTILINE):
        if match:
            package_exists = True
            break

    if package_exists:
        yum_package_exists.append(package)
    else:
        yum_package_unfounds.append(package)

#
# install or give up
#
lets_install_tests = []
give_up_tests      = []
for name,values in list(supported.items()):
    all_exists = True
    for package in values['packages']:
        if package in yum_package_unfounds:
            all_exists = False
            break

    packages      = supported[name]['packages']
    download_size = supported[name]['download']
    disk_size     = supported[name]['disk']
    time          = supported[name]['time']
    if all_exists:
        lets_install_tests.append(name)
    else:
        give_up_tests.append(name)

#
# output
#
print("Give up testing these ... or over size / time")
print()
print("    " + ', '.join(give_up_tests))
print()

print("Because not found packages ...")
print()
print("    " + ', '.join(yum_package_unfounds))
print()

print("Unsupported packages ... %s tests" % len(unsupported))
print()
print("    " + ', '.join(unsupported.keys()))
print()

print("Planning tests are ... %s tests" % len(lets_install_tests))
print()
for name in lets_install_tests:
    print("    %s: download = %s MB, disk = %s MB, time = %s seconds" % (name, supported[name]['download'], supported[name]['disk'], supported[name]['time']))
print()

if yum_package_exists:
    print("Lets install yum packages for tests.")
    print()
    print("    yum install %s" % ' '.join(yum_package_exists))
    print()

    print("After installing yum packages, retry this.")
    print()

#
# Save data
#
print("Saved info of tests to %s" % INFO_LOG_FILE)
print()
install_info = {}
for name in lets_install_tests:
    install_info[name] = supported[name]

if not os.path.isdir(LOG_DIR):
    os.mkdir(LOG_DIR)
f = open(INFO_LOG_FILE, "w")
f.write(json.dumps(install_info))
f.close()


