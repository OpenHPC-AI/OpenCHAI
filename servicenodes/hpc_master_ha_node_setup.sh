#!/bin/bash

base_dir="/OpenCHAI"
provision_playbook="ha_master.yml"
ansible-playbook $base_dir/automation/ansible/playbook_library/provision/$provision_playbook -l hpc_master
