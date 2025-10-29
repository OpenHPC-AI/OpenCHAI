⚙️ Automation

This section forms the core of the OpenCHAI Manager tool, powering the automated provisioning and management of the HPC+AI cluster.
It is built around Ansible, Bash, and Python, and is designed to be modular, scalable, and version-controlled.

The automation directory serves as a central workspace containing all automation scripts and configuration files required for seamless deployment, configuration, and lifecycle management of the HPC-AI cluster.

🔍 Overview

The automation directory includes:

Ansible-based automation workspace

Python scripts for cluster logic and configuration generation

Bash scripts for orchestration, setup, and system-level automation

📁 Directory Structure
Ansible Directory — automation/ansible/

Contains all Ansible-related configurations, inventories, playbooks, and role definitions.

ansible.cfg
Main Ansible configuration file.
(Path: automation/ansible/ansible.cfg)

inventory/
Contains dynamic and static inventories of all node types in the cluster.
(Path: automation/ansible/inventory/)

group_vars/
Stores global variables and environment definitions used across playbooks and roles.
(Path: automation/ansible/group_vars/)

playbook_library/
Contains playbooks for pre-requisites, tool installation, configuration, and cluster deployment.
(Path: automation/ansible/playbook_library/)

roles_library/
Houses all Ansible roles — the core automation logic for specific tools and technologies, invoked by playbooks from the playbook library.
(Path: automation/ansible/roles_library/)

Bash Directory

Contains shell scripts that automate system setup, configuration management, and orchestration tasks supporting cluster deployment.

Python Directory

Contains Python scripts responsible for generating configuration files, parsing inventories, and handling dynamic automation tasks.


