"AMP Package Functionality"

from pathlib import Path
import logging
import tarfile
from datetime import datetime
import yaml
import time
import io
import platform
import tempfile
import subprocess
import os
import shutil
import re
import fcntl

# Packages are simple tarballs with these properties:
# * Top level directory that matches the package name
# * Metadata file in <base>/amp_package.yml with this information:
#   * format: Package format version (this is version 1)
#   * name: Package name
#   * version: Package version
#   * build_date: Package build date as yyyymmdd_hhmmss 
#   * install_path: Installation directory, relative to the AMP root
#   * hooks:  hook -> script mapping for different packing actions
#   * metapackage:  true if there's no payload, just hooks and configuration
# * A data directory which contains the payload (for non-metapackages)
# * A hooks directory for any hook scripts
# * If user defaults are supplied, a "user_defaults.yaml" file will be
#   installed in data/default_config/<base>.user_defaults
# * If system defaults are supplied, a "system_defaults.yaml" file will be
#   installed in data/default_config/<base>.system_defaults
#
# Supported hooks:
#   pre => script is run prior to installation.  Args:  installation directory
#   post => script is run after files have been written to filesystem.  Args: installation directory
#   config => script is run during configuration phase
#   start => called when the package needs to be started
#   stop = called when the package needs to be stopped
# when installed config, start, and stop hook scripts are stored in data/package_hooks,
# named as <package name>__<hook_name>


REQUIRED_META = {'format', 'name', 'version', 'build_date', 'install_path', 'arch', 'metapackage'}
ALL_HOOKS = {'pre', 'post', 'config', 'start', 'stop'}

def create_package(name: str, version: str, install_path: str,
                   destination_dir: Path, payload_dir: Path, 
                   hooks: dict=None, system_defaults=None, user_defaults=None, 
                   arch_specific=False, depends_on=None) -> Path:
    """Create a new package from the content in payload_dir, returning the package Path.  
       metadata keywords will go into amp_package.yaml"""
    if not destination_dir.is_dir():
        raise NotADirectoryError(f"Destination directory needs to be a directory: {destination_dir!s}")
    if payload_dir and not payload_dir.is_dir():
        raise NotADirectoryError(f"Payload directory needs to be a directory: {payload_dir!s}")
    
    # store the core metadata
    metadata = {
        'format': 1,
        'name': name, 
        'version': version,
        'build_date': datetime.now().strftime("%Y%m%d_%H%M%S"),
        'install_path': install_path,
        'arch': platform.machine() if arch_specific else 'noarch',
        'metapackage': payload_dir is None,
    }

    # we need to make sure the name doesn't contain any weird characters
    if not re.match(r'^[\w\-]+$', metadata['name']):
        raise ValueError(f"Package name must only include A-Z, a-z, 0-9, -, and _:  {metadata['name']}")

    # Merge the hooks into to the metadata
    logging.debug("Adding hooks")
    metadata['hooks'] = {}    
    hookfiles = {}
    if hooks:
        for h in hooks:
            metadata['hooks'][h] = Path(hooks[h]).name
            hookfiles[h] = hooks[h]

    # Include the dependency information
    logging.debug("Adding dependencies")
    if not depends_on:
        metadata['dependencies'] = []    
    elif not isinstance(depends_on, (list, set)):
        metadata['dependencies'] = [depends_on]
    else:
        metadata['dependencies'] = list(depends_on)


    # now that everything looks good, create the tarball.
    logging.info(f"Creating package for {metadata['name']} with version {metadata['version']} in {destination_dir}")
    basename = metadata['name'] + "__" + metadata['version'] + "__" + metadata['arch']
    pkgfile = Path(destination_dir, basename + ".tar")
    with tarfile.TarFile(pkgfile, "w") as tfile:
        # create base directory
        base_info = tarfile.TarInfo(name=basename)
        base_info.mtime = int(time.time())
        base_info.type = tarfile.DIRTYPE
        base_info.mode = 0o755
        tfile.addfile(base_info, None)                    

        # write metadata file
        metafile = tarfile.TarInfo(name=f"{basename}/amp_package.yaml")
        metafile_data = yaml.safe_dump(metadata, default_flow_style=False).encode('utf-8')
        metafile.size = len(metafile_data)
        metafile.mtime = int(time.time())
        metafile.mode = 0o644
        tfile.addfile(metafile, io.BytesIO(metafile_data))

        # grab the payload
        logging.debug(f"Pushing data from {payload_dir!s} to data in tarball")
        if payload_dir:
            tfile.add(payload_dir, f"{basename}/data", recursive=True)

        # grab any hooks
        if hooks:
            hooks_dir = tarfile.TarInfo(name=basename + "/hooks")
            hooks_dir.mtime = int(time.time())
            hooks_dir.type = tarfile.DIRTYPE
            hooks_dir.mode = 0o755
            tfile.addfile(hooks_dir, None)                    
            # add each of the hooks
            for h in ALL_HOOKS:
                if h in hooks:
                    tfile.add(hookfiles[h], basename + "/hooks/" + Path(hooks[h]).name)

        # copy the defaults into the package
        if user_defaults:
            tfile.add(user_defaults, basename + "/user_defaults.yaml")
        if system_defaults:
            tfile.add(system_defaults, basename + "/system_defaults.yaml")

    return pkgfile


