#!/usr/bin/env python3
#
# This is a temporary tool to bootstrap the REST UI collection, until AMP-1893 is completed
#

import argparse
import amp_control
import logging
from urllib.request import Request, urlopen
from urllib.parse import quote

import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--config', default=None, help="Configuration file to use")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
    config = amp_control.load_config(args)

    url_base = f"http://{config['amp']['host']}:{config['amp']['port']}"
    amp_user = config['rest']['admin_username']
    amp_pass = config['rest']['admin_password']

    # get the token from the interface.
    req = Request(url_base + "/rest/account/authenticate", 
                  data=bytes(json.dumps({'username': amp_user, 'password': amp_pass}), encoding='utf-8'),
                  headers={'Content-Type': 'application/json'},
                  method="POST")
    with urlopen(req) as res:
        rdata = json.loads(res.read())
        amp_token = rdata['token']

    # see if the default unit is present
    default_unit = config['ui']['unit']
    req = Request(url_base + "/rest/units/search/findByName?name=" + quote(default_unit),
                  headers={'Authorization': f"Bearer {amp_token}"})
    with urlopen(req) as res:
        rdata = json.loads(res.read())
        
    if len(rdata['_embedded']['units']) == 0:
        # create the unit
        req = Request(url_base + "/rest/units",
                      headers={'Authorization': f"Bearer {amp_token}",
                               'Content-Type': 'application/json'},
                      data=bytes(json.dumps({'name': default_unit}), encoding="utf-8"),
                      method="POST")
        with urlopen(req) as res:
            print(res.status)
    else:
        print("Unit already exists")
                                 


   
if __name__ == "__main__":
    main()