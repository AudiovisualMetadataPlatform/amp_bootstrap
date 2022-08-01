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
import urllib.request
import tarfile
from datetime import datetime
import zipfile
import urllib
import email.utils
import platform
import re


amp_root = Path(sys.path[0]).parent
#config = None

# We need to use one of the 9.x since 10.x changed the package names for the EE
# stuff and it breaks code
tomcat_download_url_base = "https://archive.apache.org/dist/tomcat/tomcat-9/"
tomcat_download_version = "9.0.65"

# mediaprobe repo
mediaprobe_repo = "https://github.com/IUMDPI/MediaProbe.git"

# development repos
dev_repos = {
    'amppd': 'https://github.com/AudiovisualMetadataPlatform/amppd.git',
    'amppd-ui': 'https://github.com/AudiovisualMetadataPlatform/amppd-ui.git',
    'amp_mgms': 'https://github.com/AudiovisualMetadataPlatform/amp_mgms.git',
    'galaxy': 'https://github.com/AudiovisualMetadataPlatform/galaxy.git',
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
    p = subp.add_parser('install', help="Install a package")
    p.add_argument('--yes', default=False, action="store_true", help="Automatically answer yes to questions")
    p.add_argument("package", nargs="+", help="Package file(s) to install")    

    # Development stuff    
    p = subp.add_parser('devel', help="Intialize the development environment")
    subd = p.add_subparsers(dest='devaction', help="Development actions")
    subd.required = True
    p = subd.add_parser('init', help="Initialize the development environment")
    p = subd.add_parser('build', help="Build packages")
    p.add_argument("package", nargs='*', help="Packages to build (default all)")
    p.add_argument("--dest", type=str, default=str(amp_root / 'packages'), 
                   help=f"Alternate destination dir (default: {amp_root / 'packages'!s})")


    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
    
    try:        
        if args.action in ('init', 'download', 'install', 'devel'):
            # these don't need a valid config
            config = {}
        else:
            config = load_config(args.config)


        # call the appropriate action function
        if args.action == 'devel':
            check_prereqs(True)
            globals()["devaction_" + args.devaction](config, args)
        else:
            check_prereqs()
            globals()["action_" + args.action](config, args)
        
            
    except Exception as e:
        logging.exception(f"Program exception {e}")


###########################################
# Normal Actions
###########################################

def action_init(config, args):
    "Create the directories needed for AMP to do it's thing"    

    if not (amp_root / "tomcat").exists():
        # Install a tomcat.  Specifically we're going with tomcat 9.0.60
        # which is the latest as of this release.  Tomcat 10 changes the
        # servlet namespace and is incompatible with what we're running
        logging.info(f"Installing tomcat {tomcat_download_version} as {amp_root / 'tomcat'!s}")
        tomcat_url = f"{tomcat_download_url_base}/v{tomcat_download_version}/bin/apache-tomcat-{tomcat_download_version}.tar.gz"    
        u = urllib.request.urlopen(tomcat_url)
        with tarfile.open(fileobj=u, mode="r|gz") as t:
            t.extractall(amp_root)
        (amp_root / f"apache-tomcat-{tomcat_download_version}").rename(amp_root / "tomcat")
        shutil.rmtree(amp_root / 'tomcat/webapps')
        (amp_root / 'tomcat/webapps').mkdir()
    
    # create a bunch of directories we can populate later...
    for n in ('packages', 'galaxy', 'data', 'data/symlinks', 'data/config'):
        d = amp_root / n
        if not d.exists():
            logging.info(f"Creating {d!s}")
            d.mkdir(parents=True)

    # mediaprobe needs to be checked out and setup in data/MediaProbe.
    if not (amp_root / "data/MediaProbe").exists():
        # Mediaprobe needs ffmpeg so let's make sure it's installed.
        if not shutil.which("ffmpeg"):
            logging.error("AMP requires ffmpeg to be installed.  Aborting init")
            exit(1)

        logging.info("Checking out mediaprobe repository")
        here = os.getcwd()
        os.chdir(amp_root / "data")
        subprocess.run(['git', 'clone', mediaprobe_repo], check=True)
        # we really don't need to do any setup -- the only
        # module that MediaProbe needs is pyyaml, which is
        # something that /this/ script needs, so it can
        # be run without dealing with the pipenv stuff.        
        os.chdir(here)


def action_download(config, args):
    "download packages from URL directory"

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
                urllib.request.urlretrieve(f"{args.url}/{pkg}", dest / pkg)
    except Exception as e:
        logging.exception(f"Something went wrong: {e}")
        exit(1)


def action_install(config, args):
    # extract the package and validate that it's OK
    for package in [Path(x) for x in args.package]:
        with tempfile.TemporaryDirectory(prefix="amp_bootstrap_") as tmpdir:
            logging.debug(f"Unpacking package {package!s} into {tmpdir}")
            # I think unpack archive is broken in some situations...I seem to
            # be losing the executable bits :(
            #shutil.unpack_archive(str(package), str(tmpdir))
            subprocess.run(['tar', '-C', tmpdir, '--no-same-owner', '-xvvf' if args.debug else '-xf', str(package)])
            #if args.debug:
            #    subprocess.run(f'ls -alR {tmpdir} > /dev/stderr', shell=True)

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
            required_keys = set(['name', 'version', 'build_date', 'install_path'])
            if not required_keys.issubset(set(pkgmeta.keys())):
                logging.error(f"Malformed package: One or more required keys missing from package metadata")
                logging.error(f"Needs: {required_keys}, has {set(pkgmeta.keys())}")
                exit(1)
                    
            install_path = amp_root / pkgmeta['install_path']

            print(f"Package Data:")
            print(f"  Name: {pkgmeta['name']}")
            print(f"  Version: {pkgmeta['version']}")
            print(f"  Build date: {pkgmeta['build_date']}")
            print(f"  Installation path: {install_path!s}")

            if not args.yes:
                if input("Continue? ").lower() not in ('y', 'yes'):
                    logging.info("Installation terminated.")
                    exit(0)

            if not install_path.exists():
                install_path.mkdir(parents=True)

            # copy the files from the data directory to the install_path
            here = Path.cwd().resolve()
            os.chdir(pkgroot / "data")
            try:
                subprocess.run(['cp', '-a' if not args.debug else '-av', '.', str(install_path)], check=True)
                #if args.debug:
                #    subprocess.run(f'ls -alR {str(install_path)} > /dev/stderr', shell=True)
            
            except Exception as e:
                print(f"Copying package failed: {e}")
                exit(1)
            os.chdir(here)

            # Log the installation
            with open(amp_root / "install.log", "a") as f:
                f.write(f"{datetime.now().strftime('%Y%m%d-%H%M%S')}: Package: {pkgmeta['name']} Version: {pkgmeta['version']}  Build Date: {pkgmeta['build_date']}\n")

            logging.info("Installation complete")

            # manually deploy the servlet if it is the UI or REST
            servlets = {
                'amp_ui': 'ROOT.war',
                'amp_rest': 'rest.war'
            }
            if pkgmeta['name'] in servlets:
                logging.info("Deploying war file")
                warfile = amp_root / f'tomcat/webapps/{servlets[pkgmeta["name"]]}'
                deployroot = amp_root / f'tomcat/webapps/{Path(servlets[pkgmeta["name"]]).stem}'
                with zipfile.ZipFile(warfile, 'r') as zfile:
                    zfile.extractall(deployroot)
                warfile.unlink()


def action_configure(config, args): 
    "Configure the amp system"
    logging.info("Configuring Galaxy")
    config_galaxy(config, args)
    logging.info("Configuring Tomcat")
    config_tomcat(config, args)
    logging.info("Configuring UI")
    config_ui(config, args)
    logging.info("Configuring Backend")
    config_rest(config, args)
    logging.info("Configuration complete")


def config_galaxy(config, args):
    # config/galaxy.yml isn't a real YAML file, so writing this is actually a manual dump
    # for the uwsgi section, and a real yaml dump for the galaxy section.
    with open(amp_root / "galaxy/config/galaxy.yml", "w") as f:
        f.write("## Automatically generated file, do no edit\n")
        f.write("uwsgi:\n")
        # the host/port for galaxy
        port = config['amp']['port'] + 2
        config['amp']['galaxy_port'] = port  # we'll need this value later.
        host = config['galaxy'].get('host', '')
        f.write(f"  http: {host}:{port}\n")
        
        # the application mount settings        
        f.write(f"  mount: {config['galaxy']['root']}=galaxy.webapps.galaxy.buildapp:uwsgi_app()\n")
        f.write(f"  manage-script-name: true\n")

        # do the uwsgi things
        for k,v in config['galaxy']['uwsgi'].items():
            if isinstance(v, bool):
                f.write(f"  {k}: {'true' if v else 'false'}\n")                
            elif isinstance(v, list):
                for x in v:
                    f.write(f"  {k}: {x}\n")
            else:
                f.write(f"  {k}: {v}\n")

        # Now for the actual galaxy config stuff.  It is really
        # yaml, so we can just build the data structure in memory
        # and append it to the file.
        galaxy = config['galaxy']['galaxy']

        # the admin user
        galaxy['admin_users']  = config['galaxy']['admin_username']
        
        # id_secret -- fail if it hasn't been changed
        if config['galaxy']['id_secret'] == 'CHANGE ME':
            logging.error("The galaxy id_secret needs to be changed for successful installation")
            exit(1)
        else:
            galaxy['id_secret'] = config['galaxy']['id_secret']

        f.write(yaml.safe_dump({'galaxy': galaxy}))
        f.write("\n")

    # set up the galaxy python
    logging.info("Installing galaxy python and node")
    os.environ['GALAXY_ROOT'] = str(amp_root / "galaxy")
    here = os.getcwd()
    os.chdir(amp_root / "galaxy")
    try:
        subprocess.run(['scripts/common_startup.sh'], check=True)
    except Exception as e:
        logging.error(f"Could not set up galaxy python: {e}")
        exit(1)
    galaxy_python = str(amp_root / "galaxy/.venv/bin/python")

    # Now that there's a configuration (and python), let's create the DB (if needed)
    # and create the user.  
    logging.info("Creating galaxy database")
    subprocess.run([str(amp_root / "galaxy/create_db.sh")], check=True)
    # now that there's a database, we need to have an admin user created, with the
    # password specified.  Luckily, there's a script at 
    # https://gist.github.com/jmchilton/1979583 that was referenced in scripts/db_shell.py
    # that shows how to set up an administration user.  galaxy_configure.py is based 
    # heavily on those things.
    try:
        p = subprocess.run([galaxy_python, sys.path[0] + "/galaxy_configure.py", 
                            config['galaxy']['admin_username'], config['galaxy']['admin_password'], config['galaxy']['id_secret']],
                        check=True, stdout=subprocess.PIPE, encoding='utf-8')
        if not p.stdout.startswith('user_id='):
            raise ValueError("Galaxy configuration didn't return a user_id")
        (_, config['galaxy']['user_id']) = p.stdout.splitlines()[0].split('=', 1)
        print(config['galaxy']['user_id'])
    except Exception as e:
        logging.error(f"Galaxy database config failed: {e}")
        exit(1)

    logging.info("Creating the galaxy toolbox configuration")
    with open(amp_root / "galaxy/config/tool_conf.xml", "w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<toolbox monitor="true">\n')
        counter = 0
        for s in config['galaxy']['toolbox']:
            f.write(f'  <section id="sect_{counter}" name="{s}">\n')
            for t in config['galaxy']['toolbox'][s]:
                f.write(f'    <tool file="{t}"/>\n')
            f.write("  </section>\n")
            counter += 1
        f.write("</toolbox>\n")

    logging.info("Creating the MGM configuration file")
    with open(amp_root / "galaxy/tools/amp_mgms/amp_mgm.ini", "w") as f:
        for s in config['mgms']:
            f.write(f'[{s}]\n')
            for k,v in config['mgms'][s].items():
                f.write(f'{k} = {v}\n')



def config_tomcat(config, args):
    tomcat_port = config['amp']['port']
    tomcat_shutdown_port = str(int(tomcat_port) + 1)

    if config['amp'].get('https', False):        
        proxy_data = f'proxyName="{config["amp"]["host"]}" proxyPort="443" secure="true" scheme="https"'
    else:
        proxy_data = ""

    # Main tomcat configuration file
    with open(amp_root / "tomcat/conf/server.xml", "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<Server port="{tomcat_shutdown_port}" shutdown="SHUTDOWN">
  <Listener className="org.apache.catalina.startup.VersionLoggerListener" />
  <Listener className="org.apache.catalina.core.AprLifecycleListener" SSLEngine="on" />
  <Listener className="org.apache.catalina.core.JreMemoryLeakPreventionListener" />
  <Listener className="org.apache.catalina.mbeans.GlobalResourcesLifecycleListener" />
  <Listener className="org.apache.catalina.core.ThreadLocalLeakPreventionListener" />
  <GlobalNamingResources>
    <Resource name="UserDatabase" auth="Container"
              type="org.apache.catalina.UserDatabase"
              description="User database that can be updated and saved"
              factory="org.apache.catalina.users.MemoryUserDatabaseFactory"
              pathname="conf/tomcat-users.xml" />
  </GlobalNamingResources>
  <Service name="Catalina">
    <Connector port="{tomcat_port}" protocol="HTTP/1.1"
               connectionTimeout="20000"
               redirectPort="8443" {proxy_data}/>
    <Engine name="Catalina" defaultHost="localhost">
      <Realm className="org.apache.catalina.realm.LockOutRealm">
        <Realm className="org.apache.catalina.realm.UserDatabaseRealm"
               resourceName="UserDatabase"/>
      </Realm>
      <Host name="localhost"  appBase="webapps"
            unpackWARs="true" autoDeploy="true">
        <Valve className="org.apache.catalina.valves.AccessLogValve" directory="logs"
               prefix="localhost_access_log" suffix=".txt"
               pattern="%h %l %u %t &quot;%r&quot; %s %b" />
      </Host>
    </Engine>
  </Service>
</Server>\n""")

    # allow ROOT webapp to access symlinks
    (amp_root / "tomcat/conf/Catalina/localhost").mkdir(parents=True, exist_ok=True)
    with open(amp_root / "tomcat/conf/Catalina/localhost/ROOT.xml", "w") as f:
        f.write(f"""<Context>
   <Resources allowLinking="true">
    <PreResources className="org.apache.catalina.webresources.DirResourceSet" webAppMount="/symlinks" base="{amp_root / 'data/symlinks'!s}"/>
  </Resources>
</Context>\n""")


def config_ui(config, args):    
    # the UI bits are configured with these variables in javascript...    
    vars = {'VUE_APP_DISABLE_AUTH': config['ui'].get('disable_auth', 'false'),
            'VUE_APP_AMP_UNIT': config['ui']['unit'],
            'VUE_APP_USER_GUIDE': config['ui']['user_guide_url']}
            

    if config['amp'].get('use_https', False):
        vars['VUE_APP_AMP_URL'] = f"https://{config['amp']['host']}/rest"
        vars['VUE_APP_GALAXY_WORKFLOW_URL'] = f"https://{config['amp']['host']}/rest/galaxy/workflow/editor?id="
    else:
        vars['VUE_APP_AMP_URL'] = f"http://{config['amp']['host']}:{config['amp']['port']}/rest"
        vars['VUE_APP_GALAXY_WORKFLOW_URL'] = f"http://{config['amp']['host']}:{config['amp']['port']}/rest/galaxy/workflow/editor?id="




    # config.js holds the values we need
    with open(amp_root / "tomcat/webapps/ROOT/config.js", "w") as f:
        f.write("// automatically generated, do not edit\n")
        f.write("window.config = {\n")
        for v in vars:
            f.write(f'    "{v}": "{vars[v]}",\n')
        f.write('    "AUTO": 1\n')
        f.write("}\n")


def config_rest(config, args):
    """Create the configuration file for the AMP REST service"""
    # make sure the configuration file is specified in the tomcat startup env stuff:
    # JAVA_OPTS:  -Dspring.config.location=/path/to/config.properties
    if not (amp_root / "tomcat/bin/setenv.sh").exists():
        with open(amp_root / "tomcat/bin/setenv.sh", "w") as o:
            o.write(f'JAVA_OPTS="$JAVA_OPTS -Dspring.config.location={amp_root / "data/config/application.properties"!s}"\n')
    else:
        (amp_root / "tomcat/bin/setenv.sh").rename(amp_root / "tomcat/bin/setenv.sh.bak")        
        with open(amp_root / "tomcat/bin/setenv.sh.bak") as i:
            with open(amp_root / "tomcat/bin/setenv.sh", "w") as o:
                for l in i.readlines():
                    if 'spring.config.location' in l:
                        pass
                    else:
                        o.write(l)
                    o.write('\n')
                o.write(f'JAVA_OPTS="$JAVA_OPTS -Dspring.config.location={amp_root / "data/config/application.properties"!s}"')

    # create the configuration file, based on config data...
    with open(amp_root / "data/config/application.properties", "w") as f:
        # simple property map
        property_map = {
            # server port and root            
            'server.port': (['amp', 'port'], None),
            # database creds (host/db/port is handled elsewhere)
            'spring.datasource.username': (['rest', 'db_user'], None),
            'spring.datasource.password': (['rest', 'db_pass'], None),
            # initial user
            'amppd.username': (['rest', 'admin_username'], None),
            'amppd.password': (['rest', 'admin_password'], None), 
            'amppd.adminEmail': (['rest', 'admin_email'], None), 
            # galaxy integration
            "galaxy.host": (['galaxy', 'host'], 'localhost'),            
            "galaxy.root": (['galaxy', 'root'], None),            
            "galaxy.username": (['galaxy', 'admin_username'], None),
            "galaxy.password": (['galaxy', 'admin_password'], None),
            "galaxy.port": (['amp', 'galaxy_port'], None),  # set during galaxy config generation
            "galaxy.userId": (['galaxy', "user_id"], None), # set during galaxy config generation
            # AMPUI properties           
            'amppdui.hmgmSecretKey': (['mgms', 'hmgm', 'auth_key'], None),
            # Directories
            'amppd.fileStorageRoot': (['rest', 'storage_path'], 'media', 'path_rel', ['amp', 'data_root']),
            'amppd.dropboxRoot': (['rest', 'dropbox_path'], 'dropbox', 'path_rel', ['amp', 'data_root']),
            'logging.path': (['rest', 'logging_path'], 'logs', 'path_rel', ['amp', 'data_root']),
            'amppd.mediaprobeDir': (['rest', 'mediaprobe_dir'], 'MediaProbe', 'path_rel', ['amp', 'data_root']),
            # Avalon integration
            "avalon.url": (['rest', 'avalon_url'], 'https://avalon.example.edu'),
            "avalon.token": (['rest', 'avalon_token'], 'dummytoken'),
            # secrets             
            'amppd.encryptionSecret': (['rest', 'encryption_secret'], None), 
            'amppd.jwtSecret': (['rest', 'jwt_secret'], None),
        }
   
        def resolve_list(data, path, default=None):
            # given a data structure and a path, walk it and return the value
            if len(path) == 1:
                logging.debug(f"Base case: {data}, {path}, {default}")
                return data.get(path[0], default)
            else:
                v = data.get(path[0], None)
                logging.debug(f"Lookup: {data}, {path}, {default} = {v}")
                if v is None or not isinstance(v, dict):
                    logging.debug("Returning the default")
                    return default
                else:
                    logging.debug(f"Recurse: {v}, {path[1:]}, {default}")
                    return resolve_list(v, path[1:], default)

        # create the configuration
        for key, val in property_map.items():
            if isinstance(val, str):
                # this is a constant, just write it.
                f.write(f"{key} = {val}\n")
            elif isinstance(val, tuple):
                # every section starts with a reference list
                logging.debug(f"Looking up {key} {val}")
                v = resolve_list(config, val[0], val[1])
                if v is None:
                    logging.error(f"Error setting {key}:  Section {val[0]} doesn't exist in the configuration")
                    continue
                if len(val) < 3:
                    # write it.
                    if isinstance(v, bool):
                        f.write(f"{key} = {'true' if v else 'false'}\n")
                    else:
                        f.write(f"{key} = {v}\n")
                else:
                    # there's a function to be called.
                    if val[2] == 'path_rel':
                        if Path(v).is_absolute():
                            f.write(f"{key} = {v}\n")
                        else:
                            r = resolve_list(config, val[3], None)
                            if r is None:
                                logging.error(f"Error setting {key}:  Section {val[3]} doesn't exist in the configuration")
                                continue                        
                            this_path = None
                            if Path(r).is_absolute():
                                this_path = Path(r, v)
                            else:
                                this_path = Path(amp_root, r, v)
                            f.write(f"{key} = {this_path!s}\n")
                            # create the directory if we need to (need the check because it may be symlink)
                            if not this_path.exists():
                                this_path.mkdir(exist_ok=True)
                    else:
                        logging.error(f"Error handling {key}:  special action {val[2]} not supported")


        # these are things which are "hard" and can't be done through the generic mechanism.        
        # datasource configuration
        f.write(f"spring.datasource.url = jdbc:postgresql://{config['rest']['db_host']}:{config['rest'].get('db_port', 5432)}/{config['rest']['db_name']}\n")
        # amppdui.url and amppd.url -- where we can find the UI and ourselves.
        if config['amp'].get('use_https', False):
            f.write(f"amppdui.url = https://{config['amp']['host']}/#\n")
            f.write(f"amppd.url = https://{config['amp']['host']}/rest\n")
        else:
            f.write(f"amppdui.url = http://{config['amp']['host']}:{config['amp']['port']}/#\n")
            f.write(f"amppd.url = http://{config['amp']['host']}:{config['amp']['port']}/rest\n")
        #  amppdui.documentRoot -- this should be somewhere in the tomcat tree.
        f.write(f"amppdui.documentRoot = {amp_root}/tomcat/webapps/ROOT\n")
        f.write(f"amppdui.symlinkDir = {amp_root}/{config['amp']['data_root']}/symlinks\n")
                        
        f.write("# boilerplate properties\n")
        for k,v in config['rest']['properties'].items():
            if isinstance(v, bool):
                f.write(f"{k} = {'true' if v else 'false'}\n")
            else:
                f.write(f"{k} = {v}\n")
        

def action_start(config, args):
    if args.service in ('all', 'galaxy'):
        logging.info("Starting Galaxy")
        subprocess.run([str(amp_root / "galaxy/run.sh"), "start"])

    if args.service in ('all', 'tomcat'):
        logging.info("Starting Tomcat")
        subprocess.run([str(amp_root / "tomcat/bin/startup.sh")], check=True)


def action_stop(config, args):
    if args.service in ('all', 'tomcat'):
        logging.info("Stopping Tomcat")
        subprocess.run([str(amp_root / "tomcat/bin/shutdown.sh")], check=True)
    if args.service in ('all', 'galaxy'):
        logging.info("Stopping Galaxy")
        subprocess.run([str(amp_root / "galaxy/run.sh"), "stop"])


def action_restart(config, args):
    action_stop(config, args)
    action_start(config, args)

###########################################
# Development Actions
###########################################
def devaction_init(config, args):
    "Configure the evironment for development"
    # make sure the basic configuration is installed
    action_init(config, args)
    
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
                subprocess.run(['git', 'clone', '--recursive', dev_repos[repo]], check=True)
            except Exception as e:
                logging.error(f"Failed to clone {repo}: {e}")
                exit(1)
        else:
            logging.info(f"{repo} is already cloned")
    os.chdir(here)


def devaction_build(config, args):
    "Build the packages!"
    if not args.package:
        args.package = list(dev_repos.keys())

    for pkg in args.package:
        if pkg not in dev_repos:
            logging.warning(f"Skipping {pkg} since it doesn't appear to be a valid repo")
            continue
        here = os.getcwd()
        os.chdir(amp_root / f"src_repos/{pkg}")
        logging.info(f"Building packages for {pkg}")
        p = subprocess.run(['./amp_build.py', '--package', args.dest])
        if p.returncode:
            logging.error(f"Failed building package for repo {pkg}")
            exit(1)
        os.chdir(here)

    # create the manifest
    with open(args.dest + "/manifest.txt", "w") as m:
        for f in Path(args.dest).glob("*.tar"):
            m.write(f.name + "\n")


###########################################
# Utilities
###########################################
def load_config(config_file=None):
    "Load the configuration file"
    # load the default config
    try:
        with open(sys.path[0] + "/amp.default") as f:
            default_config = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Cannot load default config file: {sys.path[0]}/amp.default: {e}")
        exit(1)

    # find the overlay config...
    if config_file is None:
        for d in [Path(x) for x in (sys.path[0], '.', Path.home())]:
            cfg_file = d / 'amp.yaml'
            if cfg_file.exists():
                logging.info(f"Using config file {cfg_file!s}")
                config_file = cfg_file.resolve()
                break
        else:
            logging.error(f"Unable to locate a user configuration file")
            exit(1)
    config_file = Path(config_file).resolve()
    if not config_file.exists():
        logging.error(f"Config file {config_file!s} doesn't exist")
        exit(1)

    try:
        with open(config_file) as f:
            overlay_config = yaml.safe_load(f)
        if overlay_config is None or type(overlay_config) is not dict:
            raise ValueError("YAML file is valid but is either empty or is not a dictionary")
    except Exception as e:
        logging.error(f"Cannot load config file {config_file!s}: {e}")
        exit(1)

    _merge(default_config, overlay_config)
    return default_config


def _merge(model, overlay, context=None):
    "Merge two dicts"
    if not context:
        context = []
        
    def context_string():
        return '.'.join(context)

    logging.debug(f"Merge context: {context_string()}")
    for k in overlay:
        if k not in model:
            logging.warning(f"Adding un-modeled value: {context_string()}.{k} = {overlay[k]}")
            model[k] = overlay[k]
        elif type(overlay[k]) is not type(model[k]):            
            if type(overlay[k]) is type(None):
                logging.debug(f"Removing {context_string()}.{k}")
                model.pop(k)
            else:
                logging.warning(f"Skipping - type mismatch: {context_string()}.{k}:  model={type(model[k])}, overlay={type(overlay[k])}")
        elif type(overlay[k]) is dict:   
            nc = list(context)
            nc.append(k)         
            _merge(model[k], overlay[k], nc)
        else:
            # everything else is replaced wholesale
            logging.debug(f"Replacing value: {context_string()}.{k}:  {model[k]} -> {overlay[k]}")
            model[k] = overlay[k]


def check_prereqs(dev=False):
    "Check the system prerequisites"
    logging.info(f"Checking {'development' if dev else 'system'} prerequisites")
    failed = False
    # check our python version.  The version of galaxy we're running requires
    # a python that's >= 3.6 and <= 3.9.  3.10 definitely breaks things.
    # since we're running the in-path python, we can use our instance to 
    # determine which python is installed.
    if not (6 <= int(platform.python_version_tuple()[1]) <= 9):
        logging.error(f"AMP requires python 3.6 - 3.9.  You're running {platform.python_version()}")
        failed = True

    # amppd requires JRE 11, although it might run on newer versions.  Let's 
    # not take a chance and force it here.    
    v = get_version('java', ['-version'], r'version "(\d+)\.(\d+)') 
    if not v:
        failed = True
    else:    
        if v != (11, 0):
            logging.error(f"Found JRE version {v}, need (11, 0)")
            failed = True

    # Singularity 3.7 or greater (or apptainer 1.0 or newer)
    v = get_version('apptainer', ['--version'], r'version (\d+)\.(\d+)')
    if not v:
        # ok, apptainer isn't installed, so look for singularity
        v = get_version('singularity', ['--version'], r'version (\d+)\.(\d+)')
        if not v:
            logging.error("Neither apptainer nor singularity is available")
            failed = True
        else:
            if v <= (3, 7):
                logging.error(f"Found singularity version {v}, need 3.7 or greater")
                failed = True
    else:
        # if we have apptainer, we're good, but let's make sure the singularity
        # symlink is there.
        if not shutil.which('singularity'):
            failed = True
            logging.error("Apptainer is installed, but the singularity symlink isn't available")
        
    # just make sure ffmpeg is here
    v = get_version('ffmpeg')
    if not v:
        failed = True

    # and the same with file
    v = get_version('file')
    if not v:
        failed = True

    # galaxy sometimes really, really wants gcc.  So let's make sure there's one there
    v = get_version('gcc')
    if not v:
        failed = True


    # Development tools
    if dev:
        # JDK
        v = get_version('javac', ['--version'], r'javac (\d+)\.(\d+)')
        if not v:
            failed = True
        else:    
            if v != (11, 0):
                logging.error(f"Found JDK version {v}, need (11, 0)")
                failed = True       
        
        # Node.js 12 - 14
        v = get_version('node', ['--version'], r'v(\d+)')
        if not v:
            failed = True
        else:
            if not ((12, ) <= v <= (14, )):
                logging.error(f"Found node.js version {v}, need 12 or 14")
                failed = True

        # just make sure make is there somewhere
        v = get_version('make')
        if not v:
            failed = True

        # and lastly, check for docker and/or podman
        dv = get_version('docker')
        pv = get_version('podman')
        if not (pv or dv):
            logging.warning("Neither podman nor docker found.  You will not be able to build a containerized version")
        else:
            logging.info(f"Use {'podman' if pv else 'docker'} to build a container.")


    if failed:
        logging.error("Prerequistes have failed.  Install them and try again")
        exit(1)


def get_version(cmd, args=None, pattern=None):
    logging.debug(f"Checking path for {cmd}")
    if not shutil.which(cmd):
        logging.error(f"Command {cmd} not in path")
        return None
    # if a pattern is not supplied, just make sure the binary is there
    # and return a generic version number
    if not pattern:
        return (1, 0)

    command = [cmd]
    if args:
        command.extend(args)
    logging.debug(f"Version command: {command}")
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    if p.returncode != 0:
        logging.error(f"Command {command} failed with return code: {p.returncode}")
        return None
    m = re.search(pattern, p.stdout)
    if not m:
        logging.error(f"Command {command} didn't return version pattern matching: <<{pattern}>>")
        return None
    return tuple([int(x) for x in m.groups()])
    



if __name__ == "__main__":
    main()