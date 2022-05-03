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


amp_root = Path(sys.path[0]).parent
config = None

# We need to use one of the 9.x since 10.x changed the package names for the EE
# stuff and it breaks code
tomcat_download_url_base = "https://dlcdn.apache.org/tomcat/tomcat-9/"
tomcat_download_version = "9.0.60"

# TODO/Wishlist:
#  * should there be a 'download' option to download the latest packages from our site?

def main():    

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--config', default=None, help="Configuration file to use")
    subp = parser.add_subparsers(dest='action', help="Program action")
    subp.required = True
    p = subp.add_parser('init', help="Initialize the AMP installation")
    p.add_argument("--force", default=False, action="store_true", help="Force a reinitialization of the environment")
    p = subp.add_parser('start', help="Start one or more services")
    p.add_argument("service", help="AMP service to start, or 'all' for all services")
    p = subp.add_parser('stop', help="Stop one or more services")
    p.add_argument("service", help="AMP service to stop, or 'all' for all services")
    p = subp.add_parser('restart', help="Restart one or more services")
    p.add_argument("service", help="AMP service to restart, or 'all' for all services")
    p = subp.add_parser('configure', help="Configure AMP")
    p = subp.add_parser('install', help="Install a service")
    p.add_argument('--yes', default=False, action="store_true", help="Automatically answer yes to questions")
    p.add_argument("package", help="Package file to install")    
    args = parser.parse_args()
    
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    load_config(args)

    # call the appropriate action function
    globals()["action_" + args.action](config, args)


def load_config(args):
    global config
    if args.config is None:
        for n in ('amp.yaml', 'amp.yaml.default'):
            args.config = Path(sys.path[0], n)
            if args.config.exists():
                break
        else:
            logging.error("No default configuration file found.")
            exit(1)
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
        except Exception as e:
            print(f"Copying package failed: {e}")
            exit(1)
        os.chdir(here)

        # Log the installation
        with open(amp_root / "install.log", "a") as f:
            f.write(f"{datetime.now().strftime('%Y%m%d-%H%M%S')}: Package: {pkgmeta['name']} Version: {pkgmeta['version']}  Build Date: {pkgmeta['build_date']}\n")

        logging.info("Installation complete")

        if pkgmeta['name'] == 'amp_galaxy':
            # All of the packages (except for galaxy) are ready to configure as-is.  
            # force the setup_python to run here so it can be (ab)used later
            # when configuring it.
            logging.info("Installing the python venv for galaxy")            
            subprocess.run(["bash", "-c", f"cd {amp_root / 'galaxy'!s}; source scripts/common_startup_functions.sh; run_common_start_up"], check=True)
            logging.info("Python venv for galaxy has been installed")            


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
        port = config['galaxy']['port']
        if 'host' in config['galaxy']:
            if config['galaxy']['host'] is None:
                f.write(f'  http: :{port}\n')
            else:
                f.write(f'  http: {config["galaxy"]["host"]}:{port}\n')
        else:
            f.write(f"  http:  {config['amp']['url_host']}:{port}\n")

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

    # Now that there's a configuration, let's create the DB (if needed)
    # and create the user.
    subprocess.run([str(amp_root / "galaxy/create_db.sh")], check=True)
    # now that there's a database, we need to have an admin user created, with the
    # password specified.  Luckily, there's a script at 
    # https://gist.github.com/jmchilton/1979583 that was referenced in scripts/db_shell.py
    # that shows how to set up an administration user.
    with open(amp_root / "galaxy/admin-bootstrap.py", "w") as f:
        os.chmod(f.name, 0o600) # make sure nobody can read this file but us.
        f.write(f"""from scripts.db_shell import *
# check the user, and add it if it doesn't exist
admin_user = sa_session.query(User).filter(User.email=="{config['galaxy']['username']}").first()
if admin_user is None:
    print("Creating user")
    admin_user = User("{config['galaxy']['username']}")
    admin_user.username = 'ampuser'
    admin_user.active = True
    sa_session.add(admin_user)
    sa_session.flush()

# update the password to match the config
print("Resetting password")
admin_user.set_password_cleartext("{config['galaxy']['password']})

# set up the API key
admin_key = sa_session.query(APIKeys).filter(APIKeys.user_id==admin_user.id).first()
if admin_key is None:
    print("Creating a new API key")
    admin_key = APIKeys()
    admin_key.user_id = admin_user.id
    admin_key.key = "{config['galaxy']['user_id']}
    sa_session.add(admin_key)
else:
    if admin_key.key != "{config['galaxy']['user_id']})":
        print("Clearing old API Key")
        sa_session.delete(admin_key)
        sa_session.flush()
        admin_key = APIKeys()
        admin_key.user_id = admin_user.id
        admin_key.key = "{config['galaxy']['user_id']}
        sa_session.add(admin_key)
    else:
        print("Retaining API Key")
sa_session.flush()
""")
        










    # TODO:  galaxy tool config needs to come from somewhere
    # TODO:  the file which is used by the tools themselves.




