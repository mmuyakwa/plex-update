# Plex-Update

A significantly modernized **Python script** for installing and updating Plex Media Server on Debian-based systems. This script automates the process of checking for the latest Plex versions, downloading them, verifying their integrity, and installing them, with support for different architectures and operational modes like dry-run and download-only.

[![license](https://img.shields.io/github/license/mashape/apistatus.svg?style=plastic)](https://github.com/mmuyakwa/bash-scripts/blob/master/LICENSE)

## Key Features

*   **Automated Update Check**: Fetches the latest version information from the Plex API.
*   **Architecture Support**: Handles updates for different architectures (e.g., `amd64`, `armhf`).
*   **Checksum Verification**: Verifies the SHA1 checksum of downloaded files before installation to ensure integrity.
*   **Secure Installation**: Uses `subprocess` for command execution and prompts for `sudo` confirmation if needed.
*   **Flexible Execution Modes**:
    *   `--dry-run`: See what would happen without making any changes.
    *   `--download-only`: Download and verify the package but skip installation.
*   **Configuration Management**: Stores details of the last update in an `info.ini` file to avoid reprocessing the same version.
*   **Logging**: Provides informative output with different log levels (INFO, DEBUG) and a `--verbose` option.
*   **Error Handling**: Robust error handling for network issues, file operations, and unexpected conditions.

## Usage

The script is run from the command line as follows:

```bash
python3 plex-update.py <architecture> [options]
```

### Arguments:

*   `<architecture>`: (Required) The target architecture for the Plex update.
    *   Choices: `amd64`, `armhf`

### Options:

*   `-h, --help`: Show the help message and exit.
*   `--version`: Show the script's version number and exit.
*   `--dry-run`: Check for updates and report what actions would be taken, but do not download or install anything. The configuration file will not be modified.
*   `--download-only`: Download the update package if available and verify its checksum, but do not install it. The configuration file will be updated if the download is successful.
*   `-v, --verbose`: Enable verbose logging, providing DEBUG level output.

## Table of Contents

<!-- toc -->

* [Python dependencies](#python-dependencies)
* [Linux dependencies](#linux-dependencies)
* [Running the script](#running-the-script)
  * [manually](#manually)
  * [via cron](#via-cron)

<!-- toc stop -->

## Python Dependencies

*   **Python Version**: This script requires **Python 3.7 or higher**. (Python 3.6 might work, but 3.7+ is recommended due to features like `Path.unlink(missing_ok=True)` being available, although the script currently uses explicit checks for wider compatibility).
*   **External Libraries**: The primary external dependency is the `requests` library, used for making HTTP requests.
*   **Installation**: Dependencies are listed in `requirements.txt` and can be installed using pip:
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` file contains:
    ```
    requests
    ```

## Linux Dependencies

This script is designed for Debian-based Linux systems (e.g., Debian, Ubuntu, Raspberry Pi OS).

*   **gdebi**: The `gdebi-core` package is required for installing the Plex `.deb` file and automatically handling its dependencies. You can install it using:
    ```bash
    sudo apt update
    sudo apt install gdebi-core
    ```
*   **Sudo Privileges**: The script uses `gdebi` for installation, which typically requires superuser privileges. If the script is not run as root, it will prompt you to confirm whether it should proceed by prepending `sudo` to the `gdebi` command.

## Configuration File (`info.ini`)

The script uses a configuration file named `info.ini` located in the same directory as `plex-update.py`. This file is used to store the checksum, download URL, and version of the last successfully processed Plex Media Server package for each architecture.

The script will create or update this file automatically.

**Structure:**

The `info.ini` file follows a simple INI format:

```ini
[amd64]
checksum = <sha1_checksum_of_last_downloaded_deb_for_amd64>
url = <url_of_last_downloaded_deb_for_amd64>
version = <version_string_of_last_downloaded_deb_for_amd64>

[armhf]
checksum = <sha1_checksum_of_last_downloaded_deb_for_armhf>
url = <url_of_last_downloaded_deb_for_armhf>
version = <version_string_of_last_downloaded_deb_for_armhf>
```

*   Each section (e.g., `[amd64]`) corresponds to an architecture.
*   `checksum`: The SHA1 checksum of the last downloaded/verified `.deb` file.
*   `url`: The URL from which the last `.deb` file was downloaded.
*   `version`: The version string of that Plex Media Server release.

The `[DEFAULT]` section might have existed in older versions for the Plex JSON URL, but this URL is now a constant within the script. The script primarily manages the architecture-specific sections.

## Running the Script

Ensure you have installed Python 3.7+ and the required dependencies (see "Python Dependencies" section). The script must be run from its directory or by providing the correct path to `plex-update.py`.

### Basic Execution:

To check for an update and install it for a specific architecture:

```bash
python3 plex-update.py amd64
```
or
```bash
python3 plex-update.py armhf
```

### Using Options:

*   **Dry Run (see what would happen):**
    ```bash
    python3 plex-update.py amd64 --dry-run
    ```

*   **Download Only (download but don't install):**
    ```bash
    python3 plex-update.py armhf --download-only
    ```

*   **Verbose Output (for debugging):**
    ```bash
    python3 plex-update.py amd64 -v
    ```
    or
    ```bash
    python3 plex-update.py amd64 --verbose
    ```

### Running Periodically (e.g., via Cron)

You can automate the update check by scheduling the script to run periodically using cron.

1.  Open your crontab for editing:
    ```bash
    crontab -e
    ```

2.  Add a line to schedule the script. For example, to run it daily at 3:00 AM for the `amd64` architecture:
    ```cron
    0 3 * * * /usr/bin/python3 /path/to/your/plex-update.py amd64 > /tmp/plex-update.log 2>&1
    ```
    **Important:**
    *   Replace `/usr/bin/python3` with the actual path to your Python 3 interpreter if it's different (use `which python3`).
    *   Replace `/path/to/your/plex-update.py` with the absolute path to the `plex-update.py` script.
    *   It's recommended to redirect output to a log file (`> /tmp/plex-update.log 2>&1`) to capture any messages or errors.
    *   Consider using the `--verbose` flag if you want detailed logs, or ensure your script's default logging level is appropriate for cron execution.
