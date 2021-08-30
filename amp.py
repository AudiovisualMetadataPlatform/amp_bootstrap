#!/usr/bin/env python3
#
# Control the AMP System
#
import logging
import argparse
import yaml
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import os
from amp_bootstrap_utils import run_cmd, get_amp_root

def main():    
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--config', default=Path(sys.path[0], 'amp.yaml'), help="Configuration file to use")
    subp = parser.add_subparsers(dest='action', help="Program action")
    subp.required = True
    p = subp.add_parser('start', help="Start one or more services")
    p.add_argument("service", help="AMP service to start, or 'all' for all services")
    p = subp.add_parser('stop', help="Stop one or more services")
    p.add_argument("service", help="AMP service to stop, or 'all' for all services")
    p = subp.add_parser('restart', help="Restart one or more services")
    p.add_argument("service", help="AMP service to restart, or 'all' for all services")
    p = subp.add_parser('configure', help="Configure a service")
    p.add_argument("--force", default=False, action="store_true", help="Force reconfiguration")
    p.add_argument("service", help="AMP service to configure")
    p = subp.add_parser('install', help="Install a service")
    p.add_argument('--yes', default=False, action="store_true", help="Automatically answer yes to questions")
    p.add_argument("package", help="Package file to install")    
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    args.config = Path(args.config).resolve()
    if not args.config.exists():
        logging.error(f"Config file {args.config!s} doesn't exist")
        exit(1)
    try:
        with open(args.config) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Cannot load config file {args.config!s}: {e}")
        exit(1)

    # call the appropriate action function
    globals()["action_" + args.action](config, args)


def get_service_path(config, name):
    "Generate a service path based on the package name and installation_root"
    if name not in config['amp_bootstrap']['packages']:
        logging.warning(f"'{name}' isn't a known service")
        return None
    return Path(config['amp_bootstrap']['installation_root'], name)



def action_start(config, args):
    control(config, args, 'start')

def action_stop(config, args):
    control(config, args, 'stop')    

def action_restart(config, args):
    control(config, args, 'restart')
    
def control(config, args, mode):
    logging.info(f"Attempting to {mode} {args.service}")
    srvpath = get_amp_root(args.service)
    if srvpath is None:        
        logging.error("Control aborted: service doesn't exist")
        exit(1)
    if (srvpath / 'amp_control.py').exists():
        cmd = [str(srvpath / 'amp_control.py'), mode, str(args.config)]
        if args.debug:
            cmd.append('--debug')
        run_cmd(cmd, "Control failed", workdir=srvpath)
        logging.info("Successful")
    else:
        logging.warning(f"Doing nothing: There is no amp_control.py for {args.service}")

def action_configure(config, args):    
    #srvpath = get_service_path(config, args.service)
    srvpath = get_amp_root(args.service)
    if srvpath is None:
        logging.error("Terminating configuration")
        exit(1)
    if (srvpath / "amp_configure.py").exists():
        logging.info("Running configuration script")
        cmd = [str(srvpath / "amp_configure.py"), str(args.config)]
        if args.force:
            cmd.append('--force')
        if args.debug:
            cmd.append('--debug')        
        run_cmd(cmd, "Configure failed", workdir=srvpath)
    else:
        logging.info("No configuration script for this service")
    

def action_install(config, args):
    # extract the package and validate that it's OK
    package = Path(args.package)
    with tempfile.TemporaryDirectory(prefix="amp_bootstrap_") as tmpdir:
        logging.debug(f"Unpacking package {package!s} into {tmpdir}")
        shutil.unpack_archive(str(package), str(tmpdir))
        pkg_stem = package.stem.replace('.tar', '')
        if not Path(tmpdir, pkg_stem).exists():
            logging.error("Package doesn't contain a directory that matches the package stem")
            exit(1)
        pkgroot = Path(tmpdir, pkg_stem)
        try:
            with open(pkgroot / "amp_package.yaml") as f:
                pkgmeta = yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Cannot load package metadata: {e}")
        required_keys = set(['name', 'version', 'build_date'])
        if not required_keys.issubset(set(pkgmeta.keys())):
            logging.error(f"One or more required keys missing from package metadata")
            exit(1)
                
        #install_path = get_service_path(config, pkgmeta['name'])
        install_path = get_amp_root(pkgmeta['name'])
        if install_path is None:
            logging.error("Installation aborted")
            exit(1)

        print(f"Package Data:")
        print(f"  Name: {pkgmeta['name']}")
        print(f"  Version: {pkgmeta['version']}")
        print(f"  Build date: {pkgmeta['build_date']}")
        print(f"  Installation path: {install_path!s}")

        if not args.yes:
            if input("Continue? ").lower() not in ('y', 'yes'):
                logging.info("Installation terminated.")
                exit(0)
                
        here = Path.cwd().resolve()
        args.config = str(Path(args.config).resolve())
        # step 1: copy the files                
        run_cmd(['cp', '-a' if not args.debug else '-av', '.', str(install_path)], "Copying packaged failed", workdir=pkgroot / "data")
        
        # step 2: run the installation script (if it exists)
        if (install_path / "amp_install.py").exists():
            logging.info("Running install script")
            cmd = [install_path / 'amp_install.py', args.config]
            if args.debug:
                cmd.append('--debug')
            run_cmd(cmd, "Install script failed", workdir=install_path)
        logging.info("Installation complete")

if __name__ == "__main__":
    main()