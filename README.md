# amp_bootstrap
AMP system managment tool


Drop this directory where you want to install the AMP system - the different
component packages will be installed as peers to amp_bootstrap

Developers:  check out the repositories in the same directory as amp_bootstrap
so the bootstrap program can find the other components and the utilities library

# AMP System Requirements
To run AMP the following system requirements must be met:
* Python >= 3.6 
* Java Runtime 11
* nginx or apache
* Singularity runtime 3.8
* PostgreSQL >= 12

If you wish to collect uwsgi metrics, you will need:
* Make
* GCC

# Installation
## Install/Configure postgres
### For RHEL-derived distributions:

As root:
* yum install postgresql-server
* postgresql-setup --initdb
* cat > /var/lib/pgsql/data/pg_hba.conf <<EOF
```
# type db   user      addr           method
local  all  postgres                 peer
local  all  all       127.0.0.1/32   md5
local  all  all       ::1/128        md5
EOF
```
* systemctl start postgresql.service
* systemctl enable postgresql.service
* su - postgres
  * createuser amp --pwprompt
  * createdb --owner=amp amp
  * exit




## Select an installation directory
The installation directory will contain all of the components as well as the data.
Given an installation directory called $AMP_ROOT, copy/download/clone the amp_bootstrap repository into that directory.  At the end of the installation, the layout for AMP will be:
````
$AMP_ROOT
  amp_bootstrap  <-- this tool
  amp_mgms  <-- MGMs/Galaxy tools used by AMP
  amp_rest <-- The AMP REST service
  amp_ui <-- The AMP UI HTML/Javascript files
  galaxy <-- Galaxy
  galaxy_data  <-- data/files used by galaxy
````








## Install the component packages
NOTE:  Largly TBD

The pre-built packages are located at [TBD].  Download them into a temporary directory and install them using the amp_bootstrap:
````
cd $AMP_ROOT/amp_bootstrap

````