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

# Packages are simple tarballs with these properties:
# * Top level directory that matches the package name
# * Metadata file in <base>/amp_package.yml with this information:
#   * format: Package format version (this is version 1)
#   * name: Package name
#   * version: Package version
#   * build_date: Package build date as yyyymmdd_hhmmss 
#   * install_path: Installation directory, relative to the AMP root
# * A data directory which contains the payload

REQUIRED_META = set(('format', 'name', 'version', 'build_date', 'install_path', 'arch'))


def create_package(destination_dir: Path, payload_dir: Path, metadata: dict, hooks: dict=None) -> Path:
    """Create a new package from the content in payload_dir, returning the package Path.  
       metadata keywords will go into amp_package.yaml"""
    if not destination_dir.is_dir():
        raise NotADirectoryError("Destination directory needs to be a directory")
    if not payload_dir.is_dir():
        raise NotADirectoryError("Payload directory needs to be a directory")
    metadata['format'] = 1  # make sure there's a format (and it's correct)
    metadata['build_date'] = datetime.now().strftime("%Y%m%d_%H%M%S")
    if 'arch' not in metadata:
        metadata['arch'] = platform.machine()


    missing_meta = REQUIRED_META.difference(set(metadata.keys()))
    if missing_meta:
        raise ValueError(f"Metadata is missing these keys: {missing_meta}")

    # Merge the hooks into to the metadata (if we need to)
    if hooks:
        metadata['hooks'] = {}
        for h in hooks:
            metadata['hooks'][h] = hooks[h]

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
        metafile_data = yaml.safe_dump(metadata).encode('utf-8')
        metafile.size = len(metafile_data)
        metafile.mtime = int(time.time())
        metafile.mode = 0o644
        tfile.addfile(metafile, io.BytesIO(metafile_data))

        # grab the payload
        logging.debug(f"Pushing data from {payload_dir!s} to data in tarball")
        for pfile in payload_dir.glob("**/*"):            
            logging.debug(f"Adding {pfile!s} as {basename}/data/{pfile.relative_to(payload_dir)!s}")
            tfile.add(pfile, f'{basename}/data/{pfile.relative_to(payload_dir)!s}')

        # grab any hooks
        if hooks:
            hooks_dir = tarfile.TarInfo(name=basename + "/hooks")
            hooks_dir.mtime = int(time.time())
            hooks_dir.type = tarfile.DIRTYPE
            hooks_dir.mode = 0o755
            tfile.addfile(hooks_dir, None)                    

            # add each of the hooks
            for h in hooks:
                tfile.add(hooks[h], basename + "/hooks/" + Path(hooks[h]).name)

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
        if basename + "/data" not in pkgfiles:
            raise ValueError("Package doesn't have a payload directory")
        
        # read the metadata from the archive and parse it.    
        with f.extractfile(basename + "/amp_package.yaml") as mf:
            metadata = yaml.safe_load(mf)
    
        if 'format' not in metadata or int(metadata['format']) > 1:
            raise IOError(f"Unknown Package Format: {metadata.get('format', None)}")

        # make sure that all of the metadata fields are there.
        missing_meta = REQUIRED_META.difference(set(metadata.keys()))
        if missing_meta:
            raise ValueError(f"Metadata is missing these keys: {missing_meta}")


    return metadata

def correct_architecture(arch):
    "Return true/false if the supplied architecture is compatible with what's running"
    if arch == "noarch" or arch == platform.machine():
        return True
    return False


def install_package(package, amp_root):
    "Install a package file"
    with tempfile.TemporaryDirectory(prefix="amp_package_") as tmpdir:
        logging.debug(f"Unpacking package {package!s} into {tmpdir}")
        pkgroot = Path(tmpdir, package.stem)
        subprocess.run(['tar', '-C', tmpdir, '--no-same-owner', '-xf', str(package)])
        subprocess.run(['ls', '-alR', tmpdir])
        with open(pkgroot / "amp_package.yaml") as f:
            metadata = yaml.safe_load(f)

        install_path = Path(amp_root, metadata['install_path'])        
        if not install_path.exists():
            install_path.mkdir(parents=True)

        # check for a pre-install hook
        if 'hooks' in metadata and 'pre' in metadata['hooks']:
            hook = pkgroot / "hooks" / metadata['hooks']['pre']
            if hook.exists():
                try:
                    logging.debug(f"Running pre-install script {hook!s}")
                    subprocess.run([str(hook), str(install_path)], check=True)
                except Exception as e:
                    raise Exception(f"Pre-install script failed: {e}")                

        # copy the files from the data directory to the install_path
        logging.debug(f"Copying files from {pkgroot / 'data'!s} to {install_path!s}")
        here = Path.cwd().resolve()
        os.chdir(pkgroot / "data")
        try:
            subprocess.run(['cp', '-a', '.', str(install_path)], check=True)
        except Exception as e:
            raise Exception(f"Copying package failed: {e}")            
        os.chdir(here)

        # execute any post-install hooks
        if 'hooks' in metadata and 'post' in metadata['hooks']:
            hook = pkgroot / "hooks" / metadata['hooks']['post']
            if hook.exists():
                try:
                    logging.debug(f"Running post-install script {hook!s}")
                    subprocess.run([str(hook), str(install_path)], check=True)
                except Exception as e:
                    raise Exception(f"Pre-install script failed: {e}")                

