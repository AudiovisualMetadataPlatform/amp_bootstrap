# Ansible Setup
These setup scripts can be used to create a usable AMP installation for development (and maybe production?)
instead of manually configuring an installation.

## Base VM setup

### The VM itself

Create a VM using whatever environment suits you -- since this works on the OS level any hypervisor
should work.

You'll probably want at least these specs:
* 8GB RAM
* 2 CPU
* Disk:
  * xGB for operating system and AMP software
  * xGB for data files
  * xGB for development (at least 150G for container dev)
* Network that can be reached from the outside for these ports:
  * 22 - SSH for shell/file access
  * 8080 - AMP's main port
  * 8082 - Galaxy (optional)

### Base operating system install

For IU development we've been using Rocky Linux 8 as our OS.  

Download the Rocky Linux 8 Minimal ISO from https://rockylinux.org/download

(at the time of this writing it is RockyLinux-8.6-x86_64-minimal.iso)

Boot the ISO and Install Rocky Linux with these options:
* Partitioning:
  * Default partitioning 
  * AMP will be installed in /home/amp
* Set your timezone
* Software Selection:
  * Server
* Network
  * Connect the network device
* User settings
  * set the root password to something secure
  * create a user for administration
    * Not "amp"!
    * select "Make this user administrator"

### Get the setup scripts

This repository has the scripts needed to bring
the VM up
