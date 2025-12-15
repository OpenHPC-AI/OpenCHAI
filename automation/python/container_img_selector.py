#!/usr/bin/env python3
import os
import re
import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Disable SSL warnings
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

LOCAL_DIR = "/OpenCHAI/hpcsuite_registry/container_img_reg"

# ANY valid container-file extension + filenames containing cdac_
VALID_EXTENSIONS = (".tar", ".img", ".gz", ".xz", ".bz2", ".tgz")

BASE_URL = None   # dynamic after OS selection


# ============================
# OS VERSION SELECTION
# ============================

def select_os_version_from_network(base_registry_url, no_cert_check=True):
    """Discover OS-version directories (alma9, rocky9, etc.)"""
    print("\n🔍 Fetching OS-version list from registry...")

    try:
        resp = requests.get(base_registry_url, verify=not no_cert_check, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ ERROR: Cannot fetch OS version list:\n{e}")
        return None

    os_versions = re.findall(r'href="([^"/]+)/"', resp.text)
    if not os_versions:
        print("⚠️ No OS version directories found.")
        return None

    os_versions = sorted(set(os_versions))

    print("\n📂 Available OS Versions:")
    for i, v in enumerate(os_versions, 1):
        print(f"  {i}) {v}")

    while True:
        choice = input("\nSelect OS Version: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(os_versions):
            selected = os_versions[int(choice) - 1]
            break
        print("❌ Invalid choice. Try again.")

    BASE_URL = f"{base_registry_url}/{selected}"
    print(f"\n✅ Selected OS Version: {selected}")
    print(f"🔗 BASE_URL = {BASE_URL}\n")

    return BASE_URL, selected


# ============================
# LOCAL DIRECTORY SETUP
# ============================

def create_directory_structure():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    for tool in TOOLS:
        os.makedirs(os.path.join(LOCAL_DIR, tool), exist_ok=True)
    print(f"✅ Local directory structure ready at: {LOCAL_DIR}\n")


# ============================
# RECURSIVE VERSION FINDER
# ============================

def recursive_list_registry(url):
    """Fetch raw directory HTML and return all subfolders/files."""
    try:
        resp = requests.get(url, timeout=10, verify=False)
        resp.raise_for_status()
        return re.findall(r'href="([^"]+)"', resp.text)
    except:
        return []


def get_all_versions_recursive(tool_name):
    """
    Detect ALL version directories under tool_name.
    Supports:
      - digits        (1, 2024)
      - alphabets     (alpha, stable)
      - words         (release, latest)
      - mixed         (v1.2.3, rocky9.6, beta_01)
    """
    tool_url = f"{BASE_URL}/{tool_name}/"
    html_items = recursive_list_registry(tool_url)

    version_dirs = []

    for item in html_items:
        # Only directories
        if not item.endswith("/"):
            continue

        name = item.rstrip("/")

        # Ignore parent/current dirs
        if name in ("..", "."):
            continue

        # Accept ANY alphanumeric folder name
        # (letters, digits, dot, dash, underscore)
        if re.match(r'^[A-Za-z0-9._-]+$', name):
            version_dirs.append(name)

    return sorted(set(version_dirs))


# ============================
# FIND ALL IMAGES IN VERSION
# ============================

def get_images_in_version(tool_name, version):
    """
    Recursively find ALL images under a version folder.
    Handles deeply nested structures.
    """
    version_url = f"{BASE_URL}/{tool_name}/{version}/"
    items = recursive_list_registry(version_url)

    found_images = []

    for item in items:
        # Skip parent folders
        if item in ("../", "/"):
            continue

        # Case 1: It's a subdirectory → search inside it
        if item.endswith("/"):
            sub_url = f"{version_url}{item}"
            sub_items = recursive_list_registry(sub_url)

            for f in sub_items:
                if ":" in f or f.endswith(VALID_EXTENSIONS) or "cdac_" in f:
                    found_images.append(f"{item}{f}")

        # Case 2: Direct file under version folder
        else:
            if ":" in item or item.endswith(VALID_EXTENSIONS) or "cdac_" in item:
                found_images.append(item)

    return found_images


# ============================
# TOOL VERSION SELECTOR
# ============================

def select_tool_version(tool_name):
    versions = get_all_versions_recursive(tool_name)

    if not versions:
        print(f"⚠️ No versions found for {tool_name}. Skipping...\n")
        return None

    print(f"\n📦 Versions available for: {tool_name}")
    for i, v in enumerate(versions, 1):
        print(f"  {i}) {v}")

    choice = input(f"Select version for {tool_name} (blank=skip): ").strip()
    if not choice:
        print(f"⏭️ Skipping {tool_name}\n")
        return None

    if not (choice.isdigit() and 1 <= int(choice) <= len(versions)):
        print(f"❌ Invalid choice. Skipping {tool_name}...\n")
        return None

    return versions[int(choice) - 1]


# ============================
# DOWNLOAD SELECTED IMAGES
# ============================

def pull_selected_versions():
    """Download selected container images with multi-select support."""
    for tool in TOOLS:
        print(f"\n🔍 Checking {tool}...")

        version = select_tool_version(tool)
        if not version:
            continue

        print(f"🔎 Searching for image files under {tool}/{version}...")

        images = get_images_in_version(tool, version)

        if not images:
            print(f"⚠️ No image files found for {tool}:{version}")
            continue

        print(f"\n📁 Available images for {tool}:{version}:")
        for i, img in enumerate(images, 1):
            print(f"  {i}) {img}")

        # User selection
        selection = input(
            f"\nSelect image(s) to download (comma-separated, blank=skip): "
        ).strip()

        if not selection:
            print(f"⏭️ Skipping {tool}\n")
            continue

        # Parse choices
        try:
            selected_indices = {
                int(x.strip()) for x in selection.split(",") if x.strip().isdigit()
            }
        except:
            print("❌ Invalid selection. Skipping...\n")
            continue

        # Validate selected indices
        selected_images = []
        for idx in selected_indices:
            if 1 <= idx <= len(images):
                selected_images.append(images[idx - 1])
            else:
                print(f"⚠️ Ignoring invalid entry: {idx}")

        if not selected_images:
            print("⏭️ No valid images selected. Skipping...\n")
            continue

        # Download only selected images
        for img in selected_images:
            img_url = f"{BASE_URL}/{tool}/{version}/{img}"
            local_path = os.path.join(LOCAL_DIR, tool, os.path.basename(img))

            print(f"\n⬇️ Downloading: {tool}:{version} → {img}")

            try:
                with requests.get(img_url, stream=True, timeout=30, verify=False) as resp:
                    if resp.status_code != 200:
                        print(f"⚠️ Failed (HTTP {resp.status_code})")
                        continue

                    with open(local_path, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            if chunk:
                                f.write(chunk)

                print(f"✅ Saved: {local_path}")

            except Exception as e:
                print(f"❌ Error downloading {img}: {e}")


# ============================
# MAIN ENTRY
# ============================

def main():
    print("🚀 HPCSuite Container Image Registry Selector\n")

    BASE_ROOT = "https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/container_img_reg"

    result = select_os_version_from_network(BASE_ROOT, no_cert_check=True)
    if not result:
        print("❌ Cannot continue without OS version.")
        return

    global BASE_URL
    BASE_URL, OS_SELECTED = result

    print(f"🌐 Using BASE_URL = {BASE_URL}\n")

    create_directory_structure()
    pull_selected_versions()

    print("\n🎉 DONE — All selected images downloaded.\n")


if __name__ == "__main__":
    main()
