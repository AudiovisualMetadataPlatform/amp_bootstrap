# Developing AMP
The AMP bootstrap repository contains the tools needed to modify the AMP
codebase or add new functionality.

Like the general system management, development management is run through a
single tool.  The development tool is:  amp_devel.py

amp_devel.py will run a prerequisites check when started so if anything is
missing it will be caught early in the process.


# Initializing the development environment
To begin development the environment must be initialized.  This initialization
step will create the necessary directory structures and check out all of the
core AMP repositories:

```
./amp_devel init
```

When it is finished running, the core repositories are in AMP_ROOT/src_repos.

# Building packages
Every repository has a `amp_build.py` script which drives the build process.

The packages can be built from the source by running:
```
./amp_devel.py build 
```

or an individual repository:

```
./amp_devel.py build galaxy
```

The resulting packages will be placed into the AMP_ROOT/packages directory
and can be installed there as any other package.

# Running in the AMP environment
MGMs and other tools within AMP run within an environment that may need to be
replicated while debugging and testing.  

Specifically these things are set up:
* AMP_ROOT and AMP_DATA_ROOT environment variables are set
* PYTHONPATH is set to include the AMP core libraries
* amp_python.sif  (a python interpreter environment customized for AMP) is
  in the path
* TMPDIR, TEMP, etc are all set to /var/tmp to avoid memory issues on systems
  where /tmp is actually a ramdisk.

To start a shell with an environment that should be the same as the AMP 
environment, run:

```
./amp_devel.py shell
```
The prompt will have "(amp)" at the front to identify it as the amp environment.



# Developing specific components

It is always possible to do the  

edit -> build package -> shut down amp -> install package -> 
  configure amp -> start amp

cycle for development, but it can be cumbersome.  There are some shortcuts that
can be used for different repositories.

If the ./amp_build.py script in the repository is run without the --package
option the code will be built and (for most packages) installed in the 
destination directory.  This allows the repository to overwrite installed
files in the running environment without going through the package cycle.

That said, it's important to test the package cycle prior to distributing the
code.

## galaxy

The easiest way to do this is to make the running instance of galaxy the 
development repository.  

* remove the galaxy directory that was installed via the packages
* symlink galaxy -> src_repos/galaxy
* install the amp_mgm* packages
* reconfigure amp

Now the galaxy code that is run is the stuff in the repo and you can modify it 
as needed.

Remember that the content in tools/amp_mgms and the configuration files are 
from other sources so they shouldn't be modified from within this repository 
as they will be overwritten by other install/configure actions

NOTE:  Our branch of galaxy will not build with python 3.10, which is the 
default for many current distributions.  Install a previous version, place it 
at the head of the path, install the virtualenv package into that installation.
Sometimes it will find a 3.10 install, which you can identify by a line like 
this at the start of a galaxy build:

```
created virtual environment CPython3.10.4.final.0-64 in 116ms
```

## amppd

The amppd war file can be build and put into tomcat/webapps and it should 
automatically deploy.


## amppd-ui

The UI can be built directly where tomcat can see it, without the need to 
restart anything.  

If a configuration change is needed
you should be able to reconfigure amp without restarting it in this case.

```
./amp_build.py ../tomcat/webapps/ROOT
```


## amp_mgms

Generally, it is possible to modify this repository and build it, specifying an 
installation directory that is the running instance of galaxy:

```
./amp_build.py ../../galaxy
```

The only corner case is the first build of a new tool because that's 
effectively a configuration change (the list of tools in amp.default)

Beyond that, changes should be effective as soon as the next workflow uses 
the tool

## amp_bootstrap

This repository can be edited in place and modified as needed.  Since it 
controls the rest of amp there are no dependencies.

# Configuration Changes
Any time a runtime configuration file has new variables added it's important 
to make sure that the amp system is fully reconfigured, since the configuration 
is a combination of all of the known configuration files.

The amp.yaml file can be updated with the new configuration addititions and 
then reconfigured.  When the development is ready, the values should be 
installed via the package user or system defaults and the temporary values
in amp.yaml should be removed to verify the system is picking them up correctly

# Creating your own MGMs outside of the AMP environment

There is a sample_mgm repository which contains all of the parts needed to
create a simple MGM that can be used as the basis for something more complex.

Generally you want to follow these guidelines:
* Use amp_python.sif as your interpreter.  That contains python 3.10 with lots
  of standard packages, as well as a handful of common tools (ffmpeg, sox, etc)
* If you need something more complex than what amp_python.sif can provide, 
  create a singularity container instead
* Use the Python modules in the amp namespace (which are provided in the
  bootstrap repository) whereever possible.

