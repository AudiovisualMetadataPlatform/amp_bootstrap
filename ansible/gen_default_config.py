#!/usr/bin/env python3

import yaml
import sys
from pathlib import Path
import random

def main():
    new_config = Path(sys.path[0], '../amp.yaml')
    if new_config.exists():
        print("Skipping configuration -- amp.yaml already exists")
        exit(0)

    # get the configuration from the ansible setup
    # this is really only the database password
    with open(Path(sys.path[0], "settings.yml")) as f:
        ansible_config = yaml.safe_load(f)

    # get the default configuration file
    with open(Path(sys.path[0], "../amp.yaml.sample")) as f:
        config = yaml.safe_load(f)

    # make a pile of changes (mostly snagged from the container amp_entry.py)!
    config['galaxy']['admin_username'] = 'ampuser@example.edu'
    config['galaxy']['admin_password'] = gen_garbage(12)
    config['galaxy']['id_secret'] = gen_garbage(25)
    config['galaxy']['host'] = None  # bind to all interfaces
    config['mgms']['hmgm']['auth_key'] = gen_garbage(32)
    config['rest']['admin_password'] = gen_garbage(12)
    config['rest']['encryption_secret'] = gen_garbage(14)
    config['rest']['jwt_secret'] = gen_garbage(15)
    config['rest']['db_name'] = 'amp'
    config['rest']['db_user'] = 'amp'
    config['rest']['db_pass'] = ansible_config['amp_db_password']


    # write out the new configuration file
    with open(new_config, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    print("New configuration generated.")


def gen_garbage(length=10):
    res = ""
    for i in range(length):
        res += random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")        
    return res

if __name__ == "__main__":
    main()