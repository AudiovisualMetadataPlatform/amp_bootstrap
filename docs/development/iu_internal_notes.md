# IU Internal Development Notes

These notes are useful for IU developers and are likely useless for anyone
that isn't an IU developer.

# Server VM Setup

A server-based VM service can be setup using the following instructions

Assume these (fictional) values:
* VM Host server name:  $VMHOST
* VM service user name:  $HOSTUSER
* VM service base port:  $PORT
* VM service root directory:  $SERVICEROOT (which will likely expand to /srv/services/$HOSTUSER_amp-devel-$PORT)

## Managing the VM service instance

Logging into vmhostserver as servuser, the user can start/stop/restart the
VM service by using the iul_service tool:

```
iul_service stop $HOSTUSER_amp-devel-$PORT
iul_service start $HOSTUSER_amp-devel-$PORT
```

Stopping the service using this mechanism is the equivalent of pulling the
VM's power plug, so it's probably better to shut down a VM by using the
guest OS's shutdown functionality.


## Connecting to the VM 

### VM console
The VM console can be accessed by using a VNC client with a network tunnel.

First, install a VNC client on your workstation.  The tigervnc client can be
downloaded from https://tigervnc.org/

After installing the VNC client a tunnel is required to connect to the
VNC server that the VM provides.   On modern operating systems, this tunnel
can be created by running this command in a terminal:

```
ssh -L 5900:$SERVICEROOT/vnc-socket -N $VMHOST
```

As long as this program is running the VM's console can be accessed via the
VNC display at localhost:0

### Other Services

Other services on an AMP VM service are mapped to these ports:

| Service | Real Port | Offset from base port | Example port |
| --- | --- | --- | --- |
| AMP | $PORT | 0 | 8000 |
| SSH | 22 | 1 | 8001 |
| Galaxy | $PORT + 2 | 2 | 8002 |
| Postgres | 5432 | 3 | 8003 |

When using the VM's console, the services are accessed via the 
real port column (i.e. Postgres is on port 5432)

When accessing from another host within the firewall, the example port
column is used (i.e. Postgres is available on 8003) 

## VM Setup

### Request a VM
Ask the system administrator for a VM service configured for AMP.  When the 
service is provisioned, the real values for vm host, base port, service 
directory will be supplied.  

The VM will be blank but will mount the OS install disk by default on the
first boot.

### Start the VM service
Log into $VMHOST as $HOSTUSER and start the VM service by running
```
iul_service start $SERVICEROOT
```
This will start the VM to begin installation

### Connect to the VM's console
Connect to the console using the instructions above:  create the console
tunnel and then connect the VNC client to localhost:0.

On the very first boot the VM will be in different states, depending on the
time between VM start and connection to the console:
* Boot menu countdown -- press the up arrow to select Install option and press
  enter to begin the installation
* Checking the boot media -- if it is checking the boot media, let it finish
  and it will start the installation when it finishes
* Installation start screen

### Install the Base OS

These options will be needed to set up the VM:

* Installation Destination:
  * Accept the default partitioning by just pressing "Done"
    * If reinstalling, reclaim space by removing all partitions
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

### Install the AMP prerequisites

Using the VM console, log into the VM as the AMP user and run these commands
to install the AMP prerequisites and enable the GUI:

```
export GUI_WORKSTATION=1
curl https://raw.githubusercontent.com/AudiovisualMetadataPlatform/amp_bootstrap/main/ansible/vm_bootstrap.sh | /bin/bash
```

At this point the VM will be busy for a while installing the needed dependencies
and configuring the system.

When it has finished doing the install (and the prompt is back without an error)
reboot the VM by running `shutdown -r now`

### First GUI login
When the GUI appears on the VM, select the amp user and click the gear next to
the "Sign In" button.  Select "Classic (Wayland display server)" for a more
traditional GUI experience.

### Disable firewall
Since this is running on a VM behind a firewall, it must be disabled.
* `sudo systemctl stop firewalld`
* `sudo systemctl disable firewalld`

### Installing AMP software
Now that the prerequisites have been installed, you can manage the AMP 
installation as outlined in the main README.md file.  The short version
is (logged into the VM as the AMP user):

* `cd amp_bootstrap`
* `./amp_control.py init`
* Acquire the packages.  Either:
    * Download pre-built packages `./amp_control.py download https://dlib.indiana.edu/AMP-packages/new_packages ../packages`  
    * Or use the instructions below (Build AMP packages from scratch) to build a set of packages from scratch
* `./amp_control.py install ../packages/*.tar --yes`
* `./amp_control.py configure --user_config amp.yaml`


### Configure AMP

Values in the amp_bootstrap/amp.yaml file that need to be updated:
* amp
  * port -- this should be set to $PORT
* galaxy
  * admin_username -- set to the email for the galaxy administrator
  * admin_password -- set to the password for the galaxy administrator
  * host -- set to null if you want galaxy to be available outside of the VM
* mgms
  * set these values as appropriate, although they can be ignored when testing
    non-cloud MGMs
* rest:
  * admin_email -- set to the email of the AMP administrator
  * admin_password -- set to the password of the AMP administrator
  * admin_username -- set to the username of the AMP administrator

When these values are set, apply the configuration to the AMP system:

```
./amp_control.py configure
```

### Start/stop AMP
At this point AMP is ready for use and can be managed using the normal
AMP commands 

```
./amp_control.py start all
./amp_control.py stop all
```

The rest of the system management is performed in accordance with the 
instructions in the main documentation

### Build AMP packages from scratch
Building a set of packages from scratch can be performed by:

* `cd ~/amp_bootstrap`
* `./amp_devel.py init`
* `./amp_devel.py build`

This will create the necessary directories, download the source repositories
from github, and build the packages.  When it is completed the new packages
will be in the packages directory.

