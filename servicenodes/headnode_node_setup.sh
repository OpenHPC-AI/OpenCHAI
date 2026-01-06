#!/bin/bash

base_dir="/OpenCHAI"
provision_playbook="headnode.yml"
ansible-playbook $base_dir/automation/ansible/playbook_library/provision/$provision_playbook -l headnode