def validate_package(package_file: Path) -> dict:
    "Validate a package, returning metadata"
    basename = package_file.stem
    with tarfile.open(package_file, "r") as f:
        pkgfiles = {x.name: x for x in f.getmembers()}
        bad_prefix = [x for x in pkgfiles if x != basename and not x.startswith(basename + "/")]
        if bad_prefix:        
            raise ValueError("Some files in the package do not start with the package prefix")
        if basename + "/amp_package.yaml" not in pkgfiles:
            raise ValueError("Package doesn't contain metadata file")
        
        # read the metadata from the archive and parse it.    
        with f.extractfile(basename + "/amp_package.yaml") as mf:
            metadata = yaml.safe_load(mf)

        if metadata['format'] == 1:
            # make sure that all of the metadata fields are there.
            missing_meta = REQUIRED_META.difference(set(metadata.keys()))
            if missing_meta:
                raise ValueError(f"Metadata is missing these keys: {missing_meta}")

            if not metadata.get('metapackage', False) and basename + "/data" not in pkgfiles:
                raise ValueError("Package doesn't have a payload directory")

        else:
            raise IOError(f"Unsupported package format {metadata['format']}")

    return metadata

def install_package(package, amp_root):
    "Install a package file"
    with tempfile.TemporaryDirectory(prefix="amp_package_") as tmpdir:
        logging.debug(f"Unpacking package {package!s} into {tmpdir}")
        pkgroot = Path(tmpdir, package.stem)
        subprocess.run(['tar', '-C', tmpdir, '--no-same-owner', '-xf', str(package)])
        with open(pkgroot / "amp_package.yaml") as f:
            metadata = yaml.safe_load(f)
        if metadata['format'] == 1:
            install_path = Path(amp_root, metadata['install_path'])        
            if not install_path.exists():
                install_path.mkdir(parents=True)

            # check for a pre-install hook
            if 'pre' in metadata['hooks']:
                hook = pkgroot / "hooks" / metadata['hooks']['pre']
                if hook.exists():
                    try:
                        logging.debug(f"Running pre-install script {hook!s}")
                        subprocess.run([str(hook), str(install_path)], check=True)
                    except Exception as e:
                        raise Exception(f"Pre-install script failed: {e}")                

            # copy the files from the data directory to the install_path
            if not metadata.get('metapackage', False):
                logging.debug(f"Copying files from {pkgroot / 'data'!s} to {install_path!s}")        
                here = Path.cwd().resolve()
                os.chdir(pkgroot / "data")
                try:
                    subprocess.run(['cp', '-a', '.', str(install_path)], check=True)
                except Exception as e:
                    raise Exception(f"Copying package failed: {e}")            
                os.chdir(here)

            # if there's a user_defaults.yaml file, install it into data/default_config/<pkg name>.default
            for dtype in ('user', 'system'):                
                defaults_file = pkgroot / f"{dtype}_defaults.yaml"
                defaults_name = Path(amp_root, f"data/default_config/{metadata['name']}.{dtype}_defaults")
                if defaults_name.exists():
                    defaults_name.unlink()
                if defaults_file.exists():
                    shutil.copyfile(defaults_file, defaults_name)

            # copy the post-installation hook scripts to the data/package_hooks directory
            hook_dir = Path(amp_root, "data/package_hooks")
            
            for hook in ALL_HOOKS:
                hook_file = hook_dir / f"{metadata['name']}__{hook}"
                # uninstall any old one
                if hook_file.exists():
                    hook_file.unlink()
                # install any new one
                if hook in metadata['hooks']:
                    shutil.copyfile(pkgroot / f"hooks/{metadata['hooks'][hook]}", hook_file)
                    hook_file.chmod(0o755)

            # execute the post-install hook
            if 'post' in metadata['hooks']:
                hook = pkgroot / "hooks" / metadata['hooks']['post']
                if hook.exists():
                    try:
                        logging.debug(f"Running post-install script {hook!s}")
                        subprocess.run([str(hook), str(install_path)], check=True)
                    except Exception as e:
                        raise Exception(f"Pre-install script failed: {e}")                
            logging.info(f"Installation of {package!s} complete")

        else:
            raise IOError(f"Unsupported package format {metadata['format']}")


        

