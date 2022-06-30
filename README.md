# amp_bootstrap
AMP system managment tool

(Documentation is a work in progress)

# AMP System Requirements
To run AMP the following system requirements must be met:
* Python >= 3.6 
* PyYaml
* Java Runtime 11
* Singularity runtime 3.8
* PostgreSQL >= 12
* Git

## Temporary requirements
Until AMP-1912 gets merged, the host system will also need these packages:
* ffmpeg

# Installation

The installation instructions below are for RockyLinux 8 but have also been tested on Fedora 36.  Other RedHat-like distributions should work similarly.


For non-RH distros, the commands may be different, but the package names should be similar.


## Install system dependencies

As root, install the system dependencies:

```
dnf install -y python39 python39-pyyaml java-11-openjdk git
dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
yum install -y singularity
```

Install the pre-AMP-1912 dependencies:
```
dnf config-manager --set-enabled powertools
dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm
dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
dnf install -y ffmpeg
```

### Argh, more dependencies
It looks like Galaxy wants to build some python modules because there aren't wheels available for them.  As root install GCC so it can do so:

```
dnf install -y gcc python39-devel zlib-devel
```


## Install/Configure postgres

AMP needs access to a postgres 12+ server.  If your organization has one, create a user and a database for AMP, otherwise it can be run on the AMP server.

Install the packages as root:
```
dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
dnf -qy module disable postgresql
dnf install -y postgresql12 postgresql12-server
```

Initialize postgres
```
postgresql-12-setup initdb
```

Modify postgres host-based auth rules:
```
cp /var/lib/pgsql/12/data/pg_hba.conf /var/lib/pgsql/12/data/pg_hba.conf.original
cat > /var/lib/pgsql/12/data/pg_hba.conf <<EOF
# type db   user      addr           method
local  all  postgres                 peer
host   all  all       127.0.0.1/32   md5
host   all  all       ::1/128        md5
EOF
```

Become the postgres user and set up the amp db user and database:
```
su - postgres
createuser amp --pwprompt
createdb --owner=amp amp
exit  # this will return you to root.
```

Make a note of the username and password used for the AMP database user.

## Create an amp system user and installation directory

The AMP system will need to run as a normal user so create an unpriviledged user
and a directory for AMP to lve in. This example creates /srv/amp and creates an
amp system user:

```
useradd -m amp
passwd amp
mkdir /srv/amp
chown -R amp.amp /srv/amp
```

### Singularity binding
If the AMP installation path is not within the amp user's home directory, singularity containers may fail to start.  To resolve this issue, add the "bind path" to /etc/singularity/singularity.conf

## Open the firewall
Most Linux distributions firewall ports by default.  Open the firewall for the main AMP port:

```
firewall-cmd --add-port 8080/tcp
firewall-cmd --add-port 8080/tcp --permanent
```

If you need access to galaxy, you will need to open 8082 the same way.

## Log in as the AMP user
The remainder of the instructions will be done as the amp system user.  You can either log into the system via ssh as the amp user or use sudo to become the amp user:

```
sudo -u amp bash -l
cd /srv/amp
```

## Install the bootstrap
With all of the prerequisites satisfied, the amp_bootstrap repository (this repository!) can be installed.

```
cd /srv/amp
git clone https://github.com/AudiovisualMetadataPlatform/amp_bootstrap.git
```

## Configure AMP
All of the AMP system settings are in amp_bootstrap/amp.yaml.   If you change settings in this file you will need to stop AMP, run the configuration command, and restart AMP.  Normally settings do not need to be changed after the system is running.

### Copy the default file to a working file
```
cd amp_bootstrap
cp amp.yaml.default amp.yaml
```

### Modify the amp.yaml file
You can download the file and edit it on your workstation/laptop and then upload it or you can edit it directly on the server using `nano amp.yaml`

Use whichever method works best for you.

The yaml file is broken up into different sections and each section has several keys & values that can be changed.
There are comments in the file to help you set the values.  Here are the ones that are the most common to change:

