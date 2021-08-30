# Utilities for bootstrap tools
import os
import logging
import subprocess
from pathlib import Path
import yaml
from datetime import datetime
import tempfile

def get_amp_root(service=''):
    "The installation root is the grandparent of this file"
    here = Path(__file__).resolve()    
    return here.parent.parent / service


def run_cmd(cmd, fail_message, terminate=True, workdir=None):    
    "Run an external command and optionally terminate the program"
    here = Path.cwd().resolve()
    try:        
        if workdir is not None:            
            logging.debug(f"Changing directory to {workdir}")
            os.chdir(workdir)
        logging.debug(f"Running command: {cmd}")
        subprocess.run(cmd, check=True)            
    except Exception as e:
        logging.error(f"{fail_message}: {e}")
        if terminate:
            exit(1)
    finally:
        if workdir is not None:
            logging.debug(f"Returning to {here}")
            os.chdir(here)
    


# The galaxy.yml file is not really YAML -- the uwsgi section is
# pseudo-YAML and the galaxy section is YAML.  So it has to be
# written and read specially.
def read_galaxy_config(file):
    "Read a galaxy.yml file"
    # we read it twice:
    # * one time using yaml to get the galaxy data
    # * one time using our dumb parser to get the uwsgi data    
    with open(file) as f:
        data = yaml.safe_load(f)
    data['uwsgi'] = {}
    with open(file) as f:
        in_section = False
        for line in f.readlines():            
            line = line.strip()
            if line.startswith('#') or line == '':
                continue
            logging.debug(f"in_section: {in_section}, line: {line}")
            if not in_section:
                if line == "uwsgi:":
                    in_section = True
            else:
                if line == "galaxy:":
                    in_section= False
                else:
                    key, value = line.split(':', 1)
                    if key in data:
                        if isinstance(data[key], list):
                            data['uwsgi'][key].append(value)
                        else:
                            data['uwsgi'][key] = [data[key], value]
                    else:
                        data['uwsgi'][key] = value
    return data

def write_galaxy_config(data, file):
    "write a galaxy.yml file"
    # write it in two chunks:  
    #  * the galaxy data with yaml
    #  * the uwsgi data manually
    with open(file, "w") as f:
        f.write(yaml.safe_dump({'galaxy': data['galaxy']}))
        f.write("\nuwsgi:\n")
        for k, v in data['uwsgi'].items():
            if isinstance(v, list):
                for n in v:
                    f.write(f"  {k}: {n}\n")
            else:
                f.write(f"  {k}: {v}\n")
    



def build_package(srcdir, destdir, pkgname, version=None ):
    "build a package and return its name"
    if version is None:
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
    buildtime = datetime.now().strftime("%Y%m%d_%H%M%S")

    outbase = f"{pkgname}-{version}"
    output = Path(destdir, outbase + ".tar.gz")
    with tempfile.TemporaryDirectory(prefix='amp_build-') as tmpdir:
        logging.debug(f"Temporary directory is: {tmpdir}")
        workdir = Path(tmpdir, outbase)
        logging.debug(f"Work directory is: {workdir}")
        workdir.mkdir()
        # package metadata
        logging.debug("Writing metadata")
        metadata = {
            'name': pkgname,
            'version': version,
            'build_date': buildtime,   
        }
        with open(workdir / "amp_package.yaml", "w") as f:
            yaml.safe_dump(metadata, f)

        # copy source data to data directory
        datadir = workdir / "data"
        datadir.mkdir()
        logging.info("Copying payload to temporary directory")
        run_cmd(['cp', '-a', '.', str(datadir)], "Data copy failed", workdir=srcdir)

        # build the package tarball
        logging.info("Building package")
        run_cmd(['tar', '-czf', str(output), '.'], "Tarball failed", workdir=Path(tmpdir))        
        logging.info(f"Build complete.  Package is in: {output}")
        return output


