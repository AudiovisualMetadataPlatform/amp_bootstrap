#!/bin/bash
# fail on any error
set -e

# Deferring the PostgreSQL stuff until later in the process...

# On a normal system we'd run things as an AMP user, but
# in a container that's not strictly necessary. So we're
# just going to do everything as root until I discover
# that it's a bad idea later...

# Create the AMP directory
mkdir -p /srv/amp || /bin/true
cd /srv/amp

# Update the apptainer path to bind /srv/amp when running
echo "bind path = /srv/amp" >> /etc/apptainer/apptainer.conf

# No need to open the firewall

# Install the bootstrap
mkdir amp_bootstrap
cd amp_bootstrap
tar -xvf /tmp/amp_bootstrap.tar

# Intialize the amp directory tree
./amp_control.py init

