#!/bin/bash
# fail on any error
set -e

# Deferring the PostgreSQL stuff until later in the process...

# On a normal system we'd run things as an AMP user, but
# in a container that's not strictly necessary. So we're
# just going to do everything as root until I discover
# that it's a bad idea later...

# Create the AMP directory
mkdir /srv/amp
cd /srv/amp

# Update the singularity path to bind /srv/amp when running
echo "bind path = /srv/amp" >> /etc/singularity/singularity.conf

# No need to open the firewall

# Install the bootstrap
git clone https://github.com/AudiovisualMetadataPlatform/amp_bootstrap.git

# Intialize the amp directory tree
# We can do this because nothing in the initialization requires the configuration to be correct
cd amp_bootstrap

# DEBUGGING the current branch! (force 20220726-0928)
git checkout AMP-2057

./amp_control.py init

