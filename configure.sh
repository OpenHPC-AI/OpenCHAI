#!/bin/bash
# -------------------------------------------------------------------
# Script Name: configure.sh
# Purpose: Automatically configure OpenCHAI manager tool to use for cluster 
# Author: Satish Gupta
# -------------------------------------------------------------------

# Exit immediately if a command exits with a non-zero status
set -e

# Detect the absolute path where the script is executed (OpenCHAI base path)
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Move to OpenCHAI root directory if needed
if [[ ! -d "$BASE_DIR/automation" ]]; then
    echo "Please run this script from within the OpenCHAI repository root."
    exit 1
fi


SYSTEM_ANSIBLE_CFG="/etc/ansible/ansible.cfg"
ANSIBLE_CFG="$BASE_DIR/automation/ansible/ansible.cfg"
ALL_YML="$BASE_DIR/automation/ansible/group_vars/all.yml"

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

# -------------------------------------------------------------------
# 3️⃣ Update or add inventory path in system-wide /etc/ansible/ansible.cfg
# -------------------------------------------------------------------
if [[ -f "$SYSTEM_ANSIBLE_CFG" ]]; then
    echo ""
    echo "🔍 Checking system Ansible configuration: $SYSTEM_ANSIBLE_CFG"

    # Check if inventory line exists
    if grep -q "^inventory" "$SYSTEM_ANSIBLE_CFG"; then
        # If it points to /OpenCHAI, replace it
        if grep -q "/OpenCHAI" "$SYSTEM_ANSIBLE_CFG"; then
            sed -i "s|inventory *= */OpenCHAI.*|inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh|" "$SYSTEM_ANSIBLE_CFG"
            echo "✅ Updated inventory path in: $SYSTEM_ANSIBLE_CFG"
        else
            echo "ℹ️  Inventory path already customized — no changes made."
        fi
    else
        # Add the inventory line under [defaults] section
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

