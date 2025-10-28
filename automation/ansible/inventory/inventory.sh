#!/bin/bash
set -e

base_dir="/OpenCHAI"
inventory_script_path="$base_dir/automation/ansible/inventory/inventory_def.py"
inventory_file_path="$base_dir/automation/ansible/inventory/inventory_def.txt"

python3 "$inventory_script_path" --list --input-file "$inventory_file_path"
