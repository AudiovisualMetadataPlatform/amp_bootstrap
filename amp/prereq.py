"Utilities for checking prerequisites"

import logging
import shutil
import subprocess
import re

def check_prereqs(prereqs: dict) -> dict:
    """
    Check a prerequisites dictionary and return the commands/paths found.
    
    The dict is structured thus:
    * The key is the name of the prerequisite, such as "Container Runtime"
    * The value is a list of tests.  If any of the tests are successful, then the
      prereq is considered fulfilled.
    * The format for each test is:
      * an argv list that is used to get the version information (ie. ['atool', '--version'])
      * a regex that returns a tuple of version components (ie. r'version "(\d+)\.(\d+)') (or None for no check)
      * a comparison operator:
        * 'any':  any version will do.  Takes zero arguments.
        * 'exact': this version only.  Takes one argument.
        * 'atleast':  this version or greater.  Takes one argument a min version
        * 'between': A version between the two arguments given, inclusive
      * arguments:  these are tuples that will be compared with the tuples returned by the
        regex above and using the comparison operator
    """
    failed = False
    paths = {}
    for reqname in prereqs:
        logging.debug(f"Testing prereq {reqname}")
        for test in prereqs[reqname]:            
            cmd, regex, comp, *args = test
            cmdpath = shutil.which(cmd[0])
            if cmdpath is None:
                logging.debug(f"Cannot find {cmd[0]} in the path")
                continue
            if regex is None or comp == "any":
                # don't care about the version, just that it's there, so
                # move on.
                paths[reqname] = cmdpath
                break
            logging.debug(f"Version command: {cmd}")
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
            if p.returncode != 0:
                logging.error(f"Command {cmd} failed with return code: {p.returncode}")
                continue
            m = re.search(regex, p.stdout)
            if not m:
                logging.error(f"Command {cmd} didn't return version pattern matching: <<{regex}>>")
                continue
            version = tuple([int(x) for x in m.groups()])
            if comp == "exact":
                if version == args[0]:
                    paths[reqname] = cmdpath
                    break
                else:
                    logging.debug(f"{reqname}: {cmd} was expecting exactly {args[0]}, but got {version}")
            elif comp == "atleast":
                if version >= args[0]:
                    paths[reqname] = cmdpath
                    break
                else:
                    logging.debug(f"{reqname}: {cmd} was expecting at least {args[0]}, but got {version}")
            elif comp == "between":
                if args[0] <= version <= args[1]:
                    paths[reqname] = cmdpath
                    break
                else:
                    logging.debug(f"{reqname}: was expecting between {args[0]} and {args[1]}, but got {version}")
        else:
            logging.error(f"No suitable command for {reqname}.  Used these tests:")
            for t in prereqs[reqname]:
                logging.error(t)
            failed=True

    if failed:
        raise OSError("Cannot find system prerequisites")

    return paths


def pick_program(choices: list) -> str:
    "Find the first program that's in the path and return it"
    for choice in choices:
        if shutil.which(choice):
            return choice
    raise FileNotFoundError(f"None of these programs could be found: {choices}")