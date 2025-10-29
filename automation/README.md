This section is the heart of your automated HPC+AI provisioning system, built around Ansible, and designed to be modular, scalable, and version-controllable.

+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#Overview
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

This directory serves as the main Ansible automation workspace. It includes:

#Ansible configurations(ansible/ansible.cfg)
Purpose: Configures how Ansible behaves globally in this directory.

#Inventories of all node types(ansible/inventory/)
Purpose: Hosts all inventory files grouping nodes by function.

#Role-based provisioning logic(ansible/provision)
Purpose: This is your core automation engine. It houses the actual playbooks, roles, tasks, and variables used to provision different types of nodes.

#Input configurations(ansible/input/)
Purpose: Provides dynamic, user-defined or cluster-specific inputs.

#Utility scripts(ansible/utils)
Purpose: Small helper tasks/scripts that assist provisioning.



#Templates for config files
Purpose: Jinja2 templates for config files dynamically rendered with variables.

#Examples for usage
Provides ready-to-use sample configurations to bootstrap new clusters.

#Collection dependencies
Lists required Ansible Galaxy collections (e.g., community.general, ansible.posix, containers.podman) used in your playbooks.
