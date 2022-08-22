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
import time
import amp_control

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

        # load the configuration since other things are going to need it
        # and by loading it we can make sure it's a valid yaml file.
        #with open(DATA_ROOT / "amp.yaml") as f:
        #    config = yaml.safe_load(f)

        config = amp_control.load_config()

        # start OS daemons
        start_daemons(config)

        # start/configure postgres
        start_postgres(config)

        # Set up our symlinks if we need to
        setup_symlinks(config)

        # Configure amp
        configure_amp(config)

        # Start/run amp
        run_amp(config)


        logging.info("So long, suckers!")
    except SystemExit:
        pass
    except Exception:
        logging.exception('Main exception handler caught an exception')


def test_config():
    """Check for a config file and provide a usable one if one doesn't exist"""
    if (DATA_ROOT / "amp.yaml").exists():
        logging.info("Installing amp.yaml configuration file")
        shutil.copy(DATA_ROOT / "amp.yaml", AMP_ROOT / "amp_bootstrap/amp.yaml")
        return

    logging.info("Creating default configuration file")
    # since we don't have one, let's load the default, make it usable, and exit
    with open(AMP_ROOT / "amp_bootstrap/amp.yaml.sample") as f:
        default = yaml.safe_load(f)

    # update things which need to differ on each install
    default['galaxy']['admin_username'] = 'ampuser@example.edu'
    default['galaxy']['admin_password'] = gen_garbage(12)
    default['galaxy']['id_secret'] = gen_garbage(25)
    default['galaxy'].pop('host')  # bind to all interfaces
    default['mgms']['hmgm']['auth_key'] = gen_garbage(32)
    default['rest']['admin_password'] = gen_garbage(12)
    default['rest']['jwt_secret'] = gen_garbage(15)
    default['rest']['encryption_secret'] = gen_garbage(14)
    default['rest']['db_pass'] = gen_garbage(32)

    with open(DATA_ROOT / "amp.yaml", "w") as f:
        yaml.safe_dump(default, f)

    logging.warning("A new configuration has been generated.  Update the configuration and restart the container")
    exit(0)


def start_daemons(config):
    "Start operating system daemons"
    # postfix
    logging.info("Starting postfix")
    subprocess.run(['postfix', '-c', '/etc/postfix', 'start'], check=True)


def start_postgres(config):
    "Configure and start postgres as needed"
    if config['rest']['db_host'] != 'localhost':
        logging.info("Not using a local postgres, moving on with my life")
        return

    if not (DATA_ROOT / 'postgres').exists():
        logging.info("Initializing postgresql directories")
        for cmd in (f'mkdir {DATA_ROOT}/postgres',
                    f'chown postgres {DATA_ROOT}/postgres',
                    # was /usr/pgsql-12/bin/initdb
                    f'runuser --user postgres /usr/bin/initdb {DATA_ROOT}/postgres'):
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
    # was /usr/pgsql-12/bin/pg_ctl
    subprocess.run(f"runuser --user postgres -- /usr/bin/pg_ctl -D {DATA_ROOT}/postgres -l {DATA_ROOT}/postgres/logfile start",
                   shell=True, check=True)

    logging.info("Creating schema & user (if necessary)")
    with open(f"{DATA_ROOT}/db.sql", "w") as f:
        f.write(f"create database {config['rest']['db_name']};\n")
        f.write(f"create user {config['rest']['db_user']} with password '{config['rest']['db_pass']}';\n")
        f.write(f"alter database {config['rest']['db_name']} owner to {config['rest']['db_user']};\n")
    # was /usr/pgsql-12/bin/psql
    subprocess.run(f"runuser --user postgres /usr/bin/psql < {DATA_ROOT}/db.sql",
                   shell=True, check=True)
    (DATA_ROOT / "db.sql").unlink()

    logging.info("Postgres should now be running.")


