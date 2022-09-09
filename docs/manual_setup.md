# Manual installation
If Ansible is not used, these steps should install the software requirements
on a RHEL 8 system. 

As root, install the system dependencies:

```
dnf install -y python39 python39-pyyaml java-11-openjdk git
dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
yum install -y singularity
dnf config-manager --set-enabled powertools
dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm
dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
dnf install -y ffmpeg
dnf install -y gcc python39-devel zlib-devel
```

AMP needs access to a postgres 12+ server.  If your organization has one, 
create a user and a database for AMP, otherwise it can be run on the AMP server.

Install the packages as root:
```
dnf install "@postgresql:12"
```

Initialize postgres:
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

Create an amp system user and installation directory.  The AMP system will need 
to run as a normal user so create an unpriviledged user and a directory for AMP 
to live in. Create amp system user:

```
useradd -m amp
passwd amp
```

### Singularity binding
If the AMP installation path is not within the amp user's home directory, 
singularity containers may fail to start.  To resolve this issue, add the 
"bind path" to /etc/singularity/singularity.conf

## Open the firewall
Most Linux distributions firewall ports by default.  Open the firewall for the 
main AMP port:

```
firewall-cmd --add-port 8080/tcp
firewall-cmd --add-port 8080/tcp --permanent
```

If you need access to galaxy, you will need to open 8082 the same way.

## Log in as the AMP user
The remainder of the instructions will be done as the amp system user.  You can 
either log into the system via ssh as the amp user or use sudo to become the 
amp user:

```
sudo -u amp bash -l
```

## Install the bootstrap
With all of the prerequisites satisfied, the amp_bootstrap repository 
(this repository!) can be installed.

```
git clone https://github.com/AudiovisualMetadataPlatform/amp_bootstrap.git
```

The AMP system requirements are now installed.