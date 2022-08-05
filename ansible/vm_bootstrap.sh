#!/bin/bash
set -e

echo "Installing git"
sudo dnf install -y git

echo "Cloning the AMP bootstrap repository"
git clone https://github.com/AudiovisualMetadataPlatform/amp_bootstrap.git

echo "Starting the Ansible bootstrap"
cd amp_bootstrap/ansible
./ansible_bootstrap.sh

