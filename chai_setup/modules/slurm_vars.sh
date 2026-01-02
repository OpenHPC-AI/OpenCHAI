#!/usr/bin/env bash
set -euo pipefail

############################################
# Slurm Variable Update Module
############################################

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

if [[ ! -f "$ALL_YML" ]]; then
  echo "❌ ERROR: $ALL_YML not found"
  exit 1
fi

echo "=============================================="
echo " Slurm Variable Configuration"
echo " File: $ALL_YML"
echo "=============================================="

############################################
# Generic YAML updater (SAFE)
############################################
update_var() {
  local key="$1"
  local prompt="$2"

  # Read current value safely
  local current
  current=$(grep -E "^${key}:" "$ALL_YML" | head -n1 | sed "s/^${key}:[[:space:]]*//")

  read -rp "${prompt} (default: ${current}): " input
  input="${input:-$current}"

  # Escape sed-sensitive characters
  local safe_value
  safe_value=$(printf '%s\n' "$input" | sed 's/[\/&|\\]/\\&/g')

  if grep -qE "^${key}:" "$ALL_YML"; then
    sed -i "s|^${key}:.*|${key}: ${safe_value}|" "$ALL_YML"
  else
    echo "${key}: ${safe_value}" >> "$ALL_YML"
  fi
}

############################################
# Slurm Variables
############################################
update_var slurm_version "Slurm Version"

echo
echo "✅ Slurm variables updated successfully."
echo "=============================================="
