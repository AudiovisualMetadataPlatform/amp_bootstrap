# AMP-2150-experiment overview

Per the issue on JIRA, this ticket is to investigate how to allow 
third parties to create MGMs for AMP independently of our code base

There are a lot of places in the main branch where we have made assumptions
about how the repositories are installed, configured, and started.  We've 
hardcoded those assumptions in various places which make it difficult
for anyone to extend the system.

These assumptions appear in several places

## amp_control.py
The amp_control.py program controls the lifecycle of the deployed system,
installing packages, reconfiguring, starting, stopping, etc.

It makes a lot of assumptions:
### init
During initialization it will download tomcat and mediaprobe in addition to
creating the directories needed for operation.  It shouldn't do that
because we may need to update those separately from the bootstrap.  

### install
The package installation code is hardcoded into the script, whereas it
should reside in a library somewhere so it can be reused as needed and
be adjacent to the package creation code for ease of maintenance

The code also makes the assumption that the user is aware of the
dependency order of the packages -- specifically that galaxy needs to
be installed before other things.  This is a burden that the end user
shouldn't have

Lastly, there is code to handle the amppd and amppd-ui packages.  Since
those are packaged as WAR files, they have to be unpacked to be deployed
and the install code does this.

### configure
The configuration code calls a function for each hardcoded package and all
of configuration quirks for each of those packages is included.  This 
code should be in the package itself for ease of maintenance

### start, stop
This functionality has the package start/stop information hardcoded into it

### other fuctionality
* Developer functionality is implemented in the control script -- it
  should be separate.
* System prerequisites are hardcoded into the code
* Configuration file handling is implemented directly in the code

## amp.default
The amp.default file contains the "base" configuration for AMP.  This
includes the configuration for the MGMs.  As implemented, an additional
MGM could not inject its defaults into the system

## galaxy_configure.py
This is used to configure galaxy and shouldn't be part of the bootstrap
itself

## bootstrap_rest_unit.py
This creates the initial rest unit in the REST backend.  It should be
part of the amppd repo and/or handled there during initialization

## Individual repositories
The code to create a package exists in each repository, making it difficult
to update the package format and ensure consistency

## mgm_python.sif
The MGM Python that is used by many of the in-house MGMs is stored in a
location that makes it inaccessible by other MGMs.  We also have a need
for a generic Python environment which can also be used for the evaluation
tool

## MGM Python libraries
The python libraries used by our MGMs are stored in a way that they cannot
be used by other MGMs.  Also, there are many assuptions about logging and
configuration which may not be true for others.  These libraries need
to be refactored and made more generic.  There are also several places
where we have dead code which should be removed.

These libraries should actually be part of the amp_bootstrap repo since
they are shared across all parts of AMP, not just the MGMS.

## Package format
The package format is limited to metadata file + payload.  To support
complex use cases the package format needs to handle architecture, 
dependencies, lifecycle hooks, and additional metadata.


# The Proof of Concept

The proof of concept is reaches into all parts of AMP and is contained 
in these AudiovisualMetadataPlatform repositories:

* amppd (AMP-2150-experiment branch)
* amppd-ui (AMP-2150-experiment branch)
* amp_bootstrap (AMP-2150-experiment branch)
* amp_mediaprobe (new repository)
* amp_mgms (AMP-2150-experiment branch)
* amp_python (new repository)
* amp_tomcat (new repository)
* galaxy (AMP-2150-experiment branch)
* sample_mgm (new repository)

The major components of the POC include:
## New package format
The new package format contains several new features to foster 
consistency and allow others to extend the system painlessly.

Features of the new package format:
* Expanded metadata in amp_package.yaml:
  * format -- package format version
  * name -- name of package
  * version -- version of package
  * build_data -- build date of package
  * install_path -- where to put the payload (relative to AMP_ROOT)
  * arch -- architecture (noarch, aarch64, x86_64)
* Package lifecycle hook scripts
  * pre -- prior to installing package
  * post -- after installing package
  * config -- when AMP is being configured
  * start -- when AMP is being started
  * stop -- when AMP is being stopped
* Configuration defaults
  * a yaml file with per-package configuration will
    be used when building the system configuration
* Dependencies:
  * packages can specify which other packages they need
  * used during installation, configuration, start, and stop
* Package filename change:
  * Package filenames are now PACKAGE__VERSION__ARCH.tar


## amp_python.sif
Providing a generic Python + system tools envrionment which will pull
in the shared AMP python libraries by default.  This is intended to
replace the mgm_python.sif  It is available in the PATH by default.


## Shared AMP python library
A common python library (in amp_bootstrap/amp) is available for all
AMP components to use -- MGMs, Evaluation tools, etc.

Right now the library is limited to what is needed for core AMP usage:
* config - Loading/accessing the AMP configuration
* environment - Setting up a consistent runtime environment
* logging - Providing a consistent logging environment (including rolling)
* package - package creation, validation, and installation.  Also includes
  package database managment
* prereq - Configuration-driven prerequisite testing

### config
Extending the user/default overlay functionality that's in main, the 
library now combines more yaml files into the configuration and can
find the configuration file automatically, providing that AMP_ROOT
is set.

The overlay process consists of merging multiple files to provide an
in-memory data structure that can be used by MGMs (and others) directly.

