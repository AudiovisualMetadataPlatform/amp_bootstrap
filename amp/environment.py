"""
Setup the environment for subprocesses

Make sure that this library is in the PYTHONPATH, and make sure that any "expected to be there"
things are also in the path.

This should really only be used by amp_control.py and amp_devel.py since the paths
that are generated are relative to the script and those are the only ones in the
right place.

"""

import os
import sys
from pathlib import Path

def setup():
    # Export the PYTHONPATH
    here = sys.path[0]
    pythonpath = os.environ.get('PYTHONPATH', None)
    if not pythonpath:
        pythonpath = here
    else:
        pythonpath = pythonpath.split(':')
        pythonpath.append(here)
        pythonpath = ":".join(pythonpath)    
    os.environ['PYTHONPATH'] = pythonpath

    # Export the AMP_ROOT and AMP_DATA_ROOT
    os.environ['AMP_ROOT'] = str(Path(sys.path[0], "..").resolve().absolute())
    os.environ['AMP_DATA_ROOT'] = str(Path(sys.path[0], '../data').resolve().absolute())

    # Put the amp_python container into the path
    # (if it isn't installed yet, that isn't a problem)
    if 'amp_python' not in os.environ['PATH']:
        os.environ['PATH'] = str(Path(sys.path[0], "../amp_python").absolute()) + ":" + os.environ['PATH']

    # /tmp is problematic, especially when we're building things -- especially on
    # workstations (where /tmp may be a ramdisk) and on servers with small root
    # filesystems.   /var/tmp is better for the workstation situation and 
    # possibly better for servers (since the admin may have a larger /var
    # filesystem).   To cover our bases, set temporary directories to /var/tmp
    # if they aren't already set by the user.
    for t in ('TMPDIR', 'TEMP', 'APPTAINER_TMPDIR'):
        if t not in os.environ:
            os.environ[t] = "/var/tmp"

