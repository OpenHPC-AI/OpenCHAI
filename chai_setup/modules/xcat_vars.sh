#!/bin/bash
set -euo pipefail

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

if [[ ! -f "$ALL_YML" ]]; then
  echo "❌ all.yml not found at $ALL_YML"
  exit 1
fi

echo "================================================="
echo "   OpenCHAI xCAT Configuration Variable Setup"
echo "================================================="
echo "Updating: $ALL_YML"
echo

# Helper: read value with default
read_var() {
  local key="$1"
  local prompt="$2"
  local secret="${3:-false}"

  local current
  current=$(grep -E "^${key}:" "$ALL_YML" | awk '{print $2}' || true)

  if [[ "$secret" == "true" ]]; then
    read -s -p "$prompt [hidden]: " value
    echo
  else
    read -p "$prompt [$current]: " value
  fi

  value="${value:-$current}"

  if grep -qE "^${key}:" "$ALL_YML"; then
    sed -i "s|^${key}:.*|${key}: ${value}|" "$ALL_YML"
  else
    echo "${key}: ${value}" >> "$ALL_YML"
  fi
}

###############################################################################
# xCAT / HA VARIABLES
###############################################################################
read_var "xcat_vip_ip"        "Enter xCAT Virtual IP (VIP)"
read_var "xcat_vip_interface" "Enter xCAT VIP Interface"
read_var "private_interface"  "Enter private Ethernet interface"

###############################################################################
# MySQL VARIABLES (secure)
###############################################################################
read_var "mysql_port"      "Enter MySQL port" false
read_var "mysql_admin_pw"  "Enter MySQL admin password (alphanumeric only)" true
read_var "mysql_root_pw"   "Enter MySQL root password (alphanumeric only)" true

###############################################################################
# DNS / DHCP VARIABLES
###############################################################################
read_var "domain_name"     "Enter DNS domain name"
read_var "dhcp_interface" "Enter DHCP interfaces (comma separated)"

###############################################################################
# xCAT IMAGE / VERSION VARIABLES
###############################################################################
read_var "xcat_version_tag"       "Enter xCAT version tag"
read_var "xcat_repo_version_tag"  "Enter xCAT repo version tag"

echo
echo "✔ All variables successfully updated in all.yml"
echo "👉 You can now run ansible-playbook without prompts"
echo "================================================="
