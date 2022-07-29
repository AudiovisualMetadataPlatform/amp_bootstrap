DISCLAIMER:  While the instructions below refer to Docker, this was developed
and tested using podman -- an open source equivalent to docker.  Podman is
architecturally more secure and allows users to build and run containers 
without the need for root access on the machine.  More information at
https://podman.io

# Building the container image

The build.py script does all of the magic to start a container build

```
usage: build.py [-h] [--mirror MIRROR] [--debug] [--docker DOCKER] [--tag TAG]

options:
  -h, --help       show this help message and exit
  --mirror MIRROR  Source for AMP packages
  --debug          Turn on debugging
  --docker DOCKER  Docker command to use (default is to try podman then docker)
  --tag TAG        Image tag
```

Generally you will not need to use any of the options, but if you have local packages
that you wish to install (rather than using ones downloaded), you can specify them 
using the mirror option:

```
./build.py --mirror=file:///home/bdwheele/work_projects/AMP-devel/packages/
```

On a fast server, building the image takes 12 minutes to build and 30G of docker image storage.
Your build times will differ due to memory/network/disk differences.

When local packages are not specified, the build pulls the current distribution packages from 
https://dlib.indiana.edu/AMP-packages which will transfer roughly 12G.

The resulting image is ~14G:

```
REPOSITORY                    TAG         IMAGE ID      CREATED         SIZE
localhost/amp                 test        63396dc6a857  46 seconds ago  13.6 GB
docker.io/library/rockylinux  8           8cf70153e062  7 days ago      202 MB
```


# Using the container
The container provides 2 ports:
* 8080 -- this is the main AMP ui
* 8082 -- this is the galaxy backend

The only port that should be exposed publicly is 8080.


Start the container, mounting a data directory at /srv/amp-data.  The
command will look something like this:

```
docker run -v /srv/storage/amp-data:/srv/amp-data --rm  --publish 8080:8080,8082:8082 amp:test
```

NOTE: removing the container via --rm after exit is OK since AMP is configured
from the configuration file on every start and the logs/data exist on the
external volume.

The container entrypoint will log into the amp_system.log file.  You can
enable debugging by either passing an AMP_DEBUG environment variable when
starting the container or creating a ".amp_debug" file in the data directory.

When the container starts it will look for a configuration file.  If there isn't
one, it will take the default configuration and generate a new configuration 
file in the data directory called amp.yaml and then exit.  

The file should be modified for your organziation prior to starting the container
again.

Specifically, these fields are ones that will (likely) need to be
modified:
* galaxy/admin_usermame:  this needs to be the email of the galaxy administration account.
  it is used by AMP to communicate with galaxy.  By default it is set to ampuser@example.edu
  which will work unless you prefer a specific email address for AMP galaxy usage