* amp
  * host:  the hostname that will be used for the generated URLs.  On a VM it will be the hostname of the VM
  * port:  the base port.  AMP will be accessed via this port and other services will be relative to this port
  * https:  if the service is proxied via https, set this to true
* galaxy
  * host: the hostname that galaxy will listen to.  Usually leave this as localhost since users will not access it directly.
  * admin_username:  this is the administration user for the galaxy.  It is in the form of an email address
  * admin_password:  this is the galaxy administration user password.  Don't forget this!
  * id_secret: this is a value used to hash galaxy data for security.  Change this value to some random text but do not modify it in the future, since doing so will break AMP
* ui
  * unit:  This is the name of the default unit used in AMP
* rest
  * db_host:  the hostname for the postgres server.  If you're running postgres on the amp machine it will be 'localhost'
  * db_name:  the database name used for amp
  * db_user:  the amp user in postgres
  * db_pass:  the amp user password in postgres
  * admin_username:  the username for the auto-created AMP administration user
  * admin_password:  the password for the auto-created AMP administration user
  * admin_email:  the email address for the auto-created AMP administration user
  * avalon_url:  The base URL for the Avalon Media System (ignored if you're not using Avalon integration)
  * avalon_token: The authentication token for Avalon (ignored if you're not using Avalon integration)
  * encryption_secret:  Change this to a random string for security
  * jwd_secret: Change this to a random string for security
* mgms
  * aws_comprehend -- settings for AWS comprehend MGM
    * default_bucket:  Bucket used for data transfer
    * default_access_arn:  ARN for access
  * aws_transcribe -- settings for AWS Transcribe
    * default_bucket:  Bucket used for data transfer
    * default_directory: "directory" used in the default bucket (can leave blank)
  * jira -- Settings for JIRA integration
    * server:  base URL
    * username:  Username for AMP to talk to Jira
    * password:  password for AMP to talk to Jira
    * project: Project used for AMP HMGM tasks
  * azure -- Settings for Azure-based services
    * accountId:  account id
    * apiKey: key for azure
    * s3Bucket: bucket used for storage on azure
  * aws -- Generic AWS access settings
    * aws_access_key_id:  access key id
    * aws_secret_access_key: secret access key
    * region_name: region to use
  * hmgm -- HGM settings
    * auth_key:  change to some random text for security
    * Not sure what the rest of these keys do




## Intialize the AMP environment
Initializing the environment will craete the directories need for amp and will download Tomcat and (until AMP-1912 lands) it will install MediaProbe

```
./amp_control.py init
```

The amp directory structure should look like this:
```
/srv/amp
├── amp_bootstrap
│   └── docs
├── data
│   ├── config
│   ├── MediaProbe
│   │   └── media_probe
│   └── symlinks
├── galaxy
├── packages
└── tomcat
    ├── bin
    ├── conf
    ├── lib
    ├── logs
    ├── temp
    ├── webapps
    └── work
```




# Managing AMP

## Installing AMP packages
Now that the environment has been initialized it's time to install the packages.  At this time there is not a
public website where the packages can be retrieved, so contact the AMP developers for the latest build.

The current package list:
```
-rw-r-----. 1 bdwheele bdwheele 826M Jun 23 14:11 amp_galaxy-21.01.tar
-rw-r-----. 1 bdwheele bdwheele 1.6G Jun 23 14:12 amp_mgms-applause_detection-0.1.0.tar
-rw-rw-r--. 1 bdwheele bdwheele 1.2G Jun 23 14:12 amp_mgms-gentle-0.1.0.tar
-rw-rw-r--. 1 bdwheele bdwheele 1.7G Jun 23 14:12 amp_mgms-ina_speech_segmenter-0.1.0.tar
-rw-rw-r--. 1 bdwheele bdwheele 3.9G Jun 23 14:12 amp_mgms-kaldi-0.1.0.tar
-rw-rw-r--. 1 bdwheele bdwheele 1.4G Jun 23 14:12 amp_mgms-mgm_python-0.1.0.tar
-rw-rw-r--. 1 bdwheele bdwheele 430K Jun 23 14:12 amp_mgms-mgms-0.1.0.tar
-rw-r-----. 1 bdwheele bdwheele  67M Jun 23 14:12 amp_rest-0.0.1-SNAPSHOT.tar
-rw-r-----. 1 bdwheele bdwheele 4.5M Jun 23 14:12 amp_ui-0.1.0.tar
```

Download the packages into the packages directory.

When installig AMP, the galaxy package has to be installed prior to any amp_mgms package.  Beyond that, there's no required order.

```
./amp_control.py install ../packages/amp-galaxy-21.01.tar
./amp_control.py install --yes ../packages/amp_[mru]*.tar
```

When finished the amp_bootstrap/install.log should have recorded the installation:

```
20220623-142030: Package: amp_galaxy Version: 21.01  Build Date: 20220617_155321
20220623-143306: Package: amp_mgms-applause_detection Version: 0.1.0  Build Date: 20220517_100907
20220623-143309: Package: amp_mgms-gentle Version: 0.1.0  Build Date: 20220517_100909
20220623-143315: Package: amp_mgms-ina_speech_segmenter Version: 0.1.0  Build Date: 20220517_100912
20220623-143334: Package: amp_mgms-kaldi Version: 0.1.0  Build Date: 20220517_100917
20220623-143339: Package: amp_mgms-mgm_python Version: 0.1.0  Build Date: 20220517_100931
20220623-143340: Package: amp_mgms-mgms Version: 0.1.0  Build Date: 20220517_100934
20220623-143340: Package: amp_rest Version: 0.0.1-SNAPSHOT  Build Date: 20220617_111810
20220623-143341: Package: amp_ui Version: 0.1.0  Build Date: 20220617_140922
```

New packages can be installed at any time, but AMP must be stopped during the install and the configuration must be refreshed after packages are installed.


## Configure AMP

The system can be configured based on the values in amp.yaml.

```
./amp_control.py configure
```

The first time this is run it will take some time since galaxy requires a bunch of dependencies to be downloaded before the configuration can complete.

AMP must be stopped before configuring.



## Start AMP

AMP can be started by running:

```
./amp_control.py start all
```

The first time galaxy is started it will take a while to download dependencies.  Additionally, a helper script must be run on the first startup to create the AMP default unit:

```
./bootstrap_rest_unit.py
```

## Stop AMP

AMP can be shut down by running
```
./amp_control.py stop all
```

It is important to stop AMP before:
* Installing new packages
* Updating the configuration


# Developing AMP
If you wish to modify/enhance AMP, you can use the package installation as a starting point:

* Install AMP as described above
* Create a src_repos directory in the AMP installation directory
* Check out the AMP repositories you wish to modify:  amp_mgms, amppd, amp_ui, or galaxy.
* Make code changes as desired
* You can use these methods (and others) to see your changes:
  * Use packaging
    * Guaranteed to work, but can be cumbersome
    * In the repository directory run `./amp_build.py --package ../../packages` to create a new package
    * In the amp_bootstrap directory:
      * Shut down AMP:  `./amp_control.py stop all`
      * Install the new package: `./amp_control.py install ../packages/<name of the new package>`
      * Reconfigure AMP: `./amp_control.py configure`
      * Start AMP: `./amp_control.py start all`
  * Directly update the AMP installation
    * This may or may not work depending on what you're changing...will likely work for the UI and MGMs
    * In the repository directory run `./amp_build.py` with a destination directory relevant for the repository
    * Ta da!
  * Point standalone code to the installation
    * Start a new instance of whatever you're working on...such as the REST backend or Galaxy
    * Modify the AMP configuration to use your new instance
    * Shut down AMP 
    * Configure AMP
    * Restart AMP
    * Now it should be using your code rather than the previously installed code.
    