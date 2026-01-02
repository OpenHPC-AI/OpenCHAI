#!/bin/bash

base_dir="/OpenCHAI"
MODULE_DIR="$base_dir/chai_setup/modules"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

echo "=========================================="
echo "      OpenCHAI / Headnode CLI Installer"
echo "=========================================="

# Ensure YAML exists
if [[ ! -f "$ALL_YML" ]]; then
    echo "❌ ERROR: ../automation/ansible/group_vars/all.yml not found!"
    exit 1
fi


run_module() {
    module="$1"
    echo -e "\n------------------------------------------"
    echo "Running module: $module"
    echo "------------------------------------------"
    bash "$MODULE_DIR/$module"
}


# Execute all modules
run_module "update_vars_pxe.sh"
run_module "lustre_vars.sh"
run_module "drbd_vars.sh"
run_module "swarm_vars.sh"
run_module "xcat_vars.sh"
run_module "ldap_vars.sh"
run_module "slurm_vars.sh"
run_module "application_vars.sh"
run_module "monitoring_vars.sh"

echo -e "\n🎉 All configuration modules completed!"
echo "Your ../automation/ansible/group_vars/all.yml has been fully updated."
