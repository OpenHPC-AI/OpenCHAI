#!/bin/bash
set -euo pipefail

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

[[ -f "$ALL_YML" ]] || {
  echo "❌ ERROR: $ALL_YML not found"
  exit 1
}

echo ">>> Configuring OpenLDAP environment variables"
echo

update_var() {
  local key="$1"
  local prompt="$2"
  local default="$3"
  local secret="${4:-false}"

  local current
  current=$(grep -E "^${key}:" "$ALL_YML" | awk -F': ' '{print $2}' | tr -d '"' || true)
  current="${current:-$default}"

  if [[ "$secret" == "true" ]]; then
    read -s -p "$prompt [hidden]: " value
    echo
  else
    read -p "$prompt [$current]: " value
  fi

  value="${value:-$current}"

  if grep -qE "^${key}:" "$ALL_YML"; then
    sed -i "s|^${key}:.*|${key}: \"${value}\"|" "$ALL_YML"
  else
    echo "${key}: \"${value}\"" >> "$ALL_YML"
  fi
}

# ---------------- LDAP core ----------------
update_var ldap_version_tag     "Enter the LDAP Version tag" "2.6.8"
update_var ldap_base_dn         "Enter the LDAP Base DN" "dc=nsm,dc=in"
update_var LDAP_ROOT_PASSWD     "Enter LDAP root password" "" true
update_var BASE_PRIMARY_DC      "Enter base primary DC (example: in)" "in"
update_var BASE_SECONDARY_DC    "Enter base secondary DC (example: nsm)" "nsm"
update_var BASE_SUBDOMAIN_DC    "Enter base subdomain DC (example: cdac)" "cdac"

# ---------------- Organizational Units ----------------
update_var OU1 "Enter OU1 name" "People"
update_var OU2 "Enter OU2 name" "Group"
update_var OU3 "Enter OU3 name" "CDAC"
update_var OU4 "Enter OU4 name" "support"
update_var OU5 "Enter OU5 name" "nsmext"
update_var OU6 "Enter OU6 name" "nsmapp"
update_var OU7 "Enter OU7 name" "IIT"

echo
echo "✅ OpenLDAP variables updated successfully in group_vars/all.yml"
