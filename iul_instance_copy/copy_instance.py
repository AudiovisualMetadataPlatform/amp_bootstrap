#!/bin/env python3.9

import argparse
import logging
from pathlib import Path
import shutil
import subprocess
import yaml

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("ui_dir", help="Location of UI installation")
    parser.add_argument("rest_dir", help="Location of REST installation")
    parser.add_argument("galaxy_dir", help="Location of Galaxy installation")
    parser.add_argument("managed_dir", help="Location of the Managed instance to populate")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    try:
        
        srcyaml = Path(args.managed_dir, "amp_bootstrap/amp.yaml")
        if srcyaml.exists():
            with open(srcyaml) as f:
                amp_config = yaml.safe_load(f)
        else:        
            amp_config = {}

        logging.info("Migrating UI Service")
        migrate_ui(amp_config, Path(args.ui_dir), Path(args.managed_dir))

        logging.info("Migrating REST Service")
        migrate_rest(amp_config, Path(args.rest_dir), Path(args.managed_dir))

        logging.info("Migrating Galaxy Service")
        migrate_galaxy(amp_config, Path(args.galaxy_dir), Path(args.managed_dir))

        logging.info("Configuration file:\n" + yaml.safe_dump(amp_config))


    except Exception as e:
        logging.exception("Main thread caught exception")


def migrate_ui(amp_config: dict, ui_dir: Path, managed_dir: Path):
    "Migrate an ad hock UI instance to the managed instance, updating the config"    
    # the config.js is usually just 'null' values, so I'm not going to worry about
    # parsing it, but if we need to here's where we'd do it.

    # the only thing that's stateful here is the symlinks directory.
    logging.info("Copying symlinks")
    symdir = managed_dir / 'data/symlinks'       
    symdir.mkdir(parents=True, exist_ok=True)
    mediadir = managed_dir / 'data/media'
    mediadir.mkdir(parents=True, exist_ok=True)    
    for s in (ui_dir / 'htdocs/symlink').iterdir():
        if s.is_symlink():            
            # Create the new directory structure and link, based on the last
            # 4 parts of the link destination.            
            dest = s.readlink().parts[-4:]
            mediatree = mediadir / "/".join(dest[0:3])
            mediatree.mkdir(parents=True, exist_ok=True)
            filename = mediatree / dest[-1]
            symlink = symdir / s.name
            if not symlink.exists() and not symlink.is_symlink():
                (symdir / s.name).symlink_to(filename)
            logging.debug(f"{symdir / s.name} -> {filename} ")


def migrate_rest(amp_config: dict, rest_dir: Path, managed_dir: Path):
    "Migrate an ad hoc rest instance to the managed instance, updating the config"
    

def migrate_galaxy(amp_config: dict, galaxy_dir: Path, managed_dir: Path):
    "Migrate an ad hoc galaxy instance to the managed instance, updating the config"
    # the database directory is really the bulk of the state we want to keep.
    # but, there's stuff in there we don't want.
    logging.info("Copying the database directory")
    db_source = galaxy_dir / "galaxy/database"
    db_dest = managed_dir / "galaxy/database"
    media_dir = managed_dir / 'data/media'
    
    def copy_db_tree(entry: Path, dest_root: Path):
        # recursively copy a tree doing the right thing
        # when we hit symlinks and whatnot.
        logging.debug(f"Copy {entry} -> {dest_root}")
        for f in entry.iterdir():
            dst = dest_root / f.name
            if f.is_file():
                if f.name.endswith(".pyc"):
                    # no compiled python files
                    continue
                shutil.copyfile(f, dst)
                dst.chmod(f.stat().st_mode)                
            elif f.is_dir():                
                dst.mkdir(exist_ok=True, parents=True, mode=f.stat().st_mode)
                copy_db_tree(f, dst)
            elif f.is_symlink():
                link = f.readlink()
                logging.debug(f"Symlink {f} => {link}")
                # Something with 'media' in the path has a chance of making sense.  
                # There are broken links in the database directory on the
                # instances I've looked at. Otherwise, ignore it.
                if 'media' in link.parts:
                    p = list(link.parts)
                    while p[0] != 'media':
                        p.pop(0)
                    p.pop(0)  # get rid of media.
                    link_data = Path(media_dir, *p)
                else:
                    # link to /dev/null since there's really nowhere for it to go 
                    # but at least if someone asks for it they'll get a 0-length file
                    link_data = Path("/dev/null")
                    
                link_data.parent.mkdir(parents=True, exist_ok=True)
                link_name = dest_root / f.name
                link_name.parent.mkdir(parents=True, exist_ok=True)
                if link_name.exists() or link_name.is_symlink():
                    link_name.unlink()
                link_name.symlink_to(link_data)
                logging.debug(f"-->  {link_name} -> {link_data}")
                    
                break

    
    for e in db_source.iterdir():
        if e.name in ("dependencies", "tmp"):
            # this is runtime stuff that's populated by
            # galaxy that we don't care about
            continue
        
        logging.debug(f"Copying database entry {e.name}")
        if e.is_file():
            shutil.copyfile(e, db_dest / e.name)
        elif e.is_dir():        
            copy_db_tree(e, db_dest / e.name)
        
    # for configuration, there's really only a few bits that we care about, since
    # most of the other configuration is either install-specific stuff or boilerplate.
    logging.info("Reading config/galaxy.yml file")
    with open(galaxy_dir / "galaxy/config/galaxy.yml") as f:
        galaxy_config = yaml.safe_load(f)
    amp_config['galaxy'] = {}
    amp_config['galaxy']['admin_username'] = galaxy_config['galaxy']['admin_users']
    amp_config['galaxy']['id_secret'] = galaxy_config['galaxy']['id_secret']
    if 'admin_password' in galaxy_config['galaxy']:
        amp_config['galaxy']['admin_password'] = amp_config['galaxy']['admin_password']
    else:
        amp_config['galaxy']['admin_password'] = "use previous install's password"
    
    # get the configuration values for the MGMs.






if __name__ == "__main__":
    main()