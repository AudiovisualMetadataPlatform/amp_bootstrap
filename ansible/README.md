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
  * 5432 - Postgresql

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
  * create the amp user
    * use "amp" as the username
    * select "Make this user administrator"
    * select a reasonable password

### Get the setup scripts

This repository has the scripts needed to install all of the
requirements for AMP and set up the OS.

Log into the VM as the amp user and run this command to start bootstrapping the VM...

```
curl https://raw.githubusercontent.com/AudiovisualMetadataPlatform/amp_bootstrap/main/ansible/vm_bootstrap.sh | /bin/bash
```

The command will:
* install git
* clone the amp_bootstrap repository from github (this repository)
* run the ansible/ansible_bootstrap.sh script
  * installs the EPEL repository and 



Everything below here needs to be rewritten.
----

Log into the VM as your administration user and install
the prerequisites:

```
sudo dnf install -y git
```

Clone this repository into the admin user's home directory:

```
git clone https://github.com/AudiovisualMetadataPlatform/amp_bootstrap.git
```

and change directory into this directory

```
cd amp_bootstrap/ansible
```

