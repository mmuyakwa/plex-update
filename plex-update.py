#!/bin/python
"""
Updates Plex Media Server on Debian-based systems.

This script checks for the latest Plex Media Server version via the Plex API,
compares it with the version specified in the local configuration (`info.ini`),
and if an update is available, downloads and installs it using `gdebi`.
It supports different architectures (amd64, armhf) and provides
options for dry-run and download-only modes.

Version: 1.3
Updated: 2025-05-28
License: MIT
Original Author: Michael Muyakwa (Version 1.2)
"""

# Standard library imports
import configparser
import hashlib
import json
import logging
import os # Still needed for os.geteuid()
import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Third-party imports
import requests
import urllib.request # Still used by fetch_plex_server_info

# Local application/library specific imports
# argparse is already imported under "Standard library imports"
# configparser is already imported under "Standard library imports"
# sys is already imported under "Standard library imports"
# os is already imported under "Standard library imports"
# shutil is already imported under "Standard library imports"
# subprocess is already imported under "Standard library imports"
# hashlib is already imported under "Standard library imports"
# socket is already imported under "Standard library imports"
# requests is already imported under "Third-party imports"
# logging is already imported under "Standard library imports"
# Path is already imported under "Standard library imports"

SCRIPT_DIR = Path(__file__).resolve().parent
PLEX_JSON_URL_DEFAULT = 'https://plex.tv/api/downloads/5.json' # URL to fetch Plex update information
SCRIPT_VERSION = "1.3" # Current version of this script


# Function to install the chosen Deb-File
def install_plex(deb_url: str, plex_version: str, choice: str, expected_checksum: str, download_only: bool, dry_run: bool) -> bool:
    """
    Downloads, verifies, and installs a Plex Media Server .deb package.

    Args:
        deb_url (str): The URL to download the .deb file from.
        plex_version (str): The version of Plex being installed (for naming the .deb file).
        choice (str): The architecture choice (e.g., 'amd64', 'armhf').
        expected_checksum (str): The SHA1 checksum expected for the downloaded file.
        download_only (bool): If True, downloads and verifies but does not install.
        dry_run (bool): If True, simulates the actions without downloading or installing.

    Returns:
        bool: True if the operation (download/install) was successful or if it's a dry run,
              False otherwise (though most failures will sys.exit).
    """
    if dry_run:
        logging.info("Dry run: install_plex called, but will not download or install.")
        return True # Indicate success for dry run flow

    deb_file_name = f"plexmediaserver_{plex_version}_{choice}.deb"
    deb_file_path = SCRIPT_DIR / deb_file_name
    download_successful = False
    checksum_verified = False
    logging.info(f'Downloading Plex Media Server .deb file from {deb_url} to {deb_file_path}')
    try:
        response = requests.get(deb_url, stream=True, timeout=30)
        response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
        with open(deb_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): # Read in chunks
                f.write(chunk)
        logging.info("Download complete.")
        download_successful = True

        logging.info(f"Verifying checksum for {deb_file_path}...")
        calculated_checksum = calculate_sha1(deb_file_path)
        if calculated_checksum != expected_checksum:
            logging.error(f"Checksum mismatch for downloaded file: {deb_file_path}")
            logging.error(f"Expected: {expected_checksum}, Got: {calculated_checksum}")
            sys.exit(1) # Exit, file will be removed in finally block if it exists
        logging.info(f"Checksum verified for {deb_file_path}.")
        checksum_verified = True

        if download_only:
            logging.info(f"Download of {deb_file_path} complete and checksum verified. Skipped installation due to --download-only flag.")
            # Note: File is intentionally not removed in finally block if download_only is True and successful.
            return True # Indicate successful download and verification

        # Proceed with installation
        cmd = ['gdebi', str(deb_file_path), '--n'] # Use gdebi for automatic dependency handling
        if os.geteuid() != 0: # Check if running as root
            logging.info("Plex installation requires sudo privileges.")
            sudo_confirm = input("Proceed with installation as sudo? (yes/no): ").lower()
            if sudo_confirm == 'yes':
                cmd.insert(0, 'sudo') # Prepend sudo to the command
                logging.info('Installing as SUDO.')
            else:
                logging.info("Installation aborted by user due to sudo denial.")
                if deb_file_path.exists(): # Clean up downloaded file if user aborts
                    deb_file_path.unlink()
                    logging.info(f"Removed temporary file: {deb_file_path}")
                sys.exit(0)
        
        logging.info(f'Executing installation command: {" ".join(cmd)}')
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logging.error(f"Installation failed with error code {result.returncode}: {result.stderr.strip()}")
            sys.exit(1) # File will be removed in finally block
        else:
            logging.info("Plex Media Server updated successfully.")
            logging.info(f"gdebi output: {result.stdout.strip()}")
            return True # Indicate successful installation

    except requests.exceptions.Timeout:
        logging.error(f"Timeout downloading Plex .deb file from {deb_url}")
        sys.exit(1)
    except requests.exceptions.RequestException as e: # Covers other requests issues like network problems
        logging.error(f"Error downloading Plex .deb file: {e}")
        sys.exit(1)
    except Exception as e: # Catch any other unexpected error during download/install process
        logging.error(f"An unexpected error occurred during install_plex: {e}")
        sys.exit(1)
    finally:
        # Cleanup logic:
        # Remove the .deb file if:
        # 1. It's not a 'download_only' successful operation (i.e., we intended to install or failed before that).
        # 2. OR if the download was successful but the checksum failed (always remove bad downloads).
        if deb_file_path.exists():
            # Condition 1: Not a successful download_only operation
            not_successful_download_only = not (download_only and download_successful and checksum_verified)
            # Condition 2: Downloaded but checksum failed
            checksum_failed_after_download = download_successful and not checksum_verified

            if not_successful_download_only or checksum_failed_after_download:
                try:
                    deb_file_path.unlink()
                    logging.info(f"Removed temporary file: {deb_file_path}")
                except OSError as e:
                    logging.error(f"Error removing temporary file {deb_file_path}: {e}")

    return False # Should only be reached if an unexpected path led here after failure


