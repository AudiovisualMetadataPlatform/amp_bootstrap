#!/bin/env python3
"""
This is the entrypoint of the container
"""
import argparse
import logging
import os
from pathlib import Path
import sys
import yaml
import shutil
import random
import subprocess
import signal

AMP_ROOT=Path("/srv/amp")
DATA_ROOT=Path("/srv/amp-data")

def main():
    if not DATA_ROOT.exists():
        print(f"PANIC: The expected data root {DATA_ROOT} doesn't exist.  Please mount it.", file=sys.stderr)
        exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action='store_true', help="Turn on debugging")    
    args = parser.parse_args()

    # determine whether or not we should be using debugging.  If the AMP_DEBUG environment
    # is set or DATA_ROOT/.amp_debug exists we'll use debugging.
    debugging = True if 'AMP_DEBUG' in os.environ or (DATA_ROOT / '.amp_debug').exists() or args.debug else False
    logging.basicConfig(filename=DATA_ROOT / "amp_system.log",
                        format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if debugging else logging.INFO)
    logging.debug("Debugging enabled.")

    try:
        # make sure there's a config
        test_config()

        # we're init.  let's act like it
        setup_signal_handlers()

        # load the configuration since other things are going to need it
        # and by loading it we can make sure it's a valid yaml file.
        with open(DATA_ROOT / "amp.yaml") as f:
            config = yaml.safe_load(f)

        # start/configure postgres
        start_postgres(config)

        # Set up our symlinks if we need to
        setup_symlinks(config)


        logging.info("So long, suckers!")
    except:
        logging.exception('Main exception handler caught an exception')


def test_config():
    """Check for a config file and provide a usable one if one doesn't exist"""
    if (DATA_ROOT / "amp.yaml").exists():
        logging.info("Installing amp.yaml configuration file")
        shutil.copy(DATA_ROOT / "amp.yaml", AMP_ROOT / "amp_bootstrap/amp.yaml")
        return

    logging.info("Creating default configuration file")
    # since we don't have one, let's load the default, make it usable, and exit
    with open(AMP_ROOT / "amp_bootstrap/amp.yaml.default") as f:
        default = yaml.safe_load(f)

    # update things which need to differ on each install
    default['galaxy']['admin_username'] = 'ampuser@example.edu'
    default['galaxy']['admin_password'] = gen_garbage(12)
    default['galaxy']['id_secret'] = gen_garbage(25)
    default['mgms']['hmgm']['auth_key'] = gen_garbage(32)
    default['rest']['admin_password'] = gen_garbage(12)
    default['rest']['jwt_secret'] = gen_garbage(15)
    default['rest']['db_pass'] = gen_garbage(32)

    with open(DATA_ROOT / "amp.yaml", "w") as f:
        yaml.safe_dump(default, f)

    logging.warning("A new configuration has been generated.  Update the configuration and restart the container")
    exit(0)


def setup_signal_handlers():
    """This script needs to act like an init process, so that means
       we have to handle (at least) sigchld to make sure I don't end
       up with a pile of zombies.  Set up the handlers here"""
    def sig_handler(signum, frame):
        if signum == signal.SIGCHLD:
            logging.debug("Got a SIGCHLD")
        else:
            logging.warning("Unhandled signal: ", signum)

    signal.signal(signal.SIGCHLD, sig_handler)


def start_postgres(config):
    "Configure and start postgres as needed"
    if config['rest']['db_host'] != 'localhost':
        logging.info("Not using a local postgres, moving on with my life")
        return

    if not (DATA_ROOT / 'postgres').exists():
        logging.info("Initializing postgresql directories")
        for cmd in (f'mkdir {DATA_ROOT}/postgres',
                    f'chown postgres {DATA_ROOT}/postgres',
                    f'runuser --user postgres /usr/pgsql-12/bin/initdb {DATA_ROOT}/postgres'):
            logging.debug(f"Running: {cmd}")
            subprocess.run(cmd, shell=True, check=True)
        
        with open(f"{DATA_ROOT}/postgres/pg_hba.conf", "w") as f:
            f.write("""
# type db   user      addr           method
local  all  postgres                 peer
host   all  all       127.0.0.1/32   md5
host   all  all       ::1/128        md5
""")

    logging.info("Starting postgres")
    subprocess.run(f"runuser --user postgres -- /usr/pgsql-12/bin/pg_ctl -D {DATA_ROOT}/postgres -l {DATA_ROOT}/postgres/logfile start",
                   shell=True, check=True)

    logging.info("Creating schema & user (if necessary)")
    with open(f"{DATA_ROOT}/db.sql", "w") as f:
        f.write(f"create database {config['rest']['db_name']};\n")
        f.write(f"create user {config['rest']['db_user']} with password '{config['rest']['db_pass']}';\n")
        f.write(f"alter database {config['rest']['db_name']} owner to {config['rest']['db_user']};\n")
    subprocess.run(f"runuser --user postgres /usr/pgsql-12/bin/psql < {DATA_ROOT}/db.sql",
                   shell=True, check=True)
    (DATA_ROOT / "db.sql").unlink()

    logging.info("Postgres should be running.")


def setup_symlinks(config):
    """modify the image so various directories are
       pointing to the mounted data, rather than
       within the base container"""
    symlinks = (
        'galaxy/tools/logs',
        'galaxy/logs',
        'galaxy/database',
        'data/symlinks',
        'tomcat/logs'
    )
    for s in symlinks:
        src = DATA_ROOT / s
        dst = AMP_ROOT / s
        logging.debug(f"Creating symlink: {dst!s} -> {src!s}")
        src.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        dst.symlink_to(src)
        




def gen_garbage(length=10):
    res = ""
    for i in range(length):
        res += random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")        
    return res


if __name__ == "__main__":
    main()