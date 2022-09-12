#!/usr/bin/env python3
#
# Control the AMP System
#
import logging
import argparse
import yaml
from pathlib import Path
import sys
import subprocess
import urllib.request
from datetime import datetime
import urllib
import email.utils
from amp.prereq import *
from amp.package import *
from amp.config import *
import amp.environment

amp_root = Path(sys.path[0]).parent
packagedb = amp_root / "packagedb.yaml"

runtime_prereqs = {
    'python': [[['python3', '--version'], r'Python (\d+)\.(\d+)', 'between', (3, 6), (3, 9)]],
    'java': [[['java', '-version'], r'build (\d+)\.(\d+)', 'exact', (11, 0)]],
    'singularity': [[['singularity', '--version'], r'version (\d+)\.(\d+)', 'atleast', (3, 7)],
                    [['apptainer', '--version'], None, 'any']],
    # 'ffmpeg': [[['ffmpeg', '--version'], None, 'any']],  # This was for the old install of MediaProbe
    'file': [[['file', '--version'], None, 'any']],
    'gcc': [[['gcc', '--version'], None, 'any']],
    'git': [[['git', '--version'], None, 'any']]
}


def main():    
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--config', default=None, help="Configuration file to use")
    subp = parser.add_subparsers(dest='action', help="Program action")
    subp.required = True
    p = subp.add_parser('init', help="Initialize the AMP installation")
    p.add_argument("--force", default=False, action="store_true", help="Force a reinitialization of the environment")    
    
    p = subp.add_parser('download', help='Download AMP packages')
    p.add_argument('url', help="URL amp packages directory")
    p.add_argument('dest', default=str(amp_root / 'packages'), help=f"Destination directory for packages (default {amp_root / 'packages'})")
    
    p = subp.add_parser('start', help="Start one or more services")
    p.add_argument("service", help="AMP service to start, or 'all' for all services")
    
    p = subp.add_parser('stop', help="Stop one or more services")
    p.add_argument("service", help="AMP service to stop, or 'all' for all services")
    
    p = subp.add_parser('restart', help="Restart one or more services")
    p.add_argument("service", help="AMP service to restart, or 'all' for all services")
    
    p = subp.add_parser('configure', help="Configure AMP")
    p.add_argument("--dump", default=False, action="store_true", help="Dump the computed configuration instead of applying it")
    p.add_argument("--user_config", type=str, help="Generate a sample user configuration")
    
    p = subp.add_parser('install', help="Install a package")
    p.add_argument('--yes', default=False, action="store_true", help="Automatically answer yes to questions")
    p.add_argument('--nodeps', default=False, action="store_true", help="Ignore dependencies when installing")
    p.add_argument('--force', default=False, action='store_true', help="Install even if the version is older")
    p.add_argument('--info', default=False, action="store_true", help="Show package information instead of installing")
    p.add_argument('--dryrun', default=False, action="store_true", help="Don't actually install the packages")
    p.add_argument("package", nargs="+", help="Package file(s) to install")    

    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)


    # set up the environment
    amp.environment.setup()

    try:        
        if args.action in ('init', 'download', 'install', 'configure'):
            # these don't need a valid config
            config = {}
        else:
            config = load_amp_config(args.config)

        # call the appropriate action function
        check_prereqs(runtime_prereqs)
            
        globals()["action_" + args.action](config, args)
        
    except Exception as e:
        logging.exception(f"Program exception {e}")


###########################################
# Normal Actions
###########################################

def action_init(config, args):
    "Create the directories needed for AMP to do it's thing"    
    # create a bunch of directories we can populate later...
    for n in ('packages', 'data', 'data/symlinks', 'data/config', 'data/default_config',              
              'data/package_hooks', 'data/package_config'):
        d = amp_root / n
        if not d.exists():
            logging.info(f"Creating {d!s}")
            d.mkdir(parents=True)


def action_download(config, args):
    "download packages from URL directory"
    # TODO: truncates at 1G?

    dest = Path(args.dest)
    if not dest.exists() or not dest.is_dir():
        logging.error("Destination directory doesn't exist or isn't a directory")
        exit(1)

    # there should be a manifest.txt in the file which contains the filenames
    # of the packages in it, one per line.  Get that first.
    try:        
        logging.info(f"Retrieving {args.url}/manifest.txt")
        with urllib.request.urlopen(args.url + "/manifest.txt") as f:            
            for pkg in [str(x, encoding='utf8').strip() for x in f.readlines()]:                
                dstpkg = dest / pkg                
                if dstpkg.exists():
                    # check to see if the one we have is the same or newer than
                    # what's on the source.
                    dstpkg_stat = dstpkg.stat()                                                            
                    resp = urllib.request.urlopen(urllib.request.Request(f"{args.url}/{pkg}", method="HEAD"))                  
                    newpkg_time = email.utils.parsedate_to_datetime(resp.headers.get('last-modified')).timestamp()                                        
                    if newpkg_time <= dstpkg_stat.st_mtime:
                        logging.info(f"Skipping {pkg} because the local copy is newer that remote copy  ({newpkg_time} <= {dstpkg_stat.st_mtime})")
                        continue
                logging.info(f"Retrieving {args.url}/{pkg}")
                # urlretrieve will not handle cases where the content is a partial response...just
                # call out to CURL to grab the file.  It's probably faster anyway.
                subprocess.run(['curl', '-o', str(dest / pkg), f"{args.url}/{pkg}"], check=True)
                #urllib.request.urlretrieve(f"{args.url}/{pkg}", dest / pkg)
    except Exception as e:
        logging.exception(f"Something went wrong: {e}")
        exit(1)


