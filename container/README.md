DISCLAIMER:  While the instructions below refer to Docker, this was developed
and tested using podman -- an open source equivalent to docker.  Podman is
architecturally more secure and allows users to build and run containers 
without the need for root access on the machine.  More information at
https://podman.io

# Building the container image

The Dockerfile should contain all that's needed for building the container image:

```
docker build -t amp:test .
```

On a fast server, building the image takes 12 minutes to build and 30G of docker image storage.
Your build times will differ due to memory/network/disk differences.

The build pulls the current distribution packages from https://dlib.indiana.edu/AMP-packages which
will transfer roughly 12G.

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
docker run -v /srv/storage/amp-data:/srv/amp-data --rm  amp:test
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
* create the database and whatnot

## Examples

### On first starting the container:

```
[bdwheele@esquilax amp-data]$ podman run -it -v /srv/storage/amp-data:/srv/amp-data:z  --rm amp:test
[bdwheele@esquilax amp-data]$ ls -al
total 12
drwxrwxr-x. 2 bdwheele bdwheele   56 Jul 15 10:51 .
drwxrwxrwt. 6 root     root      123 Jul 14 14:01 ..
-rw-r--r--. 1 bdwheele bdwheele  236 Jul 15 10:51 amp_system.log
-rw-r--r--. 1 bdwheele bdwheele 7993 Jul 15 10:51 amp.yaml
[bdwheele@esquilax amp-data]$ cat amp_system.log 
2022-07-15 14:51:22,446 [INFO    ] (amp_entry.py:69)  Creating default configuration file
2022-07-15 14:51:22,485 [WARNING ] (amp_entry.py:86)  A new configuration has been generated.  Update the configuration and restart the container
```

### Starting the container the first time with a valid configuration
```
[bdwheele@esquilax amp-data]$ podman run -it -v /srv/storage/amp-data:/srv/amp-data:z  --rm amp:test
The files belonging to this database system will be owned by user "postgres".
This user must also own the server process.

The database cluster will be initialized with locales
  COLLATE:  C
  CTYPE:    C.UTF-8
  MESSAGES: C
  MONETARY: C
  NUMERIC:  C
  TIME:     C
The default database encoding has accordingly been set to "UTF8".
The default text search configuration will be set to "english".

Data page checksums are disabled.

fixing permissions on existing directory /srv/amp-data/postgres ... ok
creating subdirectories ... ok
selecting dynamic shared memory implementation ... posix
selecting default max_connections ... 100
selecting default shared_buffers ... 128MB
selecting default time zone ... UTC
creating configuration files ... ok
running bootstrap script ... ok
performing post-bootstrap initialization ... ok
syncing data to disk ... ok

initdb: warning: enabling "trust" authentication for local connections
You can change this by editing pg_hba.conf or using the option -A, or
--auth-local and --auth-host, the next time you run initdb.

Success. You can now start the database server using:

    /usr/pgsql-12/bin/pg_ctl -D /srv/amp-data/postgres -l logfile start

waiting for server to start.... done
server started
CREATE DATABASE
CREATE ROLE
ALTER DATABASE
```



## Podman-specific nodes

### SELinux

When mounting the data directory, use the 'z' option for the volume:

```
podman run -it -v /srv/storage/amp-data:/srv/amp-data:z  amp:test
```





