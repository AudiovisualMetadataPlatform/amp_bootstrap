#!/bin/bash
# exit on errors
set -e

umask 022

# Download the packages
if [ "x$AMP_MIRROR" != "x"]; then
    BASEURL=$AMP_MIRROR
else
    BASEURL=https://dlib.indiana.edu/AMP-packages/current
fi
cd /srv/amp/amp_bootstrap
./amp_control.py download $BASEURL /srv/amp/packages


# Install the packages
cd /srv/amp/amp_bootstrap
./amp_control.py install --yes ../packages/amp_galaxy*
./amp_control.py install --yes ../packages/amp_[mru]*


# Remove the package files
rm -v /srv/amp/packages/*

# force galaxy to install all of its dependencies
cd /srv/amp/galaxy
export GALAXY_ROOT=`pwd`
sh scripts/common_startup.sh

# force rebuild (20220726-1538)