def setup_symlinks(config):
    """modify the image so various directories are
       pointing to the mounted data, rather than
       within the base container"""
    symlinks = (
        'galaxy/tools/amp_mgms/logs/',
        'galaxy/tools/logs/',
        'galaxy/logs/',
        'galaxy/galaxy.log',
        'galaxy/database/',
        'data/symlinks/',
        'data/dropbox/',
        'data/logs/',
        'data/media/',
        'tomcat/logs/',
        'tomcat/temp/'
    )
    for s in symlinks:
        src = DATA_ROOT / s
        dst = AMP_ROOT / s
        logging.debug(f"Creating symlink: {dst!s} -> {src!s}")
        if dst.is_dir() or s.endswith('/'):
            src.mkdir(parents=True, exist_ok=True)
        else:
            src.parent.mkdir(parents=True, exist_ok=True)
            src.touch()
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        dst.symlink_to(src)
        

def configure_amp(config):
    """
    Run the amp configuration to set up everything
    """
    subprocess.run([AMP_ROOT / "amp_bootstrap/amp_control.py", 'configure'], check=True)
    logging.info("AMP has been configured.")


def run_amp(config):
    """
    This function is the main amp manager.  It won't return until
    galaxy, postgres, or tomcat shut down
    """
    # start galaxy and wait for the initialization to finish
    subprocess.run([AMP_ROOT / "amp_bootstrap/amp_control.py", "start", "galaxy"], check=True)
    logging.info("Galaxy started.")

    subprocess.run([AMP_ROOT / "amp_bootstrap/amp_control.py", "start", "tomcat"], check=True)
    logging.info("Tomcat started")

    # special case:  we have to bootstrap the amp default unit if we haven't done it yet.
    if not (DATA_ROOT / ".default_unit").exists():
        logging.info("Creating the default unit")
        # let tomcat settle down so we can do this.
        tries = 10
        while tries > 0:
            tries -= 1
            p = subprocess.run([AMP_ROOT / "amp_bootstrap/bootstrap_rest_unit.py"])
            if p.returncode == 0:
                logging.info("Default unit created")
                (DATA_ROOT / ".default_unit").touch()
                break
            else:
                time.sleep(10)
        else:
            logging.error("Could not set up the default unit. Restart the container OR")
            logging.error(f"Connect to the container and run {AMP_ROOT}/amp_bootstrap/bootstrap_rest_unit.py manually")
            logging.error(f"and touch {DATA_ROOT}/.default_unit")


    # Everything should be up and running.  Wait for a service to die and then exit
    while(True):
        time.sleep(10)

        # we're init, so let's act like it: reap any children
        # that come our way.
        pid = 1
        while pid > 0:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid > 0:
                logging.debug(f"Reaped pid {pid}: {status}")

        # Galaxy's PID is in galaxy/galaxy.pid
        with open(AMP_ROOT / "galaxy/galaxy.pid") as f:
            pid = f.readline().strip()
            if not Path(f"/proc/{pid}").exists():
                logging.error(f"Galaxy with PID {pid} has died")
                break

        # Tomcat doesn't have a PID file by default, so
        # just look around in /proc for a tomcat
        for pdir in Path("/proc").iterdir():
            if pdir.is_dir() and pdir.name[0] in '1234567890':
                cmdline = (pdir / "cmdline").read_text()
                if 'org.apache.catalina.startup.Bootstrap' in cmdline:
                    break
        else:
            # we never found that command line.
            logging.error("Failed to find a running tomcat")
            break

        # Postgres's pidfile is in /srv/amp-data/postgres/postmaster.pid
        with open(DATA_ROOT / "postgres/postmaster.pid") as f:
            pid = f.readline().strip()
            if not Path(f"/proc/{pid}").exists():
                logging.error(f"Postgres with PID {pid} has died")
                break      





def gen_garbage(length=10):
    res = ""
    for i in range(length):
        res += random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")        
    return res


if __name__ == "__main__":
    main()