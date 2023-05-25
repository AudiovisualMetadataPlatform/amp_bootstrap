#!/bin/bash
set -e

# Install EPEL
sudo dnf install -y epel-release

# make sure ansible is installed
sudo dnf install -y ansible-core ansible-collection-ansible-posix 

# create passwords that we'll need later
if [ ! -e settings.yml ]; then
    # we've not run before, so we need to create a password
    # for the database user  
    echo "amp_db_password: " $(dd if=/dev/urandom bs=45 count=1 | md5sum -b | cut -f1 -d\ ) > settings.yml
fi

# do all of the ansible stuff
sudo ansible-playbook amp_bootstrap.yml -i inventory.yml \
     --extra-vars "use_gui=$GUI_WORKSTATION" "$@"

# create a usable default configuration file
./gen_default_config.py


echo "
The system should be properly configured for AMP:
    * All prerequisites for building and running AMP are installed
    * An AMP PostgreSQL user and database have been created
    * A default amp configuration file has been generated
    * The firewall has been opened for these ports:
      * 8080 - The main AMP port
      * 8082 - Galaxy
      * 5432 - PostgreSQL

Next steps:
    * Reboot the system to finalize the updates
    * Check the generated amp.yaml file and modify it as needed
"

