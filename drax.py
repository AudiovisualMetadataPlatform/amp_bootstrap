#!/bin/env python3
import argparse
from pathlib import Path
from subprocess import run
import logging
import sys
import os
import time
import hashlib


"Drax the deployer"
# this script is use on our development system to update and
# restart the system every time a new package is placed into
# the packages directory.  Obviously, you wouldn't want to 
# run this on a production system since there would be
# random intermittent outages and possible breakage.

# time for the packages to settle before doing an install
SETTLE_TIME = 15 * 60

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action="store_true", help="turn on debugging")
    parser.add_argument("--now", default=False, action="store_true", help="Don't wait for packages to settle")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
    # make sure that we're not already running.
    # this should be run on cron, this won't be racy
    md5 = hashlib.md5(sys.path[0].encode('utf8')).hexdigest()
    lockfile = Path(f"/tmp/drax-{md5}.lock")    
    if lockfile.exists():
        logging.debug(f"Lockfile {lockfile!s} exists")
        exit(0)
    lockfile.write_text(str(os.getpid()) + "\n")
    try:        
        pkg_dir = Path(sys.path[0], "../packages")
        last_run_file = pkg_dir / ".last_run"
        last_run = 0 if not last_run_file.exists() else last_run_file.stat().st_mtime
        
        packages = []        
        logging.debug(f"Scanning for packages newer than {last_run}")
        for pfile in pkg_dir.glob("*.tar"):
            ptime = pfile.stat().st_mtime            
            if ptime > last_run:
                logging.debug(f"{pfile!s} has time {ptime}")                
                #if args.now or time.time() - SETTLE_TIME > ptime:                    
                #    logging.debug(f"Package file {pfile!s} has settled")
                packages.append(pfile)
            
        if packages:
            last_run_file.touch(exist_ok=True)
            logging.info(f"New packages are available: {[str(x) for x in packages]}")
            
            logging.info(f"Shutting down AMP")            
            run(['./amp_control.py', 'stop', 'all'], check=True)

            logging.info(f"Updating the bootstrap")
            run(['git', 'pull'])

            logging.info(f"Installing the packages")
            run(['./amp_control.py', 'install',  '--yes', *[str(x.absolute()) for x in packages]], check=True)

            logging.info(f"Update the configuration")
            run(['./amp_control.py', 'configure'], check=True)

            logging.info(f"Starting the instance")
            run(['./amp_control.py', 'start', 'all'], check=True)

    finally:   
        lockfile.unlink()
        





    



if __name__ == "__main__":
    main()