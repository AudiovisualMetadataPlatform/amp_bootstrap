# Phase 1:  build the OS base
FROM rockylinux:8 AS osbase
COPY resources/build_osbase.sh /tmp
RUN /tmp/build_osbase.sh

# Phase 2: install the amp bootstrap and do basic initialization
FROM osbase AS ampinit
COPY resources/build_ampinit.sh /tmp
RUN /tmp/build_ampinit.sh
