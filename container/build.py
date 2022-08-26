#!/bin/env python3

import argparse
import logging
import subprocess
import shutil
import tarfile
from pathlib import Path
import sys

DEFAULT_MIRROR = "https://dlib.indiana.edu/AMP-packages/current"
DEFAULT_TAG = "amp:test"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mirror", type=str, default=DEFAULT_MIRROR, help="Source for AMP packages")
    parser.add_argument("--debug", default=False, action='store_true', help="Turn on debugging")
    parser.add_argument("--docker", help="Docker command to use (default is to try podman then docker)") 
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Image tag")
    args = parser.parse_args()

    # determine whether or not we should be using debugging.  If the AMP_DEBUG environment
    # is set or DATA_ROOT/.amp_debug exists we'll use debugging.
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)    

    if not args.docker:
        args.docker = shutil.which("podman")
        if not args.docker:
            args.docker = shutil.which("docker")
        if not args.docker:
            logging.error("Docker command was not specified and cannot find either podman or docker")
            exit(1)

    logging.info(f"Using docker command: {args.docker}")
    
    # create our dynamic resources directory
    dynresource_dir = Path(sys.path[0], "dynamic-resources")
    dynresource_dir.mkdir(exist_ok=True)

    bootstrap_dir = Path(sys.path[0], "..").resolve()
    logging.info(f"Creating bootstrap tarball from {bootstrap_dir!s}")
    Path(sys.path[0], "packages").mkdir(exist_ok=True)
    # The packages directory can't be empty or the Dockerfile will puke.
    Path(sys.path[0], "packages/placeholder").touch()
    with tarfile.open(Path(sys.path[0], "dynamic-resources/amp_bootstrap.tar"), "w") as t:
        for file in bootstrap_dir.glob("*"):            
            if file.is_file():
                if file.name.startswith('.'):
                    continue
                if file.name == "amp.yaml":
                    # do not copy the local configuration
                    continue
                logging.debug(f"Adding {file!s} as {file.name}")
                t.add(file, file.name)


    # Docker is really irritating about how it only allows files within the
    # build tree to be copied to the container.  So to use any local packages
    # they have to be copied here and then copied into the container.
    # There are optimizations (like hard linking) that I may include in the
    # future.  These local mirror specifications must start with file:/// or /
    if args.mirror.startswith('file:///'):
        args.mirror = args.mirror.replace('file:///', '/')
    if args.mirror.startswith('/'):
        # this is a local mirror, so I need to copy things.                
        for file in Path(args.mirror).glob("*"):            
            if file.is_file():
                destfile = Path(sys.path[0], 'packages', file.name)
                if not destfile.exists() or destfile.stat().st_mtime < file.stat().st_mtime:
                    logging.debug(f"Copying package file {file.name}")
                    shutil.copyfile(file, destfile)
        # fixup args.mirror so it knows to use the ones in the packages directory
        args.mirror = "NONE"




    logging.info("Starting build")
    subprocess.run([args.docker, 'build', '-t', args.tag, '--build-arg',f"AMP_MIRROR={args.mirror}", "."])



if __name__ == "__main__":
    main()