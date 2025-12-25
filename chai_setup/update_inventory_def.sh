#!/bin/bash
base_dir="/OpenCHAI"
INVENTORY_DEF="$base_dir/chai_setup/inventory_def.txt"
INVENTORY_TARGET="$base_dir/automation/ansible/inventory/inventory_def.txt"
cp -f "$INVENTORY_DEF" "$INVENTORY_TARGET" || error_exit "Failed to copy $INVENTORY_DEF to $INVENTORY_TARGET"
