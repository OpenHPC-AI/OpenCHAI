🔧 Configuring OpenCHAI manager tool paths...
Detected base directory: /OpenCHAI

✅ Updated: /OpenCHAI/automation/ansible/ansible.cfg
✅ Updated: /OpenCHAI/automation/ansible/group_vars/all.yml

🎉 OpenCHAI manager tool configuration paths updated successfully!
[root@headnode OpenCHAI]# cat configure.sh
#!/bin/bash
# -------------------------------------------------------------------
# Script Name: setup_openchai_paths.sh
# Purpose: Automatically configure OpenCHAI manager tool paths
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

BASE_ANSIBLE_CFG="/etc/ansible/ansible.cfg"
ANSIBLE_CFG="$BASE_DIR/automation/ansible/ansible.cfg"
ALL_YML="$BASE_DIR/automation/ansible/group_vars/all.yml"

echo "🔧 Configuring OpenCHAI manager tool paths..."
echo "Detected base directory: $BASE_DIR"
echo ""

# 1️⃣ Update ansible.cfg inventory path
if [[ -f "$ANSIBLE_CFG" ]]; then
    sed -i "s|inventory *= /OpenCHAI/automation/ansible/inventory/inventory.sh|inventory = $BASE_DIR/automation/ansible/inventory/                                                       inventory.sh|" "$ANSIBLE_CFG"
    echo "✅ Updated: $ANSIBLE_CFG"
else
    echo "⚠️  File not found: $ANSIBLE_CFG"
fi

# 2️⃣ Update all.yml base paths
if [[ -f "$ALL_YML" ]]; then
    sed -i "s|base_dir: /OpenCHAI|base_dir: $BASE_DIR|" "$ALL_YML"
    sed -i "s|rpm_stack_path: /OpenCHAI/rpm-stack|rpm_stack_path: $BASE_DIR/rpm-stack|" "$ALL_YML"
    sed -i "s|configuration_dir_path: /OpenCHAI/rpm-stack/mount|configuration_dir_path: $BASE_DIR/rpm-stack/mount|" "$ALL_YML"
    sed -i "s|roles_parent_path: /OpenCHAI/automation/ansible/roles_library|roles_parent_path: $BASE_DIR/automation/ansible/roles_                                                       library|" "$ALL_YML"
    echo "✅ Updated: $ALL_YML"
else
    echo "⚠️  File not found: $ALL_YML"
fi

echo ""
echo "🎉 OpenCHAI manager tool configuration paths updated successfully!"