def config_tomcat(config, args):
    tomcat_port = config['tomcat']['port']
    tomcat_shutdown_port = str(int(tomcat_port) + 1)

    if config['amp'].get('url_https', False):        
        proxy_data = f'proxyName="{config["amp"]["url_host"]}" proxyPort="443" secure="true" scheme="https"'
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
        vars['VUE_APP_AMP_URL'] = f"https://{config['amp']['url_host']}/rest"
    else:
        vars['VUE_APP_AMP_URL'] = f"http://{config['amp']['url_host']}:{config['tomcat']['port']}/rest"

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
                        o.write(f'JAVA_OPTS="$JAVA_OPTS -Dspring.config.location={amp_root / "data/config/application.properties"!s}"')
                    else:
                        o.write(l)
                    o.write('\n')
        
    # create the configuration file, based on config data...
    with open(amp_root / "data/config/application.properties", "w") as f:
        # simple property map
        property_map = {
            # server port
            'server.port': ('tomcat', 'port'),
            # paths
            'logging.path': ('rest', 'logging_path', 'logs', 'path_rel', 'amp', 'data_root'),
            'amppd.fileStorageroot': ('rest', 'storage_path', 'media', 'path_rel', 'amp', 'data_root'),
            'amppd.dropboxRoot': ('rest', 'dropbox_path', 'dropbox', 'path_rel', 'amp', 'data_root'),
            'amppd.mediaprobeDir': ('rest', 'mediaprobe_path', 'MediaProbe', 'path_rel', 'amp', 'data_root'),

            # spring database
            'spring.datasource.username': ('rest', 'db_user'),
            'spring.datasource.password': ('rest', 'db_pass'),
            'spring.jpa.hibernate.ddl-auto': ('rest', 'ddl_mode', 'update'),
            'spring.jpa.properties.javax.persistence.validation.mode': ('rest', 'validation_mode', 'none'),
            
            # initial user
            'amppd.username': ('rest', 'admin_username'),
            'amppd.password': ('rest', 'admin_password'), 
            'amppd.adminEmail': ('rest', 'admin_email'), 

            # email server
            "spring.mail.host": ('rest', 'email_host', 'localhost'),
            "spring.mail.port": ('rest', 'email_port', "25"),
            "spring.mail.protocol": "smtp",
            "spring.mail.properties.mail.smtp.auth": "false",
            "spring.mail.properties.mail.smtp.starttls.enable": "false",
            
            # request sizing.
            "spring.servlet.multipart.max-file-size": ('rest', 'max_request', '5GB'),
            "spring.servlet.multipart.max-request-size": ('rest', 'max_request', '5GB'),
      

            # AMP UI integration
            

            # galaxy integration
            "galaxy.host": ('galaxy', 'host', 'localhost'),
            "galaxy.port": ('galaxy', 'port', '8100'),
            "galaxy.root": ('galaxy', 'proxy_path', '/rest/galaxy'),
            "galaxy.userId": ('galaxy', "user_id"),
            "galaxy.username": ('galaxy', 'admin_username'),
            "galaxy.password": ('galaxy', 'admin_password'),
            
            
            # misc configuration
            "amppd.workflowEditMinutes": ('rest', 'workflow_edit_minutes', '60'),
            'ammpd.resetPasswordMinutes': ('rest', 'reset_password_minutes', '10'),
            'amppd.activateAccountDays': ('rest', 'activate_account_days', '7'),
            'amppd.refreshResultsTableMinutes': ('rest', 'refresh_results_table_minutes', '300'),
            'amppd.refreshResultsTableCron': ('rest', 'refresh_results_table_cron', '0 0/5 6-22 ? * *'),            
            'amppd.refreshResultsStatusCron': ('rest', 'refresh_results_status_cron', '0 0 1 ? * MON-FRI'),
            'logging.level.edu.indiana.dlib.amppd': ('rest', 'logging_level', "INFO"),
            'amppd.environment': ('rest', 'environment', 'prod'),
            'amppd.pythonPath': ('rest', 'python', 'python3'),
            'amppd.auth': ('rest', 'use_auth', 'true', 'boolean'),

            # external integration
            "avalon.url": ('rest', 'avalon_url', ''),
            "avalon.token": ('rest', 'avalon_url', ''),
            "amppd.externalSources": ('rest', 'external_sources', 'MCO,DarkAvalon,NYPL,WGBH,MusicLibrary,IUArchives,Test'),
            "amppd.taskManagers": ('rest','task_managers', 'Jira,Trello'),

            # secrets
            'amppdui.hmgmSecretKey': ('rest', 'amppdui_hmgm_secret'), 
            'amppd.encryptionSecret': ('rest', 'encryption_secret'), 
            'amppd.jwtSecret': ('rest', 'jwt_secret'), 
            'amppd.jwtExpireMinutes': ('rest', 'jwd_expiration_minutes', '240'),
        }
        
        # create the configuration
        for key, val in property_map.items():
            if isinstance(val, str):
                # this is a constant, just write it.
                f.write(f"{key} = {val}\n")
            elif isinstance(val, tuple):
                # tuples come in many flavors, but all of them start off with a section value...
                if val[0] not in config:
                    logging.error(f"Error setting {key}:  Section {val[0]} doesn't exist in the configuration")
                if len(val) == 2:
                    # section and item, fail if not present                    
                    if val[1] not in config[val[0]]:
                        logging.error(f"Error setting {key}:  Item {val[1]} isn't in the {val[0]} configuration section")
                    else:
                        f.write(f"{key} = {config[val[0]][val[1]]}\n")
                elif len(val) == 3:
                    # section, item, and default:
                    f.write(f"{key} = {config[val[0]].get(val[1], val[2])}\n")
                elif len(val) > 3:
                    # section, item, default, and special operation
                    if val[3] == 'path_rel':
                        # user value
                        v = config[val[0]].get(val[1], val[2])
                        # reference directory
                        if val[4] not in config:
                            logging.error(f"Error setting {key}: Section {val[4]} for reference directory doesn't exist")
                        else:
                            if val[5] not in config[val[4]]:
                                logging.error(f"Error setting {key}: Reference item {val[5]} is not in section {val[4]}")
                            else:
                                r = config[val[4]][val[5]]
                                if Path(v).is_absolute():
                                    f.write(f"{key} = {v}\n")
                                else:
                                    this_path = None
                                    if Path(r).is_absolute():
                                        this_path = Path(r, v)
                                    else:
                                        this_path = Path(amp_root, r, v)
                                    f.write(f"{key} = {this_path!s}\n")
                                    # create the directory if we need to
                                    this_path.mkdir(exist_ok=True)
                    elif val[3] == 'boolean':
                        v = config[val[0]].get(val[1], val[2])
                        if isinstance(v, bool):
                            v = 'true' if v else 'false'
                        f.write(f"{key} = {v}\n")

                    else:
                        logging.error(f"Error handling {key}:  special action {val[3]} not supported")
                else:
                    logging.error(f"Cannot handle a property map with {len(val)} element tuple for {key}")
            else:
                logging.error(f"Don't know how to handle a propertymap value of {val} for {key}")

        # these are things which are "hard" and can't be done through the generic mechanism.        
        # datasource configuration
        f.write(f"spring.datasource.url = jdbc:postgresql://{config['rest']['db_host']}:{config['rest'].get('db_port', 5432)}/{config['rest']['db_name']}\n")
        # amppdui.url and amppd.url -- where we can find the UI and ourselves.
        if config['amp'].get('use_https', False):
            f.write(f"amppdui.url = https://{config['amp']['url_host']}/#\n")
            f.write(f"amppd.url = https://{config['amp']['url_host']}/rest\n")
        else:
            f.write(f"amppdui.url = http://{config['amp']['url_host']}:{config['tomcat']['port']}/#\n")
            f.write(f"amppd.url = http://{config['amp']['url_host']}:{config['tomcat']['port']}/rest\n")
        #  amppdui.documentRoot -- this should be somewhere in the tomcat tree.
        f.write(f"amppdui.documentRoot = {amp_root}/tomcat/webapps/ROOT\n")
        f.write(f"amppdui.symlinkDir = {amp_root}/{config['amp']['data_root']}/symlinks\n")

        
        




def action_start(config, args):
    if args.service in ('all', 'galaxy'):
        logging.info("Starting Galaxy")

    if args.service in ('all', 'tomcat'):
        logging.info("Starting Tomcat")
        


        subprocess.run([str(amp_root / "tomcat/bin/startup.sh")], check=True)

def action_stop(config, args):
    if args.service in ('all', 'tomcat'):
        logging.info("Stopping Tomcat")
        subprocess.run([str(amp_root / "tomcat/bin/shutdown.sh")], check=True)
    if args.service in ('all', 'galaxy'):
        logging.info("Stopping Galaxy")

def action_restart(config, args):
    action_stop(config, args)
    action_start(config, args)
    

if __name__ == "__main__":
    main()