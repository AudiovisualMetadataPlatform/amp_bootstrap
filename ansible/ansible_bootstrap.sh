#!/bin/bash
set -e

# make sure ansible is installed
dnf install -y ansible ansible-collection-ansible-posix 

# create passwords that we'll need later
if [ ! -e settings.yml ]; then
    # we've not run before, so we need to create a password
    # for the database user  
    echo "amp_db_password: " $(dd if=/dev/urandom bs=45 count=1 | md5sum -b | cut -f1 -d\ ) > settings.yml
fi

# do all of the ansible stuff
sudo ansible-playbook amp_bootstrap.yml -i inventory.yml "$@"

# set up the AMP stuff