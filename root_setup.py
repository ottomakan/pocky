#!/usr/bin/env python3

import grp
from pathlib import Path
import pwd
import re
import os
import subprocess
import platform
#import apt
import sys
#import pip
import pyufw as ufw
from public_keys import pk, addl_ssh_config, apt_pkg, py_pkg

def pip_install(package):
    import pip
    if hasattr(pip, 'main'):
        pip.main(['install', package])
    else:
        pip._internal.main(['install', package])

# create groups and users
def create_accounts(acct, grp=None):
    grp = grp if grp else acct
    try:
        ret = grp.getgrnam(acct)
    except:
        print(f"Creating group {grp}")
        ret = subprocess.run(['addgroup',grp], capture_output=True)
    try:
        ret = pwd.getpwnam(acct)
    except:
        print(f"Creating user {acct}")
        ret = subprocess.run(['adduser','--ingroup',grp,'--disabled-password','--gecos', '""',acct])
        ret = subprocess.run(['usermod','-aG','sudo',acct])

## Add ssh keys to evaadmin:authorized_keys
def add_keys(acct,ugrp=None):
    ugrp = ugrp if ugrp else acct
    ssh_dir = Path(f"/home/{acct}/.ssh")
    os.makedirs(ssh_dir) if not os.path.exists(ssh_dir) else print(f'Path {ssh_dir} exists')
    with open(ssh_dir/"authorized_keys", mode="a") as ak:
        for k in pk:
            ak.write(f'{pk[k]} \n')
    ## Set ownership to evaadmin:evaadmin
    os.chown(ssh_dir/"authorized_keys", pwd.getpwnam(acct).pw_uid, grp.getgrnam(ugrp).gr_gid)

## Add new entries to /etc/sshd_config
def tweak_sshd():
    with open('/etc/ssh/sshd_config', 'r+') as f:
        all_lines = f.readlines()
        f.seek(0) # start at the beginning of the file
        for ln in all_lines:
            if re.match('(PermitRootLogin\s+)yes',ln):
                f.write(re.sub('(PermitRootLogin\s+)yes',r'\1no',ln))
            elif re.match('#*(MaxAuthTries\s+\d+)',ln):
                f.write(re.sub('#*(MaxAuthTries\s+\d+)',r'\1',ln))
            else:
                f.write(ln)
        for ln in addl_ssh_config:
            f.write(ln+"\n")

def tweak_sudoers(user):
    with open('/etc/sudoers') as f:
        for ln in f:
            if re.match(f'{user}\s+.+NOPASSWD',ln):
                print(f'{user} Entry exists...')
                return
    with open('/etc/sudoers', 'a') as f:
        f.write(f'{user} ALL=(ALL) NOPASSWD:ALL\n')

def install_ubuntu_pkg(pkg_name):
    #pkg_name = "libjs-yui-doc"

    cache = apt.cache.Cache()
    cache.update()
    cache.open()

    pkg = cache[pkg_name]
    if pkg.is_installed:
        print(f'{pkg_name} already installed')
    else:
        pkg.mark_install()

        try:
            cache.commit()
        except:
            print('Sorry, package installation failed!')

def pip_install(package):
    import pip
    if hasattr(pip, 'main'):
        pip.main(['install', package])
    else:
        pip._internal.main(['install', package])

def set_ufw():
    print('Setting up ufw firewall....')
    ufw_status = ufw.status()
    print(f'Current status: {ufw_status}\n')
    ## Set ufw to inactive
    ufw.disable()

    if ufw_status['status'] == 'inactive':
        # Set defaults
        ufw.default(incoming='deny', outgoing='allow', routed='reject')
        ufw.add("allow 22")
        ufw.set_logging('on')
        ufw.enable()
    print(ufw.get_rules())
    print('\nDone...')

if __name__ == '__main__':
    print('Creating server accounts...')
    create_accounts('poktadmin')
    add_keys('poktadmin')
    tweak_sshd()
    tweak_sudoers('poktadmin')
    ## Install htop, ufw
#    for pkg in apt_pkg:
#        install_ubuntu_pkg(pkg)

    ## Install additional OS packages
#    print('Installing additional Python packages...')
#    for p in py_pkg:
#        pip_install(p) if re.findall('Ubuntu', platform.version()) else print("Not running on Ubuntu")
    set_ufw()
