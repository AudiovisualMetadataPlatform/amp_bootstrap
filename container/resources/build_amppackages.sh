#!/bin/bash

# Download the packages
echo Using Package mirror $AMP_MIRROR
if [ "x$AMP_MIRROR" == "xNONE" ]; then
    # theoretically, the packages are now in /srv/amp/packages so no download
    echo Skipping download
else
    mkdir -p /srv/amp/packages
    if [ "x$AMP_MIRROR" != "x" ]; then
        BASEURL=$AMP_MIRROR
    else
        BASEURL=https://dlib.indiana.edu/AMP-packages/current
    fi
    cd /srv/amp/packages
    for pkg in `curl $BASEURL/manifest.txt`; do
        curl -o $n $BASEURL/$n
    done
fi