# AMP-2150-experiment

Per the issue on JIRA, this ticket is to investigate how to allow 
third parties to create MGMs for AMP independently of our code base

There are a lot of places in the main branch where we have made assumptions
about how the repositories are installed, configured, and started.  We've 
hardcoded those assumptions in various places which make it difficult
for anyone to extend the system.

These assumptions appear in several places

## amp_control.py
The amp_control.py program controls the 





## Installing the Proof of Concept

The proof of concept is contained in these AudiovisualMetadataPlatform repositories:

* amppd (AMP-2150-experiment branch)
* amppd-ui (AMP-2150-experiment branch)
* amp_bootstrap (AMP-2150-experiment branch)
* amp_mediaprobe (new repository)
* amp_mgms (AMP-2150-experiment branch)
* amp_python (new repository)
* amp_tomcat (new repository)
* galaxy (AMP-2150-experiment branch)
* sample_mgm (new repository)
```

Setting up the POC:

    In an empty directory, clone the amp_bootstrap repository and checkout the AMP-2150-experiment branch
    initialize the environment: 

    cd amp_bootstrap
    ./amp_control.py init
    ./amp_devel.py init 

    that will get all of the repositories used by the POC and put them into the src_repos directory
    Check out the correct branches:

 for n in amppd amppd-ui amp_mgms galaxy; do pushd ../src_repos/$n; git checkout AMP-2150-experiment; popd; done

    Build all of the package using the new format:

./amp_devel.py build 

This could take a couple of hours.

    — will continue when the build is finished —


