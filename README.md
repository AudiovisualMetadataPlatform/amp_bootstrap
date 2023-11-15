# amp_bootstrap
The AMP Bootstrap provides the utilities needed to install/configure/manage
an AMP installation

# Dependency Installation
AMP is designed to be installed on a fresh physical or virtual server.

When provisioning the server, these minimums must be met:
* 4 CPU cores
* 8G RAM
* Disk space:
  * 100G for deployment and development
  * Add the size of the data you expect to process

Once provisioned, use the steps in
[Ansible Installation Instructions](./ansible/README.md) 
to install the operating system and AMP dependencies

# Setting up the AMP software
The steps below assume:
* The server is running
* The admin is logged in as the `amp` user
* `$AMP_ROOT` is where this repository has been cloned (it should be `/home/amp`)
* The current directory is `$AMP_ROOT/amp_bootstrap`

## Initializing the AMP environment
AMP requires certain directory structures to be present prior to running.  This
command will create them:
```
./amp_control.py init
```
This process only needs to be done once, but it is safe to run additional
times.


## Downloading AMP packages
The AMP software itself is distributed in package form to allow users to 
update the software in a controlled fashion. 

The release packages can be downloaded using
```
./amp_control.py download https://dlib.indiana.edu/AMP-packages/1.0.1 ../packages
```
The version 1.0.1 release is roughly 10G, so it will take some time to download.

For updates, individual packages can be downloaded using `curl` or other tools
and installed indvidually.

## Install the AMP packages
After the packages are downloaded, they need to be installed.  When new versions
of a package is made available, it can be installed in the same way.

To install all of the downloaded packages, one would run:
```
./amp_control.py install ../packages/*.tar
```
Each package's metadata will be displayed along with prompt to continue, such
as:
```
Package Data for ../packages/amp_ui__1.0.1__noarch.tar:
  Name: amp_ui
  Version: 1.0.1
  Build date: 20230807_105728
  Build revision: Branch: master, Commit: 69951e0
  Architecture: noarch
  Dependencies: ['tomcat']
  Installation path: /srv/services/amp_sys-test-8120/tomcat/webapps
Continue?
```
Enter 'y' for each of the packages.

NOTE: packages should be installed only when AMP is stopped.

A record of the installation is kept in `$AMP_ROOT/packagedb.yaml`.  This file
is human-readable but is maintained by the software, so do not modify it.


## Initial AMP Configuration
All of the AMP configuration is done through the 
`$AMP_ROOT/amp_bootstrap/amp.yaml` file.  Settings in this file will
overlay any of the default settings that the system ships with.  

Generally, settings will not need to be modified after the system is 
initially configured.

The file contains the passwords that were generated during the install.  These
fields will need to be modified or added before AMP is started the first time:

* `galaxy`
  * `admin_username`: the username to use for the galaxy backend (optional)
  * `admin_password`: the password to use for the galaxy backend (optional)
* `rest`
  * `admin_username`: the admin username (defaults to `ampadmin`)
  * `admin_password`: the admin password for the AMP UI
  * `admin_email`: the email address for AMP's email

NOTE:  this is a [YAML](https://yaml.org/) file, so indentation is important 
and should use spaces

Out of the box AMP supports local MGMs but the cloud-based ones require
additional configuration.  You can base your configuration on the
default configuration supplied in 
`$AMP_ROOT/data/default_config/*.user_defaults`

Copy the text from the `*.user_defaults` files into the `amp.yaml` file,
taking care to merge any toplevel sections.  For example the AWS and Azure
tools both have a toplevel `cloud` section.

Once the `amp.yaml` file has been modified, the AMP system needs to be 
reconfigured.  

NOTE: Reconfiguration should only be performed when the system is stopped!

The configuration is applied to the different components by running:
```
./amp_control configure
```

NOTE: The first time configuration is started it will take a while since
galaxy needs to download dependencies before it can configure itself.


# Managing the AMP Server
The amp_control.py tool provides the functionality needed to manage the AMP
system, from downloading the AMP packages to starting/stopping the system.



Information about the options for amp control can be obtained by using the
`--help` argument on the tool:

```
$ ./amp_control --help
usage: amp_control.py [-h] [--debug] [--config CONFIG] {init,download,start,stop,restart,configure,install} ...

positional arguments:
  {init,download,start,stop,restart,configure,install}
                        Program action
    init                Initialize the AMP installation
    download            Download AMP packages
    start               Start one or more services
    stop                Stop one or more services
    restart             Restart one or more services
    configure           Configure AMP
    install             Install a package

optional arguments:
  -h, --help            show this help message and exit
  --debug               Turn on debugging
  --config CONFIG       Configuration file to use
```

## Starting/Stopping AMP
Starting and stopping AMP can be accomplished using one of these commands:
* Start AMP: `./amp_control.py start all`  
* Stop AMP: `./amp_control.py stop all`

## Reconfiguring AMP
If the AMP configuration needs to be changed it is important that the AMP
system is stopped before applying the configuration.  The steps are:
* Stop AMP: `./amp_control.py stop all`
* Edit the `amp.yaml` file as needed
* Configure AMP: `./amp_control.py configure`
* Start AMP: `./amp_control.py start all`

If there are errors, stop AMP (because some components may have started) and
corrent `amp.yaml`

## Updating AMP Packages
If AMP packages need to be updated, the process is:
* Download the requred package to `$AMP_ROOT/packages/<package.tar>`
* Stop AMP: `./amp_control.py stop all`
* Install the package: `./amp_control.py install ../packages/<package.tar>`
* Reconfigure AMP: `./amp_control.py configure`
* Start AMP: `./amp_control.py start all`


# Developing AMP
Information about developing the AMP codebase or adding your own packages can be
found [here](./docs/development/developing.md)

