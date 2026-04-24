# ================================
# Ansible Node Details File
# ================================
# This file contains connection details for all nodes that Ansible will manage.
# Each line represents one node in your cluster (for example, headnode, master, login nodes, etc.)

# -------------------------------------------------------------------------
# COLUMN MEANINGS (Fill carefully)
# -------------------------------------------------------------------------
# ansible_hostname   →  The name Ansible uses to identify this node.
# ip                 →  The node's IP address (used to connect to it over SSH).
# ansible_user       →  The Linux user account on the target system that Ansible uses to log in (for example, root).
# ansible_password   →  The password for the user mentioned above.
# group              →  Logical group name (like headnode, hpc_master, login).
# hostname           →  The actual hostname configured on the node (output of `hostname` command).
# port               →  Mention ssh port as your system configure for ssh
# NOTE:
# - Each column should be separated by spaces or tabs.
# - You can add as many nodes as you want — one per line.
# -------------------------------------------------------------------------

# Example entries:
#You may modify the entries in the table below to match your environment.
#Remove   any rows that are not required—the table shown is only an example.
#Important: Every column must have a value for each host.
# - ansible_hostname is managed by the Ansible inventory.
# - ip, ansible_user, ansible_password, hostname, and ssh_port must match the values configured on the actual system.
# - Ensure that SSH access is working using the provided user, password, and port before running Ansible.

#ansible_hostname         ip             ansible_user  ansible_password      group          hostname   ssh_port
headnode                 172.10.3.201    root          redhat                headnode       headnode        22
