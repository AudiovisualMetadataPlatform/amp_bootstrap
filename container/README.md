# Building the container


# Using the container
Start the container, mounting a data directory at /srv/amp-data.  The
command will look something like this:

```
docker run -v /srv/storage/amp-data:/srv/amp-data --rm  amp:test
```

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




## Podman

Mount the data directory with the 'z' option:

podman run -it -v /srv/storage/amp-data:/srv/amp-data:z  amp:test




