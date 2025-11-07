#!/usr/bin/env python3
import os
import re
import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Suppress certificate warnings
urllib3.disable_warnings(InsecureRequestWarning)

BASE_URL = "https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/container_img_reg/alma8.9"
TOOLS = ["chakshu-front_reg", "ganglia_reg", "ldap_reg", "nagios_reg", "osticket_reg", "xCAT_reg"]
LOCAL_DIR = "../../hpcsuite_registry/container_img_reg"

# Allow multiple image extensions
VALID_EXTENSIONS = (".tar", ".img", ".gz", ".xz", ".bz2", ".tgz")


def create_directory_structure():
    """Ensure local directories exist."""
    os.makedirs(LOCAL_DIR, exist_ok=True)
    for tool in TOOLS:
        os.makedirs(os.path.join(LOCAL_DIR, tool), exist_ok=True)
    print(f"✅ Directory structure created under: {os.path.abspath(LOCAL_DIR)}\n")


def list_available_versions(tool_name):
    """Fetch available version directories dynamically from the remote registry."""
    tool_url = f"{BASE_URL}/{tool_name}/"
    try:
        response = requests.get(tool_url, timeout=10, verify=False)
        if response.status_code != 200:
            print(f"⚠️  Unable to access {tool_url} (HTTP {response.status_code})")
            return []

        # Match directory names ending with '/' in href links
        matches = re.findall(r'href="([^"]+/)"', response.text)
        versions = []

        for m in matches:
            name = m.strip("/")

            # Accept 'latest' or any semantic version-like string
            if name.lower() == "latest" or re.match(r'^[vV]?\d+(\.\d+)*$', name):
                versions.append(name)

        return sorted(set(versions))
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching versions for {tool_name}: {e}")
        return []


def find_image_file(tool_name, version):
    """Detect actual image filename from inside the version directory."""
    version_url = f"{BASE_URL}/{tool_name}/{version}/"
    try:
        response = requests.get(version_url, timeout=10, verify=False)
        if response.status_code != 200:
            return None

        matches = re.findall(r'href="([^"]+)"', response.text)

        for file in matches:
            if file.lower().endswith(VALID_EXTENSIONS) or "cdac_" in file:
                return file
        return None
    except requests.exceptions.RequestException:
        return None


def select_tool_version(tool_name):
    """Prompt user to choose a version, skip if unavailable."""
    versions = list_available_versions(tool_name)
    if not versions:
        print(f"⚠️  No version directories found for {tool_name}. Skipping...\n")
        return None

    print(f"\n📦 Available versions for {tool_name}:")
    for i, v in enumerate(versions, 1):
        print(f"  {i}. {v}")

    choice = input(f"Select version number for {tool_name} (or press Enter to skip): ").strip()
    if not choice:
        print(f"⏭️  Skipping {tool_name}...\n")
        return None

    try:
        return versions[int(choice) - 1]
    except (ValueError, IndexError):
        print(f"❌ Invalid selection for {tool_name}, skipping...\n")
        return None


def pull_selected_versions():
    """Download selected container image files."""
    for tool in TOOLS:
        print(f"\n🔍 Checking registry for {tool}...")
        version = select_tool_version(tool)
        if not version:
            continue

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
                print(f"⚠️  Failed to download {tool}:{version} (HTTP {response.status_code})\n")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading {tool}:{version}: {e}\n")


def main():
    print("🚀 HPCSuite Container Image Registry Setup\n")
    create_directory_structure()
    pull_selected_versions()
    print("\n🎉 Process complete. All available images have been processed.\n")


if __name__ == "__main__":
    main()

