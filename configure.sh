#!/bin/bash
# -------------------------------------------------------------------
# Script Name: configure.sh
# Purpose: Automatically configure OpenCHAI manager tool to use for cluster
# Author: Satish Gupta
# -------------------------------------------------------------------

set -e  # Exit on any error

# Detect the absolute path where the script is executed (OpenCHAI base path)
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Move to OpenCHAI root directory if needed
if [[ ! -d "$BASE_DIR/automation" ]]; then
    echo "❌ Please run this script from within the OpenCHAI repository root."
    exit 1
fi

SYSTEM_ANSIBLE_CFG="/etc/ansible/ansible.cfg"
ANSIBLE_CFG="$BASE_DIR/automation/ansible/ansible.cfg"
ALL_YML="$BASE_DIR/automation/ansible/group_vars/all.yml"
INVENTORY_SCRIPT="$BASE_DIR/automation/ansible/inventory/inventory.sh"
INVENTORY_DEF="$BASE_DIR/chai_setup/inventory_def.txt"
INVENTORY_TARGET="$BASE_DIR/automation/ansible/inventory/inventory_def.txt"

# -----------------------------------------------------------------------------------------------------------------
# 0️⃣ Ensure Ansible is installed And Inventory File of Cluster Service Nodes Updated according to Your Environment
# -----------------------------------------------------------------------------------------------------------------
echo "🔍 Checking for Ansible installation..."

if ! command -v ansible >/dev/null 2>&1; then
    echo "⚠️  Ansible not found. Installing ansible-core and ansible packages..."

    if command -v dnf >/dev/null 2>&1; then
        PKG_MGR="dnf"
    elif command -v yum >/dev/null 2>&1; then
        PKG_MGR="yum"
    else
        echo "❌ No supported package manager found (dnf/yum)."
        exit 1
    fi

    sudo $PKG_MGR -y install epel-release || true
    sudo $PKG_MGR -y install ansible-core ansible || {
        echo "❌ Failed to install Ansible. Please check your network or repos."
        exit 1
    }
    echo "✅ Ansible successfully installed."
else
    echo "✅ Ansible is already installed."
fi

# -----------------------------------------------------------------------------------------------------------------
# Check if rpm-stack tar file exists
# -----------------------------------------------------------------------------------------------------------------
echo ""
read -rp "📁 Have you pulled or copied the rpm-stack.tar into ./OpenCHAI at your environment? (yes/no): " CONFIRM

if [ -f "$BASE_DIR/rpm-stack.tar" ]; then
    echo "✅ rpm-stack.tar found in $BASE_DIR"
    echo "Extracting rpm-stack..."
    tar -xvf "$BASE_DIR/rpm-stack.tar" -C "$BASE_DIR" || {
        echo "❌ Failed to extract rpm-stack.tar"
        exit 1
    }

    # Check for enroot_pyxis_config.tgz inside rpm-stack/mount
    if [ -f "$BASE_DIR/rpm-stack/mount/enroot_pyxis_config.tgz" ]; then
        echo "Extracting enroot_pyxis_config.tgz..."
        tar -xvf "$BASE_DIR/rpm-stack/mount/enroot_pyxis_config.tgz" -C "$BASE_DIR/rpm-stack/mount" || {
            echo "❌ Failed to extract enroot_pyxis_config.tgz"
            exit 1
        }
        echo "✅ Extraction complete."
        echo "Removing rm-stack.tar file after successfully extraction !"
        rm -rf "$BASE_DIR/rpm-stack.tar"
        rm -rf "$BASE_DIR/rpm-stack/mount/enroot_pyxis_config.tgz"
    else
        echo "⚠️  enroot_pyxis_config.tgz not found in $BASE_DIR/rpm-stack/mount"
    fi
else
    echo "❌ rpm-stack.tar.gz not found in $BASE_DIR"
    echo "Please place the rpm-stack.tar file in $BASE_DIR and rerun the script."
    exit 1
fi


# -------------------------------------------------------------------
# 🧩 Confirm inventory file readiness
# -------------------------------------------------------------------
echo ""
read -rp "📁 Have you updated the inventory file ($INVENTORY_DEF) according to your environment? (yes/no): " CONFIRM

if [[ "$CONFIRM" =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "✅ Copying updated inventory file..."
    cp -f "$INVENTORY_DEF" "$INVENTORY_TARGET"
    echo "📦 Copied: $INVENTORY_DEF → $INVENTORY_TARGET"
else
    echo "⚠️  Please update the inventory file before running this script."
    echo "🛑 Terminating configuration setup."
    exit 1
fi

# -------------------------------------------------------------------
# 🔧 Configure OpenCHAI manager tool paths
# -------------------------------------------------------------------
echo ""
echo "🔧 Configuring OpenCHAI manager tool paths..."
echo "Detected base directory: $BASE_DIR"
echo ""

# 1️⃣ Update ansible.cfg inventory path
if [[ -f "$ANSIBLE_CFG" ]]; then
    sed -i "s|inventory *= /OpenCHAI/automation/ansible/inventory/inventory.sh|inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh|" "$ANSIBLE_CFG"
    echo "✅ Updated: $ANSIBLE_CFG"
else
    echo "⚠️  File not found: $ANSIBLE_CFG"
fi

# 2️⃣ Update all.yml base paths
if [[ -f "$ALL_YML" ]]; then
    sed -i "s|base_dir: /OpenCHAI|base_dir: $BASE_DIR|" "$ALL_YML"
    #sed -i "s|rpm_stack_path: /OpenCHAI/rpm-stack|rpm_stack_path: $BASE_DIR/rpm-stack|" "$ALL_YML"
    #sed -i "s|configuration_dir_path: /OpenCHAI/rpm-stack/mount|configuration_dir_path: $BASE_DIR/rpm-stack/mount|" "$ALL_YML"
    #sed -i "s|roles_parent_path: /OpenCHAI/automation/ansible/roles_library|roles_parent_path: $BASE_DIR/automation/ansible/roles_library|" "$ALL_YML"
    echo "✅ Updated: $ALL_YML"
else
    echo "⚠️  File not found: $ALL_YML"
fi

# 3️⃣ Update inventory.sh base_dir
if [[ -f "$INVENTORY_SCRIPT" ]]; then
    sed -i "s|base_dir=.*|base_dir=\"$BASE_DIR\"|" "$INVENTORY_SCRIPT"
    echo "✅ Updated: $INVENTORY_SCRIPT"
else
    echo "⚠️  File not found: $INVENTORY_SCRIPT"
fi

# -------------------------------------------------------------------
# 4️⃣ Set up Ansible local configuration
# -------------------------------------------------------------------

ANSIBLE_CFG_PATH="$BASE_DIR/automation/ansible/ansible.cfg"
BASHRC_FILE="$HOME/.bashrc"

# Export ANSIBLE_CONFIG for current session
export ANSIBLE_CONFIG="$ANSIBLE_CFG_PATH"

# Persist it in ~/.bashrc if not already present
if ! grep -q "ANSIBLE_CONFIG=" "$BASHRC_FILE"; then
    echo "export ANSIBLE_CONFIG=$ANSIBLE_CFG_PATH" >> "$BASHRC_FILE"
    echo "✅ Added ANSIBLE_CONFIG export to $BASHRC_FILE"
else
    echo "ℹ️ ANSIBLE_CONFIG already set in $BASHRC_FILE"
fi

# Source ~/.bashrc so that the change takes effect immediately
source "$BASHRC_FILE"

echo "✅ Using Ansible config: $ANSIBLE_CONFIG"

echo ""
echo "🎉 OpenCHAI manager tool configuration paths updated successfully!"

