#!/usr/bin/env python3
import os
import requests

BASE_URL = "https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/v1.0/hpcsuite_registry/container_img_reg"
TOOLS = ["chakshu-front_reg", "ganglia_reg", "ldap_reg", "nagios_reg", "osticket_reg", "xCAT_reg"]
LOCAL_DIR = os.path.join(os.getcwd(), "hpcsuite_registry/container_img_reg")


def create_directory_structure():
    """Create base directories for tool registries."""
    os.makedirs(LOCAL_DIR, exist_ok=True)
    for tool in TOOLS:
        tool_path = os.path.join(LOCAL_DIR, tool)
        os.makedirs(tool_path, exist_ok=True)
    print(f"✅ Directory structure created under: {LOCAL_DIR}\n")


def list_available_versions(tool_name):
    """
    Try to fetch available versions from the remote repo.
    Assumes there is a 'versions.txt' file per tool at the base URL.
    """
    versions_url = f"{BASE_URL}/{tool_name}/versions.txt"
    try:
        response = requests.get(versions_url, timeout=10, verify=False)
        if response.status_code == 200:
            versions = response.text.strip().splitlines()
            return versions
        else:
            return []
    except requests.exceptions.RequestException:
        return []


def select_tool_version(tool_name):
    """Ask user to select a version from available options."""
    versions = list_available_versions(tool_name)

    if not versions:
        print(f"⚠️  No version list found for {tool_name}. You may need to check the repository.")
        version = input(f"Enter version manually for {tool_name}: ").strip()
    else:
        print(f"\nAvailable versions for {tool_name}:")
        for idx, v in enumerate(versions, 1):
            print(f"  {idx}. {v}")
        choice = input(f"Select version number for {tool_name}: ").strip()

        try:
            version = versions[int(choice) - 1]
        except (ValueError, IndexError):
            print("❌ Invalid choice, skipping...")
            return None

    return version


def pull_selected_versions():
    """Pull or simulate download of selected container images."""
    for tool in TOOLS:
        version = select_tool_version(tool)
        if not version:
            continue

        image_url = f"{BASE_URL}/{tool}/{version}.tar"
        local_path = os.path.join(LOCAL_DIR, tool, f"{version}.tar")

        print(f"⬇️  Downloading {tool}:{version} from {image_url} ...")

        try:
            response = requests.get(image_url, stream=True, timeout=20, verify=False)
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
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
    print("\n🎉 All selected container image versions have been downloaded successfully.")


if __name__ == "__main__":
    main()

