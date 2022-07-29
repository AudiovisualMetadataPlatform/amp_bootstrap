# Phase 1:  build the OS base
FROM rockylinux:8 AS osbase
COPY resources/build_osbase.sh /tmp
RUN /tmp/build_osbase.sh

# Phase 2: Copy the amp packages into the container
FROM osbase as amppackages
ARG AMP_MIRROR
COPY resources/build_amppackages.sh /tmp
COPY packages/* /srv/amp/packages/
RUN /tmp/build_amppackages.sh

# Phase 3: install the amp bootstrap and do basic initialization
FROM amppackages AS ampinit
COPY resources/build_ampinit.sh /tmp
COPY dynamic-resources/amp_bootstrap.tar /tmp
RUN /tmp/build_ampinit.sh

# Phase 4: install the AMP packages
FROM ampinit AS ampinstall
COPY resources/build_ampinstall.sh /tmp
RUN /tmp/build_ampinstall.sh


# Phase 5: setup entrypoint
# note that the entrypoint code is injected into the amp_bootstrap
# directory so it can import stuff amp_control.py and get easy
# access to the configuration files.
FROM ampinstall AS entrypoint
COPY resources/amp_entry.py /srv/amp/amp_bootstrap/amp_entry.py
ENTRYPOINT /srv/amp/amp_bootstrap/amp_entry.py

