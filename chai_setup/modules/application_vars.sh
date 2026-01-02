#!/usr/bin/env bash
set -euo pipefail

############################################
# Application Variable Update Module
############################################

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

if [[ ! -f "$ALL_YML" ]]; then
  echo "❌ ERROR: $ALL_YML not found"
  exit 1
fi

echo "=============================================="
echo " Application Variable Configuration"
echo " File: $ALL_YML"
echo "=============================================="

############################################
# Generic YAML updater (SAFE)
############################################
update_var() {
  local key="$1"
  local prompt="$2"

  # Read full RHS safely (supports spaces)
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
# Application Variables
############################################
update_var application_base_dir "Application base directory"
update_var nvidia_cuda_version  "NVIDIA CUDA version"
update_var intel_installer      "Intel installer package/version"

echo
echo "✅ Application variables updated successfully."
echo "=============================================="

