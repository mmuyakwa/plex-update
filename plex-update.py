#!/bin/python

#title:         plex-update.py
#description:   This script installs/updates Plexmediaserver on Debian-based systems.
#author:        Michael Muyakwa
#created:       2019-07-16
#updated:       2019-07-17
#version:       1.2
#license:       MIT

import urllib.request
import json
import configparser
import sys
import os

pathname = os.path.dirname(os.path.realpath(__file__))

def myhelp():
    exit("Provide a Parameter: 'amd64' or 'armhf'")


# Function to install the chosen Deb-File
def install_plex(deb_url, plex_version, choice):
    deb_file = pathname + '/plexmediaserver_' + plex_version + '_' + choice + '.deb'
    print('Downloading File.')
    urllib.request.urlretrieve(deb_url, deb_file)
    install_str = 'gdebi "%s" --n' % deb_file
    if os.geteuid() != 0:
        install_str = 'sudo %s' % install_str
        print('Installing as SUDO.')
    print('Updating Plexmediaserver now.')
    os.system(install_str)
    if os.path.exists(deb_file):
        os.remove(deb_file)


def main():    
    iniFile = os.path.abspath(pathname) + '/info.ini'
    config = configparser.ConfigParser()
    config.read(iniFile)
    try:
        choice = sys.argv[1]
    except IndexError:
        myhelp()
    if choice != 'amd64' and choice != 'armhf':
        myhelp()
    # Get the Info from the JSON-File.
    with urllib.request.urlopen(config['DEFAULT']['plexJSONurl']) as url:
        data = json.loads(url.read().decode())
        # Plex-Version
        plex_version = data['computer']['Linux']['version']

        # x64 (amd64)
        amd64_url = data['computer']['Linux']['releases'][1]['url']
        amd64_checksum = data['computer']['Linux']['releases'][1]['checksum']
        # Raspberry pi (armhf)
        armhf_url = data['computer']['Linux']['releases'][3]['url']
        armhf_checksum = data['computer']['Linux']['releases'][3]['checksum']
    print('Current Plex-Version: "%s"' % (plex_version))
    if config['amd64']['checksum'] != amd64_checksum:
        config['amd64']['checksum'] = amd64_checksum
        config['amd64']['url'] = amd64_url
        if choice == 'amd64':
            install_plex(amd64_url, plex_version, choice)
    if config['armhf']['checksum'] != armhf_checksum:
        config['armhf']['checksum'] = armhf_checksum
        config['armhf']['url'] = armhf_url
        if choice == 'armhf':
            install_plex(armhf_url, plex_version, choice)
    with open(iniFile, 'w') as configfile:
        config.write(configfile)

# Start Main
main()