#!/bin/bash
# exit on errors
set -e

umask 022

# Download the packages
cd /srv/amp/packages
BASEURL=https://dlib.indiana.edu/AMP-packages
for n in \
    amp_galaxy-21.01.tar \
    amp_mgms-applause_detection-0.1.0.tar \
    amp_mgms-aws-0.1.0.tar \
    amp_mgms-azure-0.1.0.tar \
    amp_mgms-gentle-0.1.0.tar \
    amp_mgms-hmgms-0.1.0.tar \
    amp_mgms-ina_speech_segmenter-0.1.0.tar \
    amp_mgms-kaldi-0.1.0.tar \
    amp_mgms-mgm_python-0.1.0.tar \
    amp_mgms-mgms-0.1.0.tar \
    amp_rest-0.0.1-SNAPSHOT.tar \
    amp_ui-0.1.0.tar \
    ; do
    echo $n
    curl -o $n $BASEURL/$n
done

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