def correct_architecture(arch):
    "Return true/false if the supplied architecture is compatible with what's running"
    if arch == "noarch" or arch == platform.machine():
        return True
    return False

def newer_version(old, new):
    "Given two version strings, compare them returning True if new is >= old"
    # honestly, I don't care a ton about the text strings in the
    # versions.  The only package we have that has text in it is amp_rest which
    # uses version 0.0.1-SNAPSHOT.  
    old = tuple([int(x) if x.isdigit() else 0 for x in old.split('.')])
    new = tuple([int(x) if x.isdigit() else 0 for x in new.split('.')])
    logging.debug(f"Old version: {old}, New version: {new}, result: {new >= old}")
    return new >= old


def dependency_order(dbfile):
    "Go through the package database and return a list with the least-to-most package dependency order"
    deps = {}
    # load the dependencies
    with PackageDB(dbfile) as pdb:
        for pkg in pdb.packages():
            deps[pkg] = pdb.info(pkg)['dependencies']
    order = []
    while deps:
        did_something = False
        for pkg in list(deps.keys()):
            if set(deps[pkg]).issubset(set(order)):
                order.append(pkg)
                deps.pop(pkg)
                did_something=True
        
        if deps and not did_something:
            raise ValueError(f"Cannot resolve dependencies for: {list(deps.keys())}")

    return order




class PackageDB:
    "Manage the PackageDB file which tracks package installation information"
    def __init__(self, dbfile):
        self.dbfile = dbfile

    def __enter__(self):
        # open the file and get the lock
        try:
            self.file = open(self.dbfile, "r+")
            fcntl.lockf(self.file, fcntl.LOCK_EX)            
            self.data = yaml.safe_load(self.file)   
            if '__PACKAGE_DATABASE__' not in self.data or self.data['__PACKAGE_DATABASE__'].get('VERSION', 0) != 1:
                raise ValueError(f"Package database file {self.dbfile!s} is invalid")
        except FileNotFoundError:
            self.file = open(self.dbfile, "w+")
            fcntl.lockf(self.file, fcntl.LOCK_EX)
            self.data = {'__PACKAGE_DATABASE__': {'NOTICE': 'Do not modify this file, it is programatically maintained',
                                                  'VERSION': 1,
                                                  'INITIALIZED': datetime.now().strftime("%Y%m%d_%H%M%S")}}   
        return self   


    def __exit__(self, exc_type, exc_val, exc_tb):
        # write the current data back to the disk
        self.file.seek(0, os.SEEK_SET)
        self.file.write(yaml.safe_dump(self.data, default_flow_style=False))        
        self.file.truncate()
        fcntl.lockf(self.file, fcntl.LOCK_UN)
        self.file.close()


    def install(self, metadata):
        "Install/update a package in the database"
        name = metadata['name']
        version = metadata['version']
        build_date = metadata['build_date']
        dependencies = metadata['dependencies']

        if name not in self.data:
            self.data[name] = {
                'version': version,
                'build_date': build_date,
                'dependencies': dependencies,
                'install_date': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'history': []
            }
        else:
            # this is an upgrade, so push the current data into the history
            # and update the current.
            self.data[name]['history'].append({'version': self.data[name]['version'],
                                               'build_date': self.data[name]['build_date'],
                                               'install_date': self.data[name]['install_date']})
            self.data[name]['version'] = version
            self.data[name]['build_date'] = build_date
            self.data[name]['install_date'] = datetime.now().strftime("%Y%m%d_%H%M%S")
            if dependencies is None:
                dependencies = []
            elif not isinstance(dependencies, (list, set)):
                dependencies = [dependencies]
            else:
                dependencies = list(dependencies)
            self.data[name]['dependencies'] = dependencies

    def packages(self):
        "Get a list of the installed packages"
        return [x for x in self.data.keys() if x != '__PACKAGE_DATABASE__']

    def info(self, name):
        "Return the information for a package, or None if it isn't installed"
        if name in self.data:
            return self.data[name]
        else:
            return None
