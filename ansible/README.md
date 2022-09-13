# Ansible System Setup
These setup scripts can be used to create a usable OS environment for 
using and developing AMP.

This can be used on a VM or a physical system.  If you are using a VM, any 
hypervisor should work since this operates at the OS level

# System requirements

## The VM itself

Create a VM using whatever environment suits you -- since this works on the OS level any hypervisor
should work.

You'll probably want at least these specs:
* 8GB RAM
* 2 CPU
* Disk:
  * 20GB for operating system and AMP software
  * xGB for data files
  * 30GB for development (at least 150G for container dev)

# Base operating system install

For IU development we've been using Rocky Linux 8 as our OS.  

Download the Rocky Linux 8 Minimal ISO from https://rockylinux.org/download

(at the time of this writing it is RockyLinux-8.6-x86_64-minimal.iso)

Boot the ISO and Install Rocky Linux with these options:
* Installation Destination:
  * Accept the default partitioning by just pressing "Done"
  * AMP will be installed in /home/amp if you wish to modify the configuration
* Network & Hostname
  * Connect the network device
* Time & Date
  * Set the time zone
  * Enable Network Time
* Software Selection:
  * Server is the default, you shouldn't need to change it.
* Root password
  * set this to something secure
* User Creation
  * Full name = AMP
  * User name = amp
  * Make this user administrator
  * Set the password to something strong


# AMP environment setup

This repository has the scripts needed to install all of the
requirements for AMP and set up the OS.

Log into the VM as the amp user to start the bootstrapping process.

If you wish the VM to have the Workstation environment installed, run this command:
```
export GUI_WORKSTATION=1
```

To start bootstrapping the VM, run this command

```
curl https://raw.githubusercontent.com/AudiovisualMetadataPlatform/amp_bootstrap/main/ansible/vm_bootstrap.sh | /bin/bash
```

The command above will start the vm_bootstrap.sh script which will:

* install git
* clone the amp_bootstrap repository (this one)
* starts the ansible_bootstrap.sh script which..
  * installs the EPEL repository and ansible
  * creates a password for the amp database user (if it hasn't done so before)
  * runs the ansible playbook amp_bootstrap.yml, which will:
    * update the system packages
    * install the GUI (if desired)
    * install the packages needed for AMP
    * install and configure PostgreSQL 12 (using the password above)
    * open the firewall for 8080 (AMP), 8082 (Galaxy), and 5432 (PostgreSQL)
  * generate a default configuration for AMP (if one doesn't exist)

At that point, the user should reboot the VM to fully apply all of the changes. 



# Using the VM

When the VM starts, all of the needed OS services should be running, but AMP requires a manual start.

Before starting AMP itself for the first time, verify the generated amp.yaml configuration file!


## Running AMP as a non-developer

The installation is the same as instrutions in the main repository README, starting with "Managing AMP"

Starting, stopping, installing packages, reconfiguring, etc should work normally.

The 8080 port on the VM should be exported to the outside world to allow access to the AMP software.  The mechanism for doing this is specific to the Hypervisor platform.

## Development using the VM

There are a couple of ways to use the VM as a development platform

In both scenarios it may be desirable to expose some VM ports to the host workstation to access the servers running on the VM

Suggested ports and local mappings:

| VM Port | Host Port | Purpose  | Notes |
| ---     | ---       | ---      | --- |
| 8080    | 8080      | AMP UI   | Access to AMP software UI |
| 8082    | 8082      | Galaxy   | Only needed to interact with galaxy backend |
| 22      | 8022      | SSH      | Useful for logging in and transferring files |
| 5432    | 8032      | Postgres | Only needed to access postgres directly |



### Using the VM as development workstation

In this scenario, the VM is a virtual workstation where the development environment (IDE, web browser, etc) and the AMP software are all running.  

The developer logs into the VM's GUI as the amp user and builds/modifies/installs AMP code using the VM's console.  

Setting up this environment would consist of:
* Installing the workstation software: 
  * If the GUI wasn't installed during the bootstrap, it can be added by running:
    * `sudo dnf groupinstall -y Workstation`
    * `sudo systemctl set-default graphical`
    * `sudo shutdown -r now`
  * When logging in the first time, select the gear next to the "Sign In" button before entering the password, and select "Classic (Wayland display server)" for a more traditional desktop experience.
* Installing the developer's preferred IDE (commands vary)
* Configuring git on the VM
  * user.name and user.email
  * ssh keys and other security bits
* use the VM's web browser to access AMP
  * AMP: http://locahost:8080
  * Galaxy: http://localhost:8082
* use a postgres client on the VM to connect via localhost port 5432
* use a VM-installed IDE to edit/build/deploy code


### Using the VM as a headless server

In this scenario the IDE and related tools are run on the hosting workstation but the AMP software is running in the VM, as if it was a server in a datacenter somewhere.

Setting this up is a little more complicated, but does allow the developer more flexibility.  

Generally, the setup would be something like this:
* expose all of the ports above to their suggested local ports
* use ssh to connect to the VM `ssh -p 8022 amp@localhost`
* use the local web browser to access AMP
  * AMP:  http://localhost:8080
  * Galaxy:  http://localhost:8082
* use a postgres client to connect to postgres on localhost port 8032
* use a local IDE that either pushes code to the VM via ssh or interacts over ssh directly (Visual Studio Code Remote Explorer will do this)

# Known issues:

## Segfault during "Update Packages"
Rarely the ansible_boostrap.yml playbook will segfault during "Update Packages".  The only explanation I've been able to come up with is a
network issue upstream.  You can safely retry the setup by:
```
cd amp_bootstrap/ansible
./ansible_bootstrap.sh
```

## The gentle MGM won't build because OpenBLAS can't determine the CPU type

Some Hypervisors will produce a set of CPU Flags and/or ID strings which doesn't match a real
CPU (I'm looking at you, QEMU/KVM!) so OpenBLAS fails to build which breaks the gentle MGM build.

The easiest solution is to pass through the host system's CPU flags to the guest  (such as `-cpu host` flag on QEMU)
so OpenBLAS gets a sane CPU configuration