* mgms/aws/*:  these are for AWS-related functionality
* mgms/aws_comprehend/*:  these are for AWS comprehend-related functionality
* mgms/aws_transcript/*:  these are for AWS transcribe-related functionality
* mgms/azure/*:  Azure service functionality
* mgms/jira/*:  JIRA-related functionality
* rest/admin_email:  The email address of the AMP administration user. This must be a
  real email since user approval goes to this address.
* rest/avalon_{token,url}: Avalon-related integration
* rest/db_{host,name,pass,user}:  These should be changed if you are planning on 
  using your own postgres server.  If you wish to use the built-in one, they can
  be left as-is
* ui/unit:  the default unit name 

Once the system has a valid configuration it will (as needed):
* create any symlinks and directories needed for operation
* initialize the local postgres server (if the db_host is "localhost")
* start postgres 
* create the database and whatnot
* configure AMP based on the configuration file
* start galaxy
* start tomcat
* continue to run until postgres, galaxy or tomcat dies.


## Examples
Note that the file .amp_debug exists in the data directory, so debugging messages are shown.

### On first starting the container:

```
[bdwheele@esquilax amp-data]$ podman image ls
REPOSITORY                    TAG         IMAGE ID      CREATED         SIZE
localhost/amp                 test        eaf4b5869b57  10 minutes ago  13.6 GB
docker.io/library/rockylinux  8           8cf70153e062  7 days ago      202 MB
[bdwheele@esquilax amp-data]$ man podman-run
[bdwheele@esquilax amp-data]$ podman run -d -v /srv/storage/amp-data:/srv/amp-data:z  --rm  -p 8080:8080 -p 8082:8082 amp:test
9ca0dc5d9ea4a4c395dff2efa66a77b1368d0792920aaa0335257dd78287cd5f
[bdwheele@esquilax amp-data]$ podman ps
CONTAINER ID  IMAGE       COMMAND     CREATED     STATUS      PORTS       NAMES
[bdwheele@esquilax amp-data]$ ls -al
total 12
drwxrwxr-x. 2 bdwheele bdwheele   78 Jul 15 13:27 .
drwxrwxrwt. 6 root     root      123 Jul 14 14:01 ..
-rw-rw-r--. 1 bdwheele bdwheele    0 Jul 15 12:24 .amp_debug
-rw-r--r--. 1 bdwheele bdwheele  309 Jul 15 13:27 amp_system.log
-rw-r--r--. 1 bdwheele bdwheele 8078 Jul 15 13:27 amp.yaml
[bdwheele@esquilax amp-data]$ tail amp_system.log
2022-07-15 17:27:54,600 [DEBUG   ] (amp_entry.py:36)  Debugging enabled.
2022-07-15 17:27:54,600 [INFO    ] (amp_entry.py:74)  Creating default configuration file
2022-07-15 17:27:54,642 [WARNING ] (amp_entry.py:91)  A new configuration has been generated.  Update the configuration and restart the container
```

### Starting the container the first time with a valid configuration
```
[bdwheele@esquilax amp-data]$ podman run -d -v /srv/storage/amp-data:/srv/amp-data:z  --rm  -p 8080:8080 -p 8082:8082 amp:test
2b3c157653f3c877dc8bcc0ecdacbaf89c28811ce17f486722223d7cdc86a592
[bdwheele@esquilax amp-data]$ podman ps
CONTAINER ID  IMAGE               COMMAND     CREATED        STATUS            PORTS                                           NAMES
2b3c157653f3  localhost/amp:test              7 seconds ago  Up 7 seconds ago  0.0.0.0:8080->8080/tcp, 0.0.0.0:8082->8082/tcp  brave_wiles
[bdwheele@esquilax amp-data]$ ls -al
total 16
drwxrwxr-x.  6 bdwheele   bdwheele  150 Jul 15 13:29 .
drwxrwxrwt.  6 root       root      123 Jul 14 14:01 ..
-rw-rw-r--.  1 bdwheele   bdwheele    0 Jul 15 12:24 .amp_debug
-rw-r--r--.  1 bdwheele   bdwheele 2280 Jul 15 13:29 amp_system.log
-rw-r--r--.  1 bdwheele   bdwheele 8078 Jul 15 13:27 amp.yaml
drwxr-xr-x.  3 bdwheele   bdwheele   30 Jul 15 13:29 data
drwxr-xr-x.  5 bdwheele   bdwheele   85 Jul 15 13:29 galaxy
drwx------. 20 1600065561 bdwheele 4096 Jul 15 13:29 postgres
drwxr-xr-x.  4 bdwheele   bdwheele   42 Jul 15 13:29 tomcat
[bdwheele@esquilax amp-data]$ cat amp_system.log
2022-07-15 17:27:54,600 [DEBUG   ] (amp_entry.py:36)  Debugging enabled.
2022-07-15 17:27:54,600 [INFO    ] (amp_entry.py:74)  Creating default configuration file
2022-07-15 17:27:54,642 [WARNING ] (amp_entry.py:91)  A new configuration has been generated.  Update the configuration and restart the container
2022-07-15 17:29:21,442 [DEBUG   ] (amp_entry.py:36)  Debugging enabled.
2022-07-15 17:29:21,442 [INFO    ] (amp_entry.py:70)  Installing amp.yaml configuration file
2022-07-15 17:29:21,467 [INFO    ] (amp_entry.py:103)  Initializing postgresql directories
2022-07-15 17:29:21,467 [DEBUG   ] (amp_entry.py:107)  Running: mkdir /srv/amp-data/postgres
2022-07-15 17:29:21,472 [DEBUG   ] (amp_entry.py:107)  Running: chown postgres /srv/amp-data/postgres
2022-07-15 17:29:21,477 [DEBUG   ] (amp_entry.py:107)  Running: runuser --user postgres /usr/pgsql-12/bin/initdb /srv/amp-data/postgres
2022-07-15 17:29:22,167 [INFO    ] (amp_entry.py:118)  Starting postgres
2022-07-15 17:29:22,293 [INFO    ] (amp_entry.py:122)  Creating schema & user (if necessary)
2022-07-15 17:29:22,347 [INFO    ] (amp_entry.py:131)  Postgres should now be running.
2022-07-15 17:29:22,347 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/galaxy/tools/amp_mgms/logs -> /srv/amp-data/galaxy/tools/amp_mgms/logs
2022-07-15 17:29:22,350 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/galaxy/tools/logs -> /srv/amp-data/galaxy/tools/logs
2022-07-15 17:29:22,350 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/galaxy/logs -> /srv/amp-data/galaxy/logs
2022-07-15 17:29:22,351 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/galaxy/galaxy.log -> /srv/amp-data/galaxy/galaxy.log
2022-07-15 17:29:22,351 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/galaxy/database -> /srv/amp-data/galaxy/database
2022-07-15 17:29:22,352 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/data/symlinks -> /srv/amp-data/data/symlinks
2022-07-15 17:29:22,353 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/tomcat/logs -> /srv/amp-data/tomcat/logs
2022-07-15 17:29:22,354 [DEBUG   ] (amp_entry.py:151)  Creating symlink: /srv/amp/tomcat/temp -> /srv/amp-data/tomcat/temp
2022-07-15 17:29:34,997 [INFO    ] (amp_entry.py:170)  AMP has been configured.
2022-07-15 17:29:51,649 [INFO    ] (amp_entry.py:180)  Galaxy started.
2022-07-15 17:29:51,822 [INFO    ] (amp_entry.py:183)  Tomcat started
2022-07-15 17:29:51,822 [INFO    ] (amp_entry.py:187)  Creating the default unit
2022-07-15 17:30:32,812 [DEBUG   ] (amp_entry.py:208)  Reaped pid 396: 0
```


## Podman-specific nodes

### SELinux

When mounting the data directory, use the 'z' option for the volume:

```
podman run -it -v /srv/storage/amp-data:/srv/amp-data:z  amp:test
```





