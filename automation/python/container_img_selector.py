#!/usr/bin/env python3
import os
import re
import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Suppress only the InsecureRequestWarning from urllib3
urllib3.disable_warnings(InsecureRequestWarning)

BASE_URL = "https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/v1.0/hpcsuite_registry/container_img_reg/alma8.9"
TOOLS = ["chakshu-front_reg", "ganglia_reg", "ldap_reg", "nagios_reg", "osticket_reg", "xCAT_reg"]
LOCAL_DIR = "../../hpcsuite_registry/container_img_reg"

# Extensions that might represent container image files
VALID_EXTENSIONS = (".tar", ".img", ".gz", ".xz", ".bz2", ".tgz")


def create_directory_structure():
    """Create base directories for tool registries."""
    os.makedirs(LOCAL_DIR, exist_ok=True)
    for tool in TOOLS:
        tool_path = os.path.join(LOCAL_DIR, tool)
        os.makedirs(tool_path, exist_ok=True)
    print(f"✅ Directory structure created under: {LOCAL_DIR}\n")


def list_available_versions(tool_name):
    """
    Dynamically fetch available versions by parsing the HTML directory listing.
    """
    tool_url = f"{BASE_URL}/{tool_name}/"
    try:
        response = requests.get(tool_url, timeout=10, verify=False)
        if response.status_code != 200:
            return []

        # Extract subdirectory names (ending with '/')
        matches = re.findall(r'href="([^"/]+)/"', response.text)
        # Filter for version-like directories
        versions = [m.strip('/') for m in matches if re.match(r'^[vV]?\d+(\.\d+)*$', m) or m.lower() == "latest"]

        return versions
    except requests.exceptions.RequestException:
        return []


def find_image_file(tool_name, version):
    """
    Detect the image file name dynamically from the version directory.
    """
    version_url = f"{BASE_URL}/{tool_name}/{version}/"
    try:
        response = requests.get(version_url, timeout=10, verify=False)
        if response.status_code != 200:
            return None

        # Find all linked file names from HTML
        matches = re.findall(r'href="([^"]+)"', response.text)

        # Filter out only valid image files
        for file in matches:
            if file.endswith(VALID_EXTENSIONS) or "cdac_" in file:
                return file  # Return the first valid image file found

        return None
    except requests.exceptions.RequestException:
        return None


def select_tool_version(tool_name):
    """Ask user to select a version from available options, skip if unavailable."""
    versions = list_available_versions(tool_name)

    if not versions:
        print(f"⚠️  No version list found for {tool_name}. Skipping...\n")
        return None

    print(f"\n📦 Available versions for {tool_name}:")
    for idx, v in enumerate(versions, 1):
        print(f"  {idx}. {v}")

    choice = input(f"Select version number for {tool_name} (or press Enter to skip): ").strip()

    if not choice:
        print(f"⏭️  Skipping {tool_name}...\n")
        return None

    try:
        version = versions[int(choice) - 1]
        return version
    except (ValueError, IndexError):
        print(f"❌ Invalid choice for {tool_name}, skipping...\n")
        return None


def pull_selected_versions():
    """Download selected container images if available."""
    for tool in TOOLS:
        print(f"\n🔍 Checking registry for {tool}...")
        version = select_tool_version(tool)
        if not version:
            continue

        # Find the correct image file name in this version folder
        image_file = find_image_file(tool, version)
        if not image_file:
            print(f"⚠️  No image file found for {tool}:{version}. Skipping...\n")
            continue

        image_url = f"{BASE_URL}/{tool}/{version}/{image_file}"
        local_path = os.path.join(LOCAL_DIR, tool, image_file)

        print(f"⬇️  Downloading {tool}:{version} → {image_file}")

        try:
            response = requests.get(image_url, stream=True, timeout=30, verify=False)
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"✅ Downloaded {tool}:{version} → {local_path}\n")
            else:
                print(f"⚠️  Image not found for {tool}:{version} (HTTP {response.status_code}), skipping...\n")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading {tool}:{version}: {e}\n")
            continue


def main():
    print("🚀 HPCSuite Container Image Registry Setup\n")
    create_directory_structure()
    pull_selected_versions()
    print("\n🎉 Process complete. All available images have been processed.\n")


if __name__ == "__main__":
    main()
