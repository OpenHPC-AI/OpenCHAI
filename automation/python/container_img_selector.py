#!/usr/bin/env python3
import os
import re
import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

# ============================
# GLOBAL CONFIGURATIONS
# ============================

TOOLS = [
    "chakshu-front_reg",
    "ganglia_reg",
    "ldap_reg",
    "nagios_reg",
    "osticket_reg",
    "xCAT_reg"
]

# Root local directory where images will be stored
LOCAL_DIR = "/OpenCHAI/hpcsuite_registry/container_img_reg"

# Allow multiple image formats
VALID_EXTENSIONS = (".tar", ".img", ".gz", ".xz", ".bz2", ".tgz")

# Global dynamic BASE_URL (set after OS selection)
BASE_URL = None


# ============================
# OS VERSION SELECTION
# ============================

def select_os_version_from_network(base_registry_url, no_cert_check=True):
    """
    Fetch list of OS-version directories from the network registry.
    Example:
        https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/container_img_reg
    """
    print("\n🔍 Fetching OS-version list from registry...")

    try:
        resp = requests.get(base_registry_url, verify=not no_cert_check, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ ERROR: Cannot fetch OS version list:\n{e}")
        return None

    # Match subdirectories → alma9, rocky9, rocky8, etc.
    os_versions = re.findall(r'href="([^"/]+)/"', resp.text)

    if not os_versions:
        print("⚠️ No OS version directories found in registry.")
        return None

    os_versions = sorted(list(set(os_versions)))

    print("\n📂 Available OS Versions in Registry:")
    for i, v in enumerate(os_versions, 1):
        print(f"  {i}) {v}")

    # User selection
    while True:
        choice = input(f"\nSelect OS-Version (1-{len(os_versions)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(os_versions):
            selected = os_versions[int(choice) - 1]
            break
        print("❌ Invalid selection. Please try again.")

    # Construct final BASE_URL
    BASE_URL = f"{base_registry_url}/{selected}"

    print(f"\n✅ Selected OS-Version: {selected}")
    print(f"🔗 BASE_URL = {BASE_URL}\n")

    return BASE_URL, selected


# ============================
# LOCAL DIRECTORY SETUP
# ============================

def create_directory_structure():
    """Ensure full directory structure exists."""
    os.makedirs(LOCAL_DIR, exist_ok=True)

    for tool in TOOLS:
        os.makedirs(os.path.join(LOCAL_DIR, tool), exist_ok=True)

    print(f"✅ Local directory structure ready: {LOCAL_DIR}\n")


# ============================
# FETCH VERSION LIST (REMOTE)
# ============================

def list_available_versions(tool_name):
    """Fetch available version directories for a tool."""
    tool_url = f"{BASE_URL}/{tool_name}/"

    try:
        resp = requests.get(tool_url, timeout=10, verify=False)
        if resp.status_code != 200:
            print(f"⚠️ Cannot access {tool_url} (HTTP {resp.status_code})")
            return []

        matches = re.findall(r'href="([^"/]+)/"', resp.text)

        versions = []
        for m in matches:
            if m == "latest" or re.match(r'^[vV]?\d+(\.\d+)*$', m):
                versions.append(m)

        return sorted(set(versions))

    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting versions for {tool_name}: {e}")
        return []


# ============================
# FIND ACTUAL IMAGE FILE
# ============================

def find_image_file(tool_name, version):
    """Find real image filename inside version directory."""
    version_url = f"{BASE_URL}/{tool_name}/{version}/"

    try:
        resp = requests.get(version_url, timeout=10, verify=False)
        if resp.status_code != 200:
            return None

        files = re.findall(r'href="([^"]+)"', resp.text)

        for f in files:
            if f.lower().endswith(VALID_EXTENSIONS) or "cdac_" in f:
                return f

        return None

    except requests.exceptions.RequestException:
        return None


# ============================
# TOOL VERSION SELECTOR
# ============================

def select_tool_version(tool_name):
    """Display list of versions and ask user to pick."""
    versions = list_available_versions(tool_name)

    if not versions:
        print(f"⚠️ No versions found for {tool_name}. Skipping...\n")
        return None

    print(f"\n📦 Versions available for: {tool_name}")
    for i, v in enumerate(versions, 1):
        print(f"  {i}) {v}")

    choice = input(f"Select version for {tool_name} (blank to skip): ").strip()
    if not choice:
        print(f"⏭️ Skipping {tool_name}\n")
        return None

    try:
        return versions[int(choice) - 1]
    except:
        print(f"❌ Invalid selection for {tool_name}, skipping...\n")
        return None


# ============================
# DOWNLOAD SELECTED IMAGES
# ============================

def pull_selected_versions():
    """Download selected container images."""
    for tool in TOOLS:
        print(f"\n🔍 Checking {tool}...")

        version = select_tool_version(tool)
        if not version:
            continue

        img_file = find_image_file(tool, version)
        if not img_file:
            print(f"⚠️ No image found for {tool}:{version}. Skipping...\n")
            continue

        img_url = f"{BASE_URL}/{tool}/{version}/{img_file}"
        save_path = os.path.join(LOCAL_DIR, tool, img_file)

        print(f"⬇️ Downloading {tool}:{version} → {img_file}")

        try:
            with requests.get(img_url, stream=True, timeout=30, verify=False) as resp:
                if resp.status_code != 200:
                    print(f"⚠️ Download failed (HTTP {resp.status_code})")
                    continue

                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        if chunk:
                            f.write(chunk)

            print(f"✅ Downloaded: {save_path}\n")

        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading {tool}:{version}: {e}\n")


# ============================
# MAIN ENTRY
# ============================

def main():
    print("🚀 HPCSuite Container Image Registry Selector\n")

    # Base URL WITHOUT OS version
    BASE_ROOT = "https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/container_img_reg"

    # Step 1: User selects OS-version
    result = select_os_version_from_network(BASE_ROOT, no_cert_check=True)
    if not result:
        print("❌ Cannot continue without OS-version registry. Exiting.")
        return

    BASE_URL_SELECTED, OS_VERSION_SELECTED = result

    # Use global BASE_URL inside other functions
    global BASE_URL
    BASE_URL = BASE_URL_SELECTED

    print(f"🌐 Using BASE_URL = {BASE_URL}\n")

    # Step 2: Prepare local directories
    create_directory_structure()

    # Step 3: Download images
    pull_selected_versions()

    print("\n🎉 DONE — All selected images have been processed.\n")


if __name__ == "__main__":
    main()
