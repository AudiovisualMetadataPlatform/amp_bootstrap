#!/bin/env python3

import amp.package
import amp.prereq
import amp.environment
import argparse
import logging
import os
from pathlib import Path
import subprocess
import sys


# AMP Root directory
amp_root = Path(sys.path[0]).parent

# development repos
dev_repos = ('amp_python', 'amp_tomcat', 'amp_mediaprobe',
             'galaxy', 'amp_mgms', "whisper",
             'amppd', 'amppd-ui', 'mgm-evaluation-scripts')

dev_repo_base = 'https://github.com/AudiovisualMetadataPlatform'


# development prereqs
devel_prereqs = {
    'javac': [[['javac', '-version'], r'javac (\d+)\.(\d+)', 'exact', (11, 0)]],
    'node': [[['node', '--version'], r'v(\d+)', 'between', (12,), (14,)]],
    'wget': [[['wget', '--version'], r'Wget (\d+)\.(\d+)', 'any']],
    'make': [[['make', '--version'], r'Make (\d+)\.(\d+)', 'any']],
    'docker': [
        [['docker', '--version'], None, 'any'],
        [['podman', '--version'], None, 'any']
    ],
    'git': [[['git', '--version'], None, 'any']]
}
     

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")    
    subp = parser.add_subparsers(dest='action', help="Actions")    
    subp.required = True
    p = subp.add_parser('init', help="Initialize the development environment")
    
    p = subp.add_parser('build', help="Build packages")
    p.add_argument("repos", nargs='*', help="Repos to build (default all)")
    p.add_argument("--dest", type=str, default=str(amp_root / 'packages'), 
                   help=f"Alternate destination dir (default: {amp_root / 'packages'!s})")
    
    p = subp.add_parser('shell', help="Start an interactive shell with the proper environment")

    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    try:
        cmdpaths = amp.prereq.check_prereqs(devel_prereqs)
    except OSError as e:
        logging.error(e)
        exit(1)

    globals()["action_" + args.action](args)



###########################################
# Development Actions
###########################################
def action_init(args):
    "Configure the evironment for development"
    
    logging.info("Creating development envrionment")
    if not (amp_root / "src_repos").exists():
        (amp_root / "src_repos").mkdir()
    here = os.getcwd()
    os.chdir(amp_root / "src_repos")
    for repo in dev_repos:
        repodir = amp_root / f"src_repos/{repo}"
        if not repodir.exists():
            logging.info(f"Cloning {repo}")
            try:
                subprocess.run(['git', 'clone', '--recursive', f"{dev_repo_base}/{repo}"], check=True)
            except Exception as e:
                logging.error(f"Failed to clone {repo}: {e}")
                exit(1)
        else:
            logging.info(f"{repo} is already cloned")
    os.chdir(here)


def action_build(args):
    "Build the repositories!"
    if not args.repos:
        args.repos = [x for x in (amp_root / "src_repos").glob("*")]
    else:
        args.repos = [amp_root / "src_repos" / x for x in args.repos]

    # set up the environment so the build utils have the libs they need.
    amp.environment.setup()

    for repo in args.repos:        
        if not repo.is_dir() or not (repo / "amp_build.py").exists():
            logging.warning(f"Skipping {repo!s} since it doesn't appear to be a valid repo")
            continue
            
        here = os.getcwd()
        os.chdir(repo)
        logging.info(f"Building packages for {repo.name}")
        p = subprocess.run(['./amp_build.py', '--package', args.dest])
        if p.returncode:
            logging.error(f"Failed building package for repo {repo}")
            exit(1)
        os.chdir(here)

    # update the manifest
    with open(args.dest + "/manifest.txt", "w") as m:
        for f in Path(args.dest).glob("*.tar"):
            m.write(f.name + "\n")


def action_shell(args):
    # setup the python env and whatnot
    amp.environment.setup()
    
    # set the PS1 string to include a note so people know
    # we're in the AMP environment.
    if 'PS1' in os.environ:
        os.environ['PS1'] = "(amp)" + os.environ['PS1']
    else:
        os.environ['PS1'] = r"(amp)[\u@\h \W]\$ "
    subprocess.run("/bin/bash")




if __name__ == "__main__":
    main()
