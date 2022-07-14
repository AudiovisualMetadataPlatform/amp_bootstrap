# Phase 1:  build the OS base
FROM rockylinux:8 AS osbase
COPY resources/build_osbase.sh /tmp
RUN /tmp/build_osbase.sh

# Phase 2: install the amp bootstrap and do basic initialization
FROM osbase AS ampinit
COPY resources/build_ampinit.sh /tmp
RUN /tmp/build_ampinit.sh

# Phase 3: install the AMP packages
FROM ampinit AS ampinstall
COPY resources/build_ampinstall.sh /tmp
RUN /tmp/build_ampinstall.sh

# Phase 4: prepare container for running
FROM ampinstall AS containerprep
COPY resources/amp_entry.py /
ENTRYPOINT /amp_entry.py