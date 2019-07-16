# Plex-Update

A **Python-Script** for updating a Plex-Mediaserver.

[![license](https://img.shields.io/github/license/mashape/apistatus.svg?style=plastic)](https://github.com/mmuyakwa/bash-scripts/blob/master/LICENSE) [![approved](https://img.shields.io/badge/approved-by%20Mein%20Nachbar-green.svg?style=plastic)](https://encrypted.google.com/search?q=steffen+held) [![powered_by](https://img.shields.io/badge/part%20of-Likando%20Publishing-red.svg?style=plastic)](https://www.likando.de)

## Example

    python plex-update.py amd64 # for Linux 64bit Systems
    or
    python plex-update.py armhf # On Raspberry pi

## Table of Contents

<!-- toc -->

* [Python dependencies](#python-dependencies)
* [Linux dependencies](#linux-dependencies)
* [Running the script](#running-the-script)
  * [manually](#manually)
  * [via cron](#via-cron)

<!-- toc stop -->

## Python dependencies

Due to the use of **urllib.request**, I got it only to run under **Pyhton 3.5** or higher.

    import urllib.request # Download File and read JSON via HTTPs
    import json # Work with JSON-information
    import configparser # to be able to parse through the INI-File
    import sys # Run System-Commands
    import os # File-oprations and determine if SUDO is needed

## Linux dependencies

This script is made for Debian-based Linux-Systems. (Debian/Ubuntu)

**GDebi** has to be installed, to install Plex with all it's dependencies automaticly.

Install via:

    sudo apt get install gdebi-core

The script installs Plexmediaserver if a new version is available.

    (sudo) gdebi plexmediaserver_file.deb --n

**"--n"** for automatic install, without prompt.

`The Script checks if your UID = 0 (root), otherwise uses SUDO. On Raspberry Pi's no password is needed.`

## Running the script

This Script always expects an **parameter** to be provided.

Parameters can be either **amd64** or **armhf**.

    amd64 = for Linux 64bit
    or
    armhf = for Raspberry Pi

### Manually

Run the script with Python 3.5 or higher.

Check your version with:

    python --version

If Version **under 3.5**, run it with

    python3.5 plex-update.py amd64

### via Cron

I let this script run **daily at 6 am** on my Raspberry Pi.

I edited Cron via **corntab -e** and added the line:

    0 0 6 1/1 * ? * python3.5 plex-update.py armhf

which ensures, that whenever there is a newer version of the Plexmediaserver, it will get updated.
