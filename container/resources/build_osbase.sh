#!/bin/bash
# fail on any error
set -e

# Standard Packages
dnf install -y python39 python39-pyyaml java-11-openjdk git gcc python39-devel zlib-devel

# FFMPEG from RPM Fusion
dnf install -y dnf-plugin-subscription-manager
dnf config-manager --set-enabled powertools
dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm
dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
dnf install -y ffmpeg

# Singularity from EPEL
dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
dnf install -y singularity

# PostgreSQL 12 from upstream
dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
dnf -qy module disable postgresql
dnf install -y postgresql12 postgresql12-server

# Install ansible for container setup (from EPEL)
dnf install -y ansible

# clean up what we can
dnf clean all
