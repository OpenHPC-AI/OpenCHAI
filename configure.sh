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
    sed -i "s|rpm_stack_path: /OpenCHAI/rpm-stack|rpm_stack_path: $BASE_DIR/rpm-stack|" "$ALL_YML"
    sed -i "s|configuration_dir_path: /OpenCHAI/rpm-stack/mount|configuration_dir_path: $BASE_DIR/rpm-stack/mount|" "$ALL_YML"
    sed -i "s|roles_parent_path: /OpenCHAI/automation/ansible/roles_library|roles_parent_path: $BASE_DIR/automation/ansible/roles_library|" "$ALL_YML"
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
# 4️⃣ Update or add inventory path in system-wide /etc/ansible/ansible.cfg
# -------------------------------------------------------------------
if [[ -f "$SYSTEM_ANSIBLE_CFG" ]]; then
    echo ""
    echo "🔍 Checking system Ansible configuration: $SYSTEM_ANSIBLE_CFG"

    if grep -q "^inventory" "$SYSTEM_ANSIBLE_CFG"; then
        if grep -q "/OpenCHAI" "$SYSTEM_ANSIBLE_CFG"; then
            sed -i 's|^[[:space:]]*inventory[[:space:]]*=.*OpenCHAI.*|inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh|" "$SYSTEM_ANSIBLE_CFG"
            echo "✅ Updated inventory path in: $SYSTEM_ANSIBLE_CFG"
        else
            echo "ℹ️  Inventory path already customized — no changes made."
        fi
    else
        if grep -q "^\[defaults\]" "$SYSTEM_ANSIBLE_CFG"; then
            sed -i "/^\[defaults\]/a inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh" "$SYSTEM_ANSIBLE_CFG"
            echo "✅ Added inventory path under [defaults] section in: $SYSTEM_ANSIBLE_CFG"
        else
            echo "[defaults]" >> "$SYSTEM_ANSIBLE_CFG"
            echo "inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh" >> "$SYSTEM_ANSIBLE_CFG"
            echo "✅ Created [defaults] section and added inventory path in: $SYSTEM_ANSIBLE_CFG"
        fi
    fi
else
    echo ""
    echo "⚠️  System-wide Ansible config not found at: $SYSTEM_ANSIBLE_CFG"
    echo "👉 Skipping system Ansible config update."
fi

echo ""
echo "🎉 OpenCHAI manager tool configuration paths updated successfully!"

