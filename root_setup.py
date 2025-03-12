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

# create sshusers group
def create_sshusers_group(gname):
    try:
        grp.getgrnam(gname)
        print(f"Group {gname} already exists.")
    except KeyError:
        print(f"Creating group {gname}")
        subprocess.run(['addgroup', gname], capture_output=True)
        print(f"Group gname created.")

# create groups and users
def create_accounts(acct, grp_name=None):
    grp_name = grp_name if grp_name else acct
    try:
        grp.getgrnam(grp_name)
    except KeyError:
        print(f"Creating group {grp}")
        subprocess.run(['addgroup', grp_name], capture_output=True)
    try:
        pwd.getpwnam(acct)
    except KeyError:
        print(f"Creating user {acct}")
        subprocess.run(['adduser', '--ingroup', grp_name, '--disabled-password', '--gecos', '""', acct])
        subprocess.run(['usermod', '-aG', 'sudo', acct])

## Add ssh keys to evaadmin:authorized_keys
def add_keys(acct, ugrp=None):
    ugrp = ugrp if ugrp else acct
    ssh_dir = Path(f"/home/{acct}/.ssh")
    os.makedirs(ssh_dir) if not os.path.exists(ssh_dir) else print(f'Path {ssh_dir} exists')
    with open(ssh_dir/"authorized_keys", mode="a") as ak:
        for k in pk:
            ak.write(f'{pk[k]} \n')
    ## Set ownership to evaadmin:evaadmin
    os.chown(ssh_dir/"authorized_keys", pwd.getpwnam(acct).pw_uid, grp.getgrnam(ugrp).gr_gid)

## Add new entries to /etc/sshd_config only if needed
def tweak_sshd():
    sshd_config_path = '/etc/ssh/sshd_config'
    modifications_needed = False
    updated_lines = []

    with open(sshd_config_path, 'r') as f:
        all_lines = f.readlines()

    for ln in all_lines:
        if re.match('(PermitRootLogin\s+)yes', ln):
            updated_lines.append(re.sub('(PermitRootLogin\s+)yes', r'\1no', ln))
            modifications_needed = True
        elif re.match('#*(MaxAuthTries\s+\d+)', ln):
            updated_lines.append(re.sub('#*(MaxAuthTries\s+\d+)', r'\1', ln))
            modifications_needed = True
        else:
            updated_lines.append(ln)

    # Add any additional SSH configuration lines if they are not already present
    for ln in addl_ssh_config:
        if ln + "\n" not in updated_lines:
            updated_lines.append(ln + "\n")
            modifications_needed = True

    if modifications_needed:
        print("Modifications needed in sshd_config. Updating...")
        with open(sshd_config_path, 'w') as f:
            f.writelines(updated_lines)
        subprocess.run(['systemctl', 'restart', 'ssh'], capture_output=True)
        print("sshd_config updated and SSH service restarted.")
    else:
        print("No modifications needed for sshd_config.")

def tweak_sudoers(user):
    with open('/etc/sudoers') as f:
        for ln in f:
            if re.match(f'{user}\s+.+NOPASSWD', ln):
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
    bastion_ips = ["65.21.206.81"]      # Replace with the actual IP addresses of nanny.example.com and mommy.example.com
    print('Setting up ufw firewall....')
    ufw_status = ufw.status()
    print(f'Current status: {ufw_status}\n')
    ## Set ufw to inactive
    ufw.disable()

    if ufw_status['status'] == 'inactive':
        # Set defaults
        ufw.default(incoming='deny', outgoing='allow', routed='reject')

        # Allow SSH from both bastion hosts
        for ip in bastion_ips:
            ufw.add(f"allow from {ip} to any port 22")

        ufw.set_logging('on')
        ufw.enable()
    print(ufw.get_rules())
    print('\nDone...')


if __name__ == '__main__':
    print('Creating sshusers group...')
    create_sshusers_group('sshusers')
    create_sshusers_group('otto')

    print('Creating server accounts...')
    create_accounts('otto','sshusers')
    add_keys('otto')

    tweak_sshd()
    tweak_sudoers('otto')

    set_ufw()