def action_install(config, args):
    "Install packages"
    def render_metadata(filename, metadata, install_path=None):
        print(f"Package Data for {filename!s}:")
        print(f"  Name: {metadata['name']}")
        print(f"  Version: {metadata['version']}")
        print(f"  Build date: {metadata['build_date']}")
        print(f"  Architecture: {metadata['arch']}")
        print(f"  Dependencies: {metadata['dependencies']}")                
        print(f"  Installation path: {install_path if install_path else 'AMP_ROOT/' + metadata['install_path']!s}")

    with PackageDB(amp_root / "packagedb.yaml") as pdb:        
        # go through the selected packages to validate them and get metadata
        metadata = {}
        for package in [Path(x) for x in args.package]:
            try:
                pmeta = validate_package(package)
                if not correct_architecture(pmeta['arch']):
                    logging.warning(f"Skipping package {package.name}: wrong architecture -- {metadata['arch']}")
                    continue
                pmeta['package_file'] = package                                
                metadata[pmeta['name']] = pmeta
            except Exception as e:
                logging.warning(f"Skipping package {package.name} because it failed validation: {e}")


        if args.info:
            # display the package information and then exit.
            for p in metadata:
                render_metadata(metadata[p]['package_file'], metadata[p])
            return

        # This is moderately hard -- I need to install the packages so they
        # have all of their dependencies first.  I'm a lazy sort of guy, so 
        # I'm going to loop through all of the outstanding packages, installing
        # what I can and when I get to a point that either (a) there's nothing
        # left to do or (b) there are still items but I can't install anything 
        # else, I'm done.  In case (b) that would mean that I have an unfulfilled
        # dependency or a cross-dependency, neither of which I can fix.
        # BUT there's an escape hatch here: the --nodeps flag will ignore 
        # dependencies and install regardless!
        installed_packages = set(pdb.packages())
        while metadata:
            did_something = False
            for pkgname in list(metadata.keys()):                
                pkgmeta = metadata[pkgname]
                if args.nodeps or set(pkgmeta['dependencies']).issubset(installed_packages):
                    install_path = amp_root / pkgmeta['install_path']                            
                    new_version = pkgmeta['version']
                    installed_version = "0.0" if pkgname not in installed_packages else pdb.info(pkgname)['version']                    
                    if args.force or newer_version(installed_version, new_version):
                        render_metadata(pkgmeta['package_file'], pkgmeta, install_path)                        
                        if not args.yes:
                            if input("Continue? ").lower() not in ('y', 'yes'):
                                logging.info("Skipping package")
                                metadata.pop(pkgname)
                                continue
                        if not args.dryrun:
                            install_package(pkgmeta['package_file'], amp_root)
                            pdb.install(pkgmeta)
                        installed_packages.add(pkgname)
                        metadata.pop(pkgname)
                        did_something = True
                    else:
                        logging.warning(f"Skipping {pkgname} because the installed version ({installed_version}) is newer than the package version ({new_version})")
                        metadata.pop(pkgname)
                else:
                    logging.debug(f"Package {pkgname} fails needed dependencies: Needs: {set(pkgmeta['dependencies'])}, Installed: {installed_packages}")
                                    
            if not did_something and metadata:
                #installed_packages = set(pdb.packages())
                for pkg in metadata:
                    logging.warning(f"Skipping package {pkg} because dependencies could not be resolved:  wants: {set(metadata[pkg]['dependencies'])}, installed: {installed_packages}")
                break


def action_configure(config, args): 
    "Configure the amp system"
    config = load_amp_config(None, None, user_defaults_only=args.user_config) 
    if args.dump:        
        print(yaml.safe_dump(config, default_flow_style=False))
        exit(0)

    if args.user_config:
        logging.info(f"Writing default user configuration to {args.user_config}")
        with open(args.user_config, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

    # there are some cases where the configuration order is important:
    # specifically the rest stuff needs some stuff from galaxy
    # which requires that the username exists and what not.    
    for pkg in dependency_order(packagedb):
        hookfile = amp_root / f"data/package_hooks/{pkg}__config"
        if hookfile.exists():
            try:
                cmd = [str(hookfile)]
                if args.debug:
                    cmd.append("--debug")
                logging.info(f"Running config hook {hookfile.name}")
                subprocess.run(cmd, check=True)
            except Exception as e:
                logging.error(f"Failed to configure {hookfile.name}: {e}")
                exit(1)


def action_start(config, args):
    for pkg in dependency_order(packagedb):
        if args.service not in ('all', pkg):
            continue
        hookfile = amp_root / f"data/package_hooks/{pkg}__start"
        if hookfile.exists():
            try:
                cmd = [str(hookfile)]
                if args.debug:
                    cmd.append("--debug")
                logging.info(f"Running start hook {hookfile.name}")
                subprocess.run(cmd, check=True)
            except Exception as e:
                logging.error(f"Failed to start {hookfile.name}: {e}")
                exit(1)


def action_stop(config, args):
    for pkg in sorted(dependency_order(packagedb), reverse=True):
        if args.service not in ('all', pkg):
            continue
        hookfile = amp_root / f"data/package_hooks/{pkg}__stop"
        if hookfile.exists():
            try:
                cmd = [str(hookfile)]
                if args.debug:
                    cmd.append("--debug")
                logging.info(f"Running start hook {hookfile.name}")
                subprocess.run(cmd, check=True)
            except Exception as e:
                logging.error(f"Failed to start {hookfile.name}: {e}")
                exit(1)

def action_restart(config, args):
    action_stop(config, args)
    action_start(config, args)


if __name__ == "__main__":
    main()