The files are merged in this order:
* amp_boostrap/amp.default   <- the amp core default configuration
* data/default_config/*.default <- default configuration for packages
* data/package_config/*.yaml <- runtime-generated package configuration
* amp_bootstrap/amp.yaml <-- user-specified configuration

When merging the configuration files it is possible to overlay an 
individual configuration or add an entire tree of configuration.

For example, the core default configuration is (comments removed):

```
---
amp_bootstrap:
    # configuration for the AMP bootstrap    
amp:
    # This is overall configuration -- things that apply to all components
    host: localhost
    port: 8080
    https: false
    data_root: data
```

When the sample_mgm is installed a default configuration file is copied
into data/default_config/sample_mgm.yaml:

```
mgms:
  sample_mgm:
    watermark: This is the default watermark
```

when these two files are merged, the configuration becomes:

```
amp_bootstrap: 
amp:
    host: localhost
    port: 8080
    https: false
    data_root: data
mgms:
  sample_mgm:
    watermark: This is the default watermark
```

The user can overlay an parts of the configuration that they need
to:

```
amp:
  port: 8100
mgms:
  sample_mgm:
    watermark:  My site watermark
```

yielding this configuration:

```
amp_bootstrap: 
amp:
    host: localhost
    port: 8100
    https: false
    data_root: data
mgms:
  sample_mgm:
    watermark: My site watermark
```

The sample MGM can read the configuration file and use it like this:

```
#!/bin/env amp_python.sif
from amp.config import load_amp_config, get_config_value

config = load_amp_config()
# get the field directly
print(config['mgms']['sample_mgm']['watermark'])
# let the library walk the tree and return the default if it can't find
# any component in the path
print(get_config_value(config, ['mgms', 'sample_mgm', 'watermark'], "no watermark"))
```

### environment 
This library is used to set up a default runtime environment for
subprocesses.  Generally it will only be used by amp_control.py and
amp_devel.py.  

The runtime environment that any AMP component (outside of things
in the bootstrap) can expect include:

* A PYTHONPATH which includes the AMP standard library
* AMP_ROOT and AMP_DATA_ROOT pointing to the current installation
* amp_python.sif at the head of the PATH
* TMPDIR, TEMP, APPTAINER_TMPDIR, and SINGULARITY_TMPDIR pointing
  to /var/tmp (to avoid out of memory issues on systems which use
  a ramdisk for /tmp)


### logging
The logging library allows a script to easily set up a standard
logging configuration, optionally allowing persistent logging to
AMP_DATA_ROOT/logs.

The setup_logging function takes two args:
* a log file basename (which usually should be the script name, or 
  None if persistent logs aren't desired)
* a debug flag which sets the logging level to logging.DEBUG

If a persistent log is used, the basename will be used as the base name
for the log file and the file will be rolled at midnight.  

In either case, the logging format is:
```
LOG_TIME [LEVEL] (FILENAME:LINE:PID) MESSAGE
```

It can be used like this:

```
#!/bin/env amp_python.sif
from amp.logging import setup_logging
import logging

setup_logging('my_script')
logging.debug("A debug message") # won't appear because debug=False
logging.info("An info message") # appears on stderr and in persistent log
```

### package
The package library provides functionality for all things packaging.

Some of the functions:
* create_package <-- create a new package from a payload dir with 
  the provided metadata, default config and hooks
* verify_package <-- verify a package and return its metadata
* install_package <--  install an AMP package

There is also a PackageDB class which maintains a package installation
database.  That will be described as part of amp_control.py.

When a build script needs to create a new package, it is just an
issue of calling the create_package function:

```
new_package = create_package(package_destination_directory,
                             on_disk_payload_source_directory,
                             metadata={"name": "my package",
                                       "version": "0.0",
                                       "install_path": "galaxy/tools"},
                             hooks={'post': 'my_post_script.py',
                                    'start': 'my_start_script.py'},
                             depends_on=['galaxy'],
                             arch_specific=False)
print(f"New package is in {new_package}")
```

### prereq
The prerequisites library is used to check the system for binaries which
match the minimal requirements.  Generally this is only used by the
amp_control.py and amp_devel.py scripts since the MGMs and other things
should only be using base-os dependencies and/or the amp_python.sif, which
has a fixed install.

The check_prereqs function is passed a struture which defines what the
script needs:

```
runtime_prereqs = {
    'python': [[['python3', '--version'], r'Python (\d+)\.(\d+)', 'between', (3, 7), (3, 9)]],
    'java': [[['java', '-version'], r'build (\d+)\.(\d+)', 'exact', (11, 0)]],
    'singularity': [[['singularity', '--version'], r'version (\d+)\.(\d+)', 'atleast', (3, 7)],
                    [['apptainer', '--version'], None, 'any']],
    'ffmpeg': [[['ffmpeg', '--version'], None, 'any']],
    'file': [[['file', '--version'], None, 'any']],
    'gcc': [[['gcc', '--version'], None, 'any']],
    'git': [[['git', '--version'], None, 'any']]
}
try:
    check_prereqs(runtime_prereqs)
    print("Ready to go!")
except Exception as e:
    print(f"Failed prereq check: {e}")

```

## amp_control.py refactor
All of the per-package code has been removed and it now behaves in a
per-installed-package-set way.  The development code has been moved to
amp_devel.py.

### init
Init now only creates the core directories need for AMP 

### download
No changes, but apparently it is broken when trying to download
packages > 1G

### install
Installation now checks the version and will refuse to install
prior versions without --force.  Architecture compatibility is checked.

Dependencies are checked and if multiple packages are to be installed,
the installation will occur in computed dependency order.

Hook scripts for pre and post are run if they are present.

The packagedb.yaml file contains installation, history, and dependency
information for installed packages.  Do not edit this file, as it is
maintaned by amp_control.py.  A sample file looks like this (truncated)

```
__PACKAGE_DATABASE__:
  INITIALIZED: '20220901_124102'
  NOTICE: Do not modify this file, it is programatically maintained
  VERSION: 1
amp_mgms-applause_detection:
  dependencies:
  - galaxy
  - amp_python
  history: []
  install_date: '20220901_124250'
  version: 0.1.0
...
amp_python:
  dependencies: []
  history:
  - install_date: '20220901_124109'
    version: '1.0'
  - install_date: '20220901_183106'
    version: '1.0'
  install_date: '20220901_184002'
  version: '1.0'
...
```


### configure
The configure hook scripts are called in dependency order.

the --dump option will display the computed configuration after
merging all of the configuration files

### start / stop / restart
These now call the package hooks (start & stop) in the dependency order.

## amp_devel.py
This is a new tool which wraps things that are used by a developer

### init
Creates the required directories for development and clones the
known core repositories to src_repos

Third party developers can place their code in src_repos and it will
be handled correctly


### build
This will call the amp_build.py script for any source in the src_repos
directory.  The scripts will build packages and place them into the
package directory.  

A manifest file is updated in the package directory so the whole directory
can be pushed to an upstream webserver and will be compatible with
the amp_control.py install functionality

### shell
This creates a shell that consists of the environment that the packages
are to run in (see amp.environment for details).  It is useful for
creating MGMs and testing code

```
[bdwheele@fedora amp_bootstrap]$ echo $PYTHONPATH $AMP_ROOT $AMP_DATA_ROOT

[bdwheele@fedora amp_bootstrap]$ which amp_python.sif
/usr/bin/which: no amp_python.sif in (/usr/lib/jvm/java-11/bin:/home/bdwheele/work_projects/Python-3.9/bin:/home/bdwheele/work_projects/node-v14.20.0-linux-x64/bin:/home/bdwheele/.local/bin:/home/bdwheele/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin)
[bdwheele@fedora amp_bootstrap]$ ./amp_devel.py shell
(amp)[bdwheele@fedora amp_bootstrap]$ echo $PYTHONPATH $AMP_ROOT $AMP_DATA_ROOT
/home/bdwheele/work_projects/AMP-devel/amp_bootstrap /home/bdwheele/work_projects/AMP-devel /home/bdwheele/work_projects/AMP-devel/data
(amp)[bdwheele@fedora amp_bootstrap]$ which amp_python.sif
~/work_projects/AMP-devel/amp_python/amp_python.sif
(amp)[bdwheele@fedora amp_bootstrap]$ exit
exit
[bdwheele@fedora amp_bootstrap]$
```

## AMP-2150-experiment branches

### amp_mgms
This branch just has a minimal conversion to the new system:
* The default configuration for the MGMs are stored in each MGM directory
* the shared package build code is used

For implementation this would require more work to refactor the library
code to the amp_bootstrap branch, clean up logging, etc.

### amppd
Conversion to the new package system:
* use shared library for package build
* defaults are pushed into package
* config and start hooks implemented

### amppd-ui
Conversion to the new package system:
* use shared library for package build
* defaults are pushed into package
* config hook implemented

### galaxy
Conversion to the new package system:
* use shared library for package build
* defaults are pushed into package
* config, start, and stop hooks implemented


## New repositories
Several new repositories were needed to complete the POC

### amp_mediaprobe
The original implementation of amp_control.py cloned the MediaProbe repository into data/MediaProbe.   The problem with this is that it runs
at a system level and thus requires ffmpeg to be installed on the base
system.

This repostory is a copy of the MediaProbe code with some modifications so
it will use amp_python.sif instead of the system Python and that removes
the need to install FFMPEG on the base system.

It is also a prereq for the amppd package.

### amp_python
This contains the code for the amp_python.sif script described elsewhere

It is a prereq for many packages

### amp_tomcat
The original amp_control.py code would download tomcat and install it 
during initialization.  This is a meta package that only contains hooks
which do the same thing:
* pre -- install tomcat from the apache website
* configure -- change the necessary tomcat config files
* start -- runs bin/startup.sh
* stop -- runs bin/shutdown.sh


### sample_mgm
This is a sample MGM that I wrote which will convert an audio file into
a waveform graphic, with a site-defined watermark and a user-selectable
color.








# Installing the Proof of Concept

It should be possible to set up the POC fairly easily.

## Set up the POC

Create an empty directory (I called my AMP-poc), clone the amp_bootstrap
repository into it, and set the branch to AMP-2150-experiment:

```
[bdwheele@fedora tmp]$ mkdir AMP-poc
[bdwheele@fedora tmp]$ cd AMP-poc
[bdwheele@fedora AMP-poc]$ git clone git@github.com:AudiovisualMetadataPlatform/amp_bootstrap.git
Cloning into 'amp_bootstrap'...
remote: Enumerating objects: 526, done.
remote: Counting objects: 100% (65/65), done.
remote: Compressing objects: 100% (53/53), done.
remote: Total 526 (delta 18), reused 31 (delta 11), pack-reused 461
Receiving objects: 100% (526/526), 484.36 KiB | 3.67 MiB/s, done.
Resolving deltas: 100% (321/321), done.
[bdwheele@fedora AMP-poc]$ cd amp_bootstrap
[bdwheele@fedora amp_bootstrap]$ git checkout AMP-2150-experiment
branch 'AMP-2150-experiment' set up to track 'origin/AMP-2150-experiment'.
Switched to a new branch 'AMP-2150-experiment'
[bdwheele@fedora amp_bootstrap]$ ./amp_control.py init
2022-09-02 11:27:35,076 [INFO    ] (amp_control.py:97)  Creating /tmp/AMP-poc/packages
2022-09-02 11:27:35,076 [INFO    ] (amp_control.py:97)  Creating /tmp/AMP-poc/data
2022-09-02 11:27:35,076 [INFO    ] (amp_control.py:97)  Creating /tmp/AMP-poc/data/symlinks
2022-09-02 11:27:35,076 [INFO    ] (amp_control.py:97)  Creating /tmp/AMP-poc/data/config
2022-09-02 11:27:35,076 [INFO    ] (amp_control.py:97)  Creating /tmp/AMP-poc/data/default_config
2022-09-02 11:27:35,076 [INFO    ] (amp_control.py:97)  Creating /tmp/AMP-poc/data/package_hooks
2022-09-02 11:27:35,076 [INFO    ] (amp_control.py:97)  Creating /tmp/AMP-poc/data/package_config
[bdwheele@fedora amp_bootstrap]$
```

## Initialize the development environment
This will set up the needed directories and clone the core repositories.  
Since this is an experimental branch, all of the repos need to have their
branch set.  

```
[bdwheele@fedora amp_bootstrap]$ ./amp_devel.py init
2022-09-02 11:28:52,766 [INFO    ] (amp_devel.py:77)  Creating development envrionment
2022-09-02 11:28:52,766 [INFO    ] (amp_devel.py:85)  Cloning amppd
Cloning into 'amppd'...
remote: Enumerating objects: 19756, done.
...
2022-09-02 11:29:33,000 [INFO    ] (amp_devel.py:85)  Cloning sample_mgm
Cloning into 'sample_mgm'...
remote: Enumerating objects: 14, done.
remote: Counting objects: 100% (14/14), done.
remote: Compressing objects: 100% (13/13), done.
remote: Total 14 (delta 2), reused 10 (delta 1), pack-reused 0
Receiving objects: 100% (14/14), 11.10 KiB | 11.10 MiB/s, done.
Resolving deltas: 100% (2/2), done.
[bdwheele@fedora amp_bootstrap]$ for n in amppd amppd-ui amp_mgms galaxy; do pushd ../src_repos/$n; git checkout AMP-2150-experiment; popd; done
/tmp/AMP-poc/src_repos/amppd /tmp/AMP-poc/amp_bootstrap
branch 'AMP-2150-experiment' set up to track 'origin/AMP-2150-experiment'.
Switched to a new branch 'AMP-2150-experiment'
...
Switched to a new branch 'AMP-2150-experiment'
/tmp/AMP-poc/amp_bootstrap
[bdwheele@fedora amp_bootstrap]$
```
## Build the packages
Build all of the packages.  It will take a while.

```
[bdwheele@fedora amp_bootstrap]$ ./amp_devel.py build
2022-09-02 11:33:50,402 [INFO    ] (amp_devel.py:113)  Building packages for amppd
2022-09-02 11:33:50,439 [INFO    ] (amp_build.py:47)  Building REST WAR
[INFO] Scanning for projects...
...
2022-09-02 11:36:11,359 [INFO    ] (package.py:88)  Creating package for galaxy with version 21.01 in /home/bdwheele/work_projects/AMP-poc/packages
2022-09-02 11:36:12,701 [INFO    ] (amp_build.py:117)  New package in /home/bdwheele/work_projects/AMP-poc/packages/galaxy__21.01__noarch.tar
[bdwheele@fedora amp_bootstrap]$ ls -al ../packages
total 13302788
drwxr-xr-x. 1 bdwheele bdwheele       1066 Sep  1 20:16 .
drwxr-xr-x. 1 bdwheele bdwheele         68 Sep  1 19:17 ..
-rw-r--r--. 1 bdwheele bdwheele 1654425600 Sep  2 11:35 amp_mgms-applause_detection__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele      51200 Sep  2 11:35 amp_mgms-aws__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele      51200 Sep  2 11:35 amp_mgms-azure__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele 1587640320 Sep  2 11:35 amp_mgms-gentle__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele      40960 Sep  2 11:35 amp_mgms-hmgms__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele 1790822400 Sep  2 11:35 amp_mgms-ina_speech_segmenter__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele 4326246400 Sep  2 11:35 amp_mgms-kaldi__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele 1875496960 Sep  2 11:35 amp_mgms-mgm_python__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele     317440 Sep  2 11:35 amp_mgms-mgms__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele 2125834240 Sep  2 11:35 amp_python__1.0__x86_64.tar
-rw-r--r--. 1 bdwheele bdwheele   69847040 Sep  2 11:33 amp_rest__0.0.1-SNAPSHOT__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele    4638720 Sep  2 11:35 amp_ui__0.1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele  186490880 Sep  2 11:36 galaxy__21.01__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele        537 Sep  2 11:36 manifest.txt
-rw-r--r--. 1 bdwheele bdwheele      71680 Sep  2 11:35 mediaprobe__1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele      30720 Sep  2 11:35 sample_mgm__1.0__noarch.tar
-rw-r--r--. 1 bdwheele bdwheele      20480 Sep  2 11:35 tomcat__9.0.65__noarch.tar
[bdwheele@fedora amp_bootstrap]$
```

# Install the packages
Now that we have new-style pacakges, let's install them.

Get information about the amp_rest package:
```
[bdwheele@fedora amp_bootstrap]$ ./amp_control.py install ../packages/amp_rest__0.0.1-SNAPSHOT__noarch.tar --info
Package Data for ../packages/amp_rest__0.0.1-SNAPSHOT__noarch.tar:
  Name: amp_rest
  Version: 0.0.1-SNAPSHOT
  Build date: 20220902_113354
  Architecture: noarch
  Dependencies: ['tomcat', 'galaxy', 'mediaprobe']
  Installation path: AMP_ROOT/tomcat/webapps
```

Looks good to me.  Install all of them

```
[bdwheele@fedora amp_bootstrap]$ ./amp_control.py install ../packages/*.tar --yes
Package Data for ../packages/amp_python__1.0__x86_64.tar:
  Name: amp_python
  Version: 1.0
...
2022-09-02 11:39:54,864 [INFO    ] (amp_hook_post.py:22:820460)  Deploying war file: /home/bdwheele/work_projects/AMP-poc/tomcat/webapps/ROOT.war -> /home/bdwheele/work_projects/AMP-poc/tomcat/webapps/ROOT
2022-09-02 11:39:54,936 [INFO    ] (package.py:228)  Installation of ../packages/amp_ui__0.1.0__noarch.tar complete

```

It's important to note the order that the packages were installed.  When
using a wildcard the file will be given the program in alphabetical
order, but they were installed in this order:
* amp_python
* galaxy
* mediaprobe
* sample_mgm
* tomcat
* amp_mgms-applause_detection
* amp_mgms-aws
* amp_mgms-azure
* amp_mgms-gentle
* amp_mgms-hmgms
* amp_mgms-ina_speech_segmenter
* amp_mgms-kaldi
* amp_mgms-mgm_python
* amp_mgms-mgms
* amp_rest
* amp_ui

The order was based on the dependency tree.  amp_rest, for example requires
that tomcat, galaxy and mediaprobe.

# Configure AMP

I haven't set up a user config (amp.yaml) file yet, so when I do things I
get a warning message:

```
2022-09-02 11:47:31,504 [WARNING ] (config.py:63)  Cannot overlay main configuration (/home/bdwheele/work_projects/AMP-poc/amp_bootstrap/amp.yaml): [Errno 2] No such file or directory: '/home/bdwheele/work_projects/AMP-poc/amp_bootstrap/amp.yaml'

```
I will copy a previous install's amp.yaml to this instance eventually.

The computed configuration (via ./amp_control.py configure --dump)

```
amp:
  data_root: data
  host: localhost
  https: false
  port: 8080
amp_bootstrap: null
galaxy:
  admin_password: my admin password
  admin_username: myuser@example.edu
  galaxy:
    allow_path_paste: true
    allow_user_creation: false
    logging:
      disable_existing_loggers: false
      filters:
        stack:
          (): galaxy.web_stack.application_stack_log_filter
      formatters:
        stack:
          (): galaxy.web_stack.application_stack_log_formatter
      handlers:
        console:
          class: logging.StreamHandler
          filters:
          - stack
          formatter: stack
          level: DEBUG
          stream: ext://sys.stderr
        galaxylog:
          class: logging.handlers.TimedRotatingFileHandler
          filename: logs/galaxy.log
          filters:
          - stack
          formatter: stack
          level: DEBUG
          when: midnight
        perflog:
          class: logging.FileHandler
          filename: logs/performance.log
          level: DEBUG
        rootlog:
          class: logging.handlers.TimedRotatingFileHandler
          filename: logs/root.log
          filters:
          - stack
          formatter: stack
          level: INFO
          when: midnight
      loggers:
        amqp:
          level: INFO
          qualname: amqp
        botocore:
          level: INFO
          qualname: botocore
        galaxy:
          handlers:
          - galaxylog
          level: DEBUG
          propagate: false
          qualname: galaxy
        paste.httpserver.ThreadPool:
          level: WARN
          qualname: paste.httpserver.ThreadPool
        performance:
          handlers:
          - perflog
          level: DEBUG
          propagate: false
        routes.middleware:
          level: WARN
          qualname: routes.middleware
        sqlalchemy:
          level: WARN
          qualname: sqlalchemy
        sqlalchemy_json.track:
          level: WARN
          qualname: sqlalchemy_json.track
        urllib3.connectionpool:
          level: WARN
          qualname: urllib3.connectionpool
      root:
        handlers:
        - rootlog
        level: INFO
      version: 1
    require_login: true
    tool_config_file: tool_conf.xml
    watch_tools: polling
    x_frame_options: null
  host: localhost
  id_secret: CHANGE ME
  root: /rest/galaxy
  toolbox:
    Applause Detection:
    - amp_mgms/applause_detection.xml
    - amp_mgms/applause_detection_to_avalon_xml.xml
    Audio Extraction:
    - amp_mgms/extract_audio.xml
    - amp_mgms/remove_trailing_silence.xml
    Audio Segmentation:
    - amp_mgms/ina_speech_segmenter.xml
    - amp_mgms/keep_speech.xml
    - amp_mgms/remove_silence_speech.xml
    - amp_mgms/adjust_transcript_timestamps.xml
    - amp_mgms/adjust_diarization_timestamps.xml
    Facial Recognition:
    - amp_mgms/dlib_face_recognition.xml
    Get Data:
    - data_source/upload.xml
    - amp_mgms/supplement.xml
    Human MGM Editor:
    - amp_mgms/hmgm_transcript.xml
    - amp_mgms/hmgm_ner.xml
    Named Entity Recognition:
    - amp_mgms/spacy.xml
    - amp_mgms/aws_comprehend.xml
    - amp_mgms/ner_to_csv.xml
    Send Data:
    - cloud/send.xml
    Shot Detection:
    - amp_mgms/pyscenedetect.xml
    - amp_mgms/azure_shot_detection.xml
    Speech to Text:
    - amp_mgms/aws_transcribe.xml
    - amp_mgms/gentle_forced_alignment.xml
    - amp_mgms/kaldi.xml
    - amp_mgms/transcript_to_webvtt.xml
    - amp_mgms/vocabulary_tagging.xml
    Video Indexing:
    - amp_mgms/azure_video_indexer.xml
    - amp_mgms/contact_sheet_frame.xml
    - amp_mgms/contact_sheet_face.xml
    - amp_mgms/contact_sheet_shot.xml
    - amp_mgms/contact_sheet_vocr.xml
    Video Optical Charater Recognition:
    - amp_mgms/tesseract.xml
    - amp_mgms/azure_video_ocr.xml
    - amp_mgms/vocr_to_csv.xml
  uwsgi:
    buffer-size: 16834
    die-on-term: true
    enable-threads: true
    hook-master-start:
    - unix_signal:2 gracefully_kill_them_all
    - unix_signal:15 gracefully_kill_them_all
    master: false
    offload-threads: 2
    processes: 1
    py-call-osafterfork: false
    pythonpath: lib
    static-map:
    - /static=static
    - /favicon.ico=static/favicon.ico
    static-safe: client/src/assets
    threads: 4
    thunder-lock: false
    umask: '002'
    virtualenv: .venv
mgms:
  aws:
    aws_access_key_id: my_awsaccess_key
    aws_secret_access_key: my_aws_secret_access
    region_name: us-east-2
  aws_comprehend:
    default_access_arn: arn:aws:iam::<some_number>:role/AwsComprehend
    default_bucket: my-bucket
  aws_transcribe:
    default_bucket: my-bucket
    default_directory: null
  azure:
    accountId: azure_account_id
    apiKey: azure_api_key
    s3Bucket: my-bucket
  hmgm:
    auth_key: some random garbage
    auth_string: auth
    ner_api: /#/hmgm/ner-editor
    ner_input: resourcePath
    segmentation_api: /#/hmgm/segmentation-editor
    segmentation_input: inputPath
    transcript_api: /#/hmgm/transcript-editor
    transcript_input: datasetUrl
    transcript_media: mediaUrl
  jira:
    password: jira_password
    project: jira_project_key
    server: https://jira.example.edu
    username: jira_username
  sample_mgm:
    watermark: This is the default watermark
rest:
  admin_email: ampadmin@example.edu
  admin_password: amppass
  admin_username: ampadmin
  avalon_token: some-really-long-hex-string
  avalon_url: https://avalon.example.edu
  db_host: localhost
  db_name: ampdb
  db_pass: amppass
  db_user: ampuser
  dropbox_path: dropbox
  encryption_secret: encryption-secret-text
  jwt_secret: jwt-secret-text
  logging_path: logs
  mediaprobe_dir: MediaProbe
  properties:
    amppd.accountActivationTokenExpiration: 604800
    amppd.activateAccountDays: 7
    amppd.auth: true
    amppd.corsOriginPattern: http://localhost:8080
    amppd.environment: prod
    amppd.externalSources: MCO,DarkAvalon,NYPL
    amppd.jwtExpireMinutes: 60
    amppd.passwordResetTokenExpiration: 600
    amppd.pythonPath: python3
    amppd.refreshResultsStatusCron: 0 0/10 6-18 ? * MON-FRI
    amppd.refreshResultsTableCron: 0 0 1 ? * MON-FRI
    amppd.refreshResultsTableMinutes: 300
    amppd.refreshWorkflowResultsAllCron: 0 0 1 ? * MON-FRI
    amppd.refreshWorkflowResultsStatusCron: 0 0/10 6-18 ? * MON-FRI
    amppd.resetPasswordMinutes: 10
    amppd.supplementCategories: Face,Transcript,Vocabulary,Program,Groundtruth,Other
    amppd.taskManagers: Jira,Trello
    amppd.workflowEditMinutes: 60
    logging.level.edu.indiana.dlib.amppd: TRACE
    management.endpoints.web.exposure.include: '*'
    server.servlet.context-path: /rest
    server.servlet.session.timeout: 1800s
    spring.datasource.driver-class-name: org.postgresql.Driver
    spring.datasource.platform: postgres
    spring.jpa.database: POSTGRESQL
    spring.jpa.generate-ddl: true
    spring.jpa.hibernate.ddl-auto: update
    spring.jpa.properties.hibernate.dialect: org.hibernate.dialect.PostgreSQLDialect
    spring.jpa.properties.hibernate.format_sql: true
    spring.jpa.properties.hibernate.jdbc.lob.non_contextual_creation: true
    spring.jpa.properties.hibernate.temp.use_jdbc_metadata_defaults: false
    spring.jpa.properties.javax.persistence.validation.mode: none
    spring.jpa.show-sql: true
    spring.mail.host: localhost
    spring.mail.port: 25
    spring.mail.properties.mail.smtp.auth: false
    spring.mail.properties.mail.smtp.connectiontimeout: 5000
    spring.mail.properties.mail.smtp.starttls.enable: false
    spring.mail.properties.mail.smtp.timeout: 3000
    spring.mail.properties.mail.smtp.writetimeout: 5000
    spring.mail.protocol: smtp
    spring.servlet.multipart.enabled: true
    spring.servlet.multipart.max-file-size: 5GB
    spring.servlet.multipart.max-request-size: 5GB
    spring.session.jdbc.initialize-schema: always
    spring.session.jdbc.schema: classpath:org/springframework/session/jdbc/schema-@@platform@@.sql
    spring.session.jdbc.table-name: SPRING_SESSION
    spring.session.store-type: jdbc
    spring.session.timeout: 1800s
  storage_path: media
ui:
  unit: AMP Pilot Unit
  user_guide:
    AMP_USER_GUIDE: https://uisapp2.iu.edu/confluence-prd/display/AMP/AMP+User+Guide
    COLLECTIONS: https://uisapp2.iu.edu/confluence-prd/display/AMP/Collections
    DELIVERABLES: https://uisapp2.iu.edu/confluence-prd/display/AMP/Deliverables
    ITEMS: https://uisapp2.iu.edu/confluence-prd/display/AMP/Items
    PRIMARY_FILE: https://uisapp2.iu.edu/confluence-prd/display/AMP/Primary+File
    THE_DASHBOARD: https://uisapp2.iu.edu/confluence-prd/display/AMP/The+Dashboard
    UNITS: https://uisapp2.iu.edu/confluence-prd/display/AMP/Units
    UPLOADING_FILES_VIA_BATCH_INGEST: https://uisapp2.iu.edu/confluence-prd/display/AMP/Uploading+Files+via+Batch+Ingest
    WORKFLOW_SUBMISSIONS: https://uisapp2.iu.edu/confluence-prd/display/AMP/Workflow+Submissions
  user_guide_url: https://example.edu/AMP/

```

Which is the merging of amp.default, and all of the files in data/default_config:

```
[bdwheele@fedora amp_bootstrap]$ ls -al ../data/default_config/
total 32
drwxr-xr-x. 1 bdwheele bdwheele  252 Sep  2 11:39 .
drwxr-xr-x. 1 bdwheele bdwheele  130 Sep  2 11:39 ..
-rw-r--r--. 1 bdwheele bdwheele  353 Sep  2 11:39 amp_mgms-aws.default
-rw-r--r--. 1 bdwheele bdwheele  119 Sep  2 11:39 amp_mgms-azure.default
-rw-r--r--. 1 bdwheele bdwheele  527 Sep  2 11:39 amp_mgms-hmgms.default
-rw-r--r--. 1 bdwheele bdwheele 4053 Sep  2 11:39 amp_rest.default
-rw-r--r--. 1 bdwheele bdwheele  925 Sep  2 11:39 amp_ui.default
-rw-r--r--. 1 bdwheele bdwheele 6294 Sep  2 11:39 galaxy.default
-rw-r--r--. 1 bdwheele bdwheele  523 Sep  2 11:39 sample_mgm.default
```

Actually do the configuration:
```
[bdwheele@fedora amp_bootstrap]$ ./amp_control.py configure
2022-09-02 11:54:59,954 [INFO    ] (amp_control.py:224)  Running config hook galaxy__config
2022-09-02 11:55:00,011 [INFO    ] (galaxy__config:77:822106)  Installing galaxy python and node
Creating Python virtual environment for Galaxy: .venv
using Python: python3
.... tons of galaxy dependency install stuff ....
2022-09-02 11:56:55,380 [INFO    ] (galaxy__config:104:822106)  Galaxy user ID: a0c079a38336483b
2022-09-02 11:56:55,380 [INFO    ] (galaxy__config:114:822106)  Creating the galaxy toolbox configuration
2022-09-02 11:56:55,381 [INFO    ] (galaxy__config:126:822106)  Creating the MGM configuration file
2022-09-02 11:56:55,388 [INFO    ] (amp_control.py:224)  Running config hook sample_mgm__config
Hello from the configuration script!
The installation directory is: /home/bdwheele/work_projects/AMP-poc
2022-09-02 11:56:55,456 [INFO    ] (amp_control.py:224)  Running config hook tomcat__config
2022-09-02 11:56:55,529 [INFO    ] (amp_control.py:224)  Running config hook amp_rest__config
2022-09-02 11:56:55,604 [INFO    ] (amp_control.py:224)  Running config hook amp_ui__config

```
There are several config hooks that are run during the process:  galaxy, sample_mgm, tomcat, amp_rest, amp_ui.  These scripts are in data/package_hooks/*__config.  

Again, the order was determined by their dependencies:  amp_rest requires tomcat and galaxy, so it runs after those two.  sample_mgm only requires galaxy so it can run time after galaxy has completed.

There are a few cases where runtime configuration is needed by different scripts, and galaxy's user ID is one of them.  For those cases, the information is stored in data/package_config/*yaml and can be retrieved by everything else.

## Start up AMP
Now that amp is installed and configured, it's time to start up AMP

```
[bdwheele@fedora amp_bootstrap]$ ./amp_control.py start all
2022-09-02 12:01:20,086 [INFO    ] (amp_control.py:242)  Running start hook galaxy__start
Unsetting $PYTHONPATH
Activating virtualenv at .venv
...
WSGI app 0 (mountpoint='/rest/galaxy') ready in 3 seconds on interpreter 0x1738290 pid: 823370 (default app)
*** daemonizing uWSGI ***
2022-09-02 12:03:10,447 [INFO    ] (amp_control.py:242)  Running start hook tomcat__start
Using CATALINA_BASE:   /home/bdwheele/work_projects/AMP-poc/tomcat
Using CATALINA_HOME:   /home/bdwheele/work_projects/AMP-poc/tomcat
Using CATALINA_TMPDIR: /home/bdwheele/work_projects/AMP-poc/tomcat/temp
Using JRE_HOME:        /usr/lib/jvm/java-11
Using CLASSPATH:       /home/bdwheele/work_projects/AMP-poc/tomcat/bin/bootstrap.jar:/home/bdwheele/work_projects/AMP-poc/tomcat/bin/tomcat-juli.jar
Using CATALINA_OPTS:   
Tomcat started.
2022-09-02 12:03:10,495 [INFO    ] (amp_control.py:242)  Running start hook amp_rest__start
2022-09-02 12:03:10,582 [WARNING ] (amp_rest__start:81:823418)  Failed to set up default unit: <urlopen error [Errno 111] Connection refused>
2022-09-02 12:03:30,904 [INFO    ] (amp_rest__start:78:823418)  Unit already exists
```

So three hooks were run during startup: galaxy__start (which starts 
galaxy), tomcat__start (which starts tomcat), and amp_rest__start (which
creates the default unit if it needs to)

So AMP is now running and can be used normally

## Making the Sample MGM available

While the Sample MGM is installed, it's not in the tools menu.  Recall
from above that the default toolbox configuration is:

```
  toolbox:
    Applause Detection:
    - amp_mgms/applause_detection.xml
    - amp_mgms/applause_detection_to_avalon_xml.xml
    Audio Extraction:
    - amp_mgms/extract_audio.xml
    - amp_mgms/remove_trailing_silence.xml
    Audio Segmentation:
    - amp_mgms/ina_speech_segmenter.xml
    - amp_mgms/keep_speech.xml
    - amp_mgms/remove_silence_speech.xml
    - amp_mgms/adjust_transcript_timestamps.xml
    - amp_mgms/adjust_diarization_timestamps.xml
    Facial Recognition:
    - amp_mgms/dlib_face_recognition.xml
    Get Data:
    - data_source/upload.xml
    - amp_mgms/supplement.xml
    Human MGM Editor:
    - amp_mgms/hmgm_transcript.xml
    - amp_mgms/hmgm_ner.xml
    Named Entity Recognition:
    - amp_mgms/spacy.xml
    - amp_mgms/aws_comprehend.xml
    - amp_mgms/ner_to_csv.xml
    Send Data:
    - cloud/send.xml
    Shot Detection:
    - amp_mgms/pyscenedetect.xml
    - amp_mgms/azure_shot_detection.xml
    Speech to Text:
    - amp_mgms/aws_transcribe.xml
    - amp_mgms/gentle_forced_alignment.xml
    - amp_mgms/kaldi.xml
    - amp_mgms/transcript_to_webvtt.xml
    - amp_mgms/vocabulary_tagging.xml
    Video Indexing:
    - amp_mgms/azure_video_indexer.xml
    - amp_mgms/contact_sheet_frame.xml
    - amp_mgms/contact_sheet_face.xml
    - amp_mgms/contact_sheet_shot.xml
    - amp_mgms/contact_sheet_vocr.xml
    Video Optical Charater Recognition:
    - amp_mgms/tesseract.xml
    - amp_mgms/azure_video_ocr.xml
    - amp_mgms/vocr_to_csv.xml
```

Copying that section to the amp.yaml file and extending it so it includes
the sample_mgm will make it available:

```
    toolbox:
        Get Data:
            - data_source/upload.xml
            - amp_mgms/supplement.xml
        Send Data:
            - cloud/send.xml
        Audio Extraction:
        ...
        Human MGM Editor:
            - amp_mgms/hmgm_transcript.xml
            - amp_mgms/hmgm_ner.xml
        Sample:
            - sample_mgm/sample_mgm.xml

```
after the stop/configure/start

# Lessons Learned / Future Directions

## Integrate proof of concept into main
Most of the changes in the POC do not impact the non-packaging parts of 
amp, so this should be integrated.

## Separate user config defaults and system config defaults
Defaults should probably be split into user and system sets when
packaging.  By separating the two we can generate a basic user
configuration that doesn't carry over all of the internal stuff.

## MGM Cleanup
Our MGMs still need a lot of cleanup and standardization.   There's some
less-than-optimal code that makes maintance hard

## MGMs should probably be installed one-directory-per-package
This would make things easier to manage from a packaging perspective.
One of the reasons they were all stuffed into the amp_mgms directory was
the lack of a standardized library and environment.

## Additional Package Metadata
With the new package format and library it should be easy to include
additional metadata for the package to cover things like help files
evaluation metadata/config, etc.

## Config merging probably has some weird corner cases
Not sure if it's possible to replace an entire data structure in
some cases rather than just mixing it in.

Maybe have a '.replace' key in the dict metadata that indicates that this
dictionary is to entirely replace the existing dictionary, rather than
being merged

## Managing the toolbox is still kinda hard
This may be a case for a simple command line tool to manage the toolbox
settings.  The config file would live in data/package_config?  Splitting
the user/system config will go a a long way to making it easier

## Generate the computed configuration as a static file?
Might be useful for the REST back end to be able to look up things in
the combined configuration.  