def load_config(config_file_path: Path) -> configparser.ConfigParser:
    """
    Loads the configuration from the specified .ini file.

    The configuration file (`info.ini`) is expected to have sections for each
    supported architecture (e.g., [amd64], [armhf]), containing:
        checksum (str): SHA1 checksum of the last downloaded .deb file.
        url (str): URL of the last downloaded .deb file.
        version (str): Version string of the last downloaded .deb file.

    Example structure:
        [amd64]
        checksum = <sha1_checksum>
        url = <url_of_deb>
        version = <version_string>

        [armhf]
        checksum = <sha1_checksum>
        url = <url_of_deb>
        version = <version_string>

    Args:
        config_file_path (Path): The path to the configuration file.

    Returns:
        configparser.ConfigParser: The loaded configuration object.

    Raises:
        SystemExit: If the configuration file is not found or cannot be read.
    """
    config = configparser.ConfigParser()
    try:
        config.read(config_file_path) # config.read() accepts Path objects
    except FileNotFoundError:
        logging.error(f"Configuration file '{config_file_path}' not found.")
        sys.exit(1)
    except IOError as e: # Catch other I/O errors like permission issues
        logging.error(f"Error reading configuration file {config_file_path}: {e}")
        sys.exit(1)
    return config


def save_config(config_file_path: Path, config_object: configparser.ConfigParser):
    """
    Saves the configuration object to the specified .ini file.

    Args:
        config_file_path (Path): The path to the configuration file.
        config_object (configparser.ConfigParser): The configuration object to save.

    Raises:
        SystemExit: If the configuration file cannot be written.
    """
    try:
        with open(config_file_path, 'w') as configfile: # open() accepts Path objects
            config_object.write(configfile)
        logging.info(f"Configuration saved to {config_file_path}")
    except IOError as e:
        logging.error(f"Error writing to configuration file {config_file_path}: {e}")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: An object containing the parsed command-line arguments.
                             Attributes include 'architecture', 'verbose', 'dry_run',
                             and 'download_only'.
    """
    parser = argparse.ArgumentParser(description="This script installs/updates Plex Media Server on Debian-based systems.")
    parser.add_argument('architecture', choices=['amd64', 'armhf'], help='Target architecture for Plex update (e.g., amd64, armhf)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging (DEBUG level).')
    parser.add_argument('--version', action='version', version=f'%(prog)s {SCRIPT_VERSION}')
    parser.add_argument('--dry-run', action='store_true', help='Check for updates and show what would happen, but do not download or install.')
    parser.add_argument('--download-only', action='store_true', help='Download the update package but do not install it. The configuration will be updated if download is successful.')
    
    args = parser.parse_args()
    logging.debug(f"Parsed command-line arguments: {args}")
    return args


def check_tool_availability(tool_name: str):
    """
    Checks if a required command-line tool is installed and in the system's PATH.

    Args:
        tool_name (str): The name of the tool to check (e.g., 'gdebi').

    Raises:
        SystemExit: If the tool is not found.
    """
    if shutil.which(tool_name) is None:
        logging.error(f"Required tool '{tool_name}' is not installed or not in PATH.")
        sys.exit(1)
    logging.info(f"Tool '{tool_name}' found.")


def calculate_sha1(filepath: Path) -> str:
    """
    Calculates the SHA1 checksum of a file.

    Args:
        filepath (Path): The path to the file.

    Returns:
        str: The hexadecimal SHA1 checksum of the file.

    Raises:
        SystemExit: If an IOError occurs during file reading, the script will exit.
    """
    sha1 = hashlib.sha1()
    try:
        with open(filepath, 'rb') as f: # open() accepts Path objects
            while True:
                data = f.read(8192)  # Read in chunks of 8KB
                if not data:
                    break
                sha1.update(data)
    except IOError as e: # Specific error type
        logging.error(f"Error reading file {filepath} for checksum calculation: {e}")
        sys.exit(1) # Exit if file can't be read
    return sha1.hexdigest()


def main():
    """
    Main function to orchestrate the Plex update process.

    Parses arguments, sets up logging, loads configuration, checks for updates,
    and performs download/installation as needed.
    No explicit arguments as it uses command-line arguments via argparse.
    No explicit return value (implicitly returns None).
    Can exit early via SystemExit if critical errors occur (e.g., tool not found, config error).
    """
    args = parse_arguments()

    # Configure logging based on verbosity argument
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s', # Added module to format
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logging.info(f"Starting Plex Update Script v{SCRIPT_VERSION}")
    logging.debug(f"Full script arguments: {args}")

    check_tool_availability('gdebi') # Ensure gdebi is available

    # Construct the absolute path to the configuration file
    config_file_path = SCRIPT_DIR / "info.ini"
    logging.debug(f"Configuration file path: {config_file_path}")
    config = load_config(config_file_path)
    
    plex_api_response = fetch_plex_server_info(PLEX_JSON_URL_DEFAULT)
    if not plex_api_response: # fetch_plex_server_info now returns None on failure
        logging.error("Exiting due to failure in fetching Plex server info.")
        sys.exit(1)

    config = check_and_perform_update(config, plex_api_response, args.architecture, args.dry_run, args.download_only)
    
    # Save configuration only if not a dry run and if any changes were made (implicitly handled by main flow)
    if not args.dry_run:
        save_config(config_file_path, config)
    else:
        logging.info("Dry run complete. No changes were made to the system or configuration file.")
        
    logging.info("Plex Update Script finished.")


def check_and_perform_update(config: configparser.ConfigParser, plex_api_response: dict, chosen_architecture: str, dry_run: bool, download_only: bool) -> configparser.ConfigParser:
    """
    Checks for Plex updates and performs actions based on flags.

    Compares the checksum of the latest available version for the chosen
    architecture with the one stored in the configuration. If different,
    it proceeds with download/installation unless in dry-run mode.

    Args:
        config (configparser.ConfigParser): The current configuration.
        plex_api_response (dict): The parsed JSON response from the Plex API.
        chosen_architecture (str): The target architecture (e.g., 'amd64').
        dry_run (bool): If True, only logs actions without performing them.
        download_only (bool): If True, downloads but does not install.

    Returns:
        configparser.ConfigParser: The (potentially updated) configuration object.
                                   Returns the original config if no release info is found
                                   or if in dry_run mode where no changes are applied.
    """
    release_info = extract_release_info(plex_api_response, chosen_architecture)

    if not release_info:
        logging.warning(f"Could not find suitable release information for architecture: {chosen_architecture}")
        return config # Return original config if no release info found

    # Ensure the architecture section exists in the config
    if not config.has_section(chosen_architecture):
        logging.warning(f"Missing section for '{chosen_architecture}' in config file. Creating it.")
        config.add_section(chosen_architecture)
        # Initialize with placeholder values, as they will be updated if a new version is found.
        config[chosen_architecture]['checksum'] = ''
        config[chosen_architecture]['url'] = ''
        config[chosen_architecture]['version'] = 'N/A'


    current_version_in_config = config.get(chosen_architecture, 'version', fallback='N/A')
    current_checksum_in_config = config.get(chosen_architecture, 'checksum', fallback='')
    
    logging.info(f'Current Plex version in config for {chosen_architecture}: "{current_version_in_config}" (Checksum: {current_checksum_in_config[:7]}...)')
    logging.info(f'Latest available Plex version for {chosen_architecture}: "{release_info["version"]}" (Checksum: {release_info["checksum"][:7]}...)')

    if current_checksum_in_config != release_info['checksum']:
        logging.info(f"New version available for {chosen_architecture}.")
        logging.info(f"  Current version: {current_version_in_config} (Checksum: {current_checksum_in_config[:7]}...)")
        logging.info(f"  New version: {release_info['version']} (Checksum: {release_info['checksum'][:7]}...)")

        if dry_run:
            logging.info(f"Dry run: Update available for {chosen_architecture} to version {release_info['version']}.")
            logging.info(f"Dry run: Would download from {release_info['url']}.")
            logging.info(f"Dry run: Would update config checksum to {release_info['checksum']} and version to {release_info['version']}.")
            return config # Return original config, no changes made in dry run

        # Update config details for the new version
        config[chosen_architecture]['checksum'] = release_info['checksum']
        config[chosen_architecture]['url'] = release_info['url']
        config[chosen_architecture]['version'] = release_info['version']
        logging.info(f"Updated configuration for {chosen_architecture} with new version details.")

        release_notes = plex_api_response.get('computer', {}).get('Linux', {}).get('items_fixed')
        if release_notes:
            logging.info(f"Release notes:\n{release_notes}")
        
        install_successful = install_plex(
            deb_url=release_info['url'],
            plex_version=release_info['version'],
            choice=chosen_architecture,
            expected_checksum=release_info['checksum'],
            download_only=download_only,
            dry_run=dry_run # This will be False here as dry_run is handled above
        )
        
        # If full installation failed (not download_only mode), we might consider reverting config.
        # However, install_plex() itself sys.exits on failure, so this part is less critical here.
        # If it were to return False, then reverting config would be important.
        if not install_successful and not download_only:
            logging.error("Installation was not successful. Configuration might be out of sync if not for sys.exit in install_plex.")
            # Potentially revert config changes here if install_plex didn't exit
            # For now, this path is unlikely due to sys.exit in install_plex on errors.
            pass
    else:
        if dry_run:
            logging.info(f"Dry run: No update needed for {chosen_architecture}. Version and checksum match.")
        else:
            logging.info(f"Plex Media Server for {chosen_architecture} is up to date.")
    return config


def fetch_plex_server_info(plex_json_url: str, timeout: int = 10) -> dict | None:
    """
    Fetches Plex Media Server download information from the Plex API.

    Args:
        plex_json_url (str): The URL to the Plex JSON API endpoint.
        timeout (int, optional): Timeout for the HTTP request in seconds. Defaults to 10.

    Returns:
        dict | None: A dictionary containing the parsed JSON response if successful,
                     None otherwise.
    """
    logging.debug(f"Fetching Plex server info from: {plex_json_url}")
    try:
        # Using urllib.request as per original code, could be swapped for requests
        with urllib.request.urlopen(plex_json_url, timeout=timeout) as response:
            # Check if the response status is OK before trying to decode
            if response.status != 200:
                logging.error(f"Error fetching Plex version information: HTTP status {response.status}")
                return None
            plex_api_response_text = response.read().decode('utf-8')
            plex_api_response = json.loads(plex_api_response_text)
    except socket.timeout:
        logging.error(f"Timeout fetching Plex version information from {plex_json_url} after {timeout} seconds.")
        return None
    except urllib.error.URLError as e: # Catches network errors like host not found
        logging.error(f"Error fetching Plex version information (URLError): {e.reason}")
        return None
    except json.JSONDecodeError as e: # Catches errors parsing the JSON
        logging.error(f"Error parsing Plex version information (JSONDecodeError): {e.msg}")
        logging.debug(f"Response text that failed to parse: {plex_api_response_text[:500]}...") # Log part of the failing response
        return None
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred in fetch_plex_server_info: {e}")
        return None

    # Basic validation of the expected JSON structure
    if not isinstance(plex_api_response, dict) or 'computer' not in plex_api_response:
        logging.error("Unexpected JSON structure from Plex API: 'computer' key missing.")
        return None
    linux_info = plex_api_response.get('computer', {}).get('Linux', {})
    if not linux_info or 'version' not in linux_info or 'releases' not in linux_info:
        logging.error("Unexpected JSON structure: 'computer.Linux.version' or 'computer.Linux.releases' missing.")
        return None
        
    logging.debug("Successfully fetched and parsed Plex server info.")
    return plex_api_response


def extract_release_info(plex_api_response: dict, architecture_choice: str) -> dict | None:
    """
    Extracts relevant release information for a specific architecture from the API response.

    It looks for a release matching the chosen architecture ('amd64' or 'armhf')
    and the 'debian' distribution.

    Args:
        plex_api_response (dict): The parsed JSON response from the Plex API.
        architecture_choice (str): The desired architecture ('amd64' or 'armhf').

    Returns:
        dict | None: A dictionary containing 'url', 'checksum', and 'version' for the
                     matching release, or None if no suitable release is found.
    """
    if not plex_api_response: # Should be handled by caller, but good practice
        logging.error("Cannot extract release info, API response is None.")
        return None

    plex_version = plex_api_response.get('computer', {}).get('Linux', {}).get('version')
    if not plex_version:
        logging.error("Could not determine Plex version from API response (missing 'computer.Linux.version').")
        return None

    releases = plex_api_response.get('computer', {}).get('Linux', {}).get('releases', [])
    if not isinstance(releases, list):
        logging.error("Invalid release data in API response (expected a list for 'computer.Linux.releases').")
        return None

    # Map user-friendly architecture choice to the build string used in Plex API
    build_arch_map = {
        'amd64': 'linux-x86_64',
        'armhf': 'linux-armv7hf' # This mapping is an assumption based on common usage
    }
    expected_build_arch = build_arch_map.get(architecture_choice)

    if not expected_build_arch:
        logging.error(f"Unsupported architecture choice: {architecture_choice}")
        return None # Should not happen due to argparse choices, but good for robustness

    for release in releases:
        if not isinstance(release, dict): # Ensure release is a dictionary
            logging.debug(f"Skipping non-dictionary item in releases list: {release}")
            continue

        build = release.get('build')
        distro = release.get('distro')
        url = release.get('url')
        checksum = release.get('checksum')

        # Check if this release matches the criteria
        if build == expected_build_arch and distro == 'debian' and url and checksum:
            logging.debug(f"Found matching release for {architecture_choice}: Build '{build}', Distro '{distro}'")
            return {
                'url': url,
                'checksum': checksum,
                'version': plex_version # The overall version for this set of releases
            }
    
    logging.warning(f"No suitable release found for architecture '{architecture_choice}' (build '{expected_build_arch}', distro 'debian') in API response.")
    return None

# Start Main
if __name__ == "__main__":
    main()