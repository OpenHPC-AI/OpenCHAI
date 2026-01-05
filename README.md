# OpenCHAI
The **Open CDAC HPC-AI Manager Tool (OpenCHAI)** is a unified and modular automation framework designed to simplify and accelerate the deployment, configuration, and management of HPC and AI clusters. It seamlessly integrates provisioning, centralized authentication and authorization, automation, workload scheduling, orchestration, and monitoring by leveraging industry-standard tools such as xCAT, OpenLDAP, Ansible, SLURM, Kubernetes, Nagios, Ganglia, and C-Chakshu etc.

# OpenCHAI Flow Diagram for HPC-AI Cluster Provisioning, Deployment & Configuration


![Flow Diagram](images/HPC-AI-Cluster-Architecture.png)


# OpenCHAI Deployment and Quickstart Guide
The Quickstart is intended for deployment on **dedicated nodes or virtual machines (VMs)** running an **RPM-based Linux distribution** with an **x86_64 architecture**.

A **minimum high-availability (HA) master node configuration** requires **three stateful nodes** — two permanent and one temporary (which can also be made permanent if desired) — along with at least **one stateless compute node** and an **optional stateless GPU node**.

**Hardware Requirements**

Both master nodes must include a **25 GB /drbd partition** to support data replication and synchronization between them. Additionally, ensure that the head node has **at least 60 GB of free disk space** in the directory where the OpenCHAI repository and the rpm-stack will be cloned, as these are required for offline installation.

For testing purposes, the minimum hardware requirements are:

**Head Node**: 4 CPU cores and 4 GB RAM (recommended: 8 CPU cores and 8 GB RAM)

**Master Nodes**: Minimum 8 to 12 CPU cores and 8 GB RAM each


# OpenCHAI Manager Tool Setup

This chapter provides a straightforward, step-by-step guide for installing the Open CDAC HPC-AI Manager Tool (OpenCHAI) on **bare-metal server**. It focuses on a quick installation process with minimal explanation of each step. By following these instructions, a moderately experienced cluster administrator can set up and configure a standard cluster environment efficiently—without needing to go through the entire OpenCHAI Administrator Manual or its detailed sections.

The quick installation steps are outlined below:

### **1  Installing The Head Node**

**1.1 Install the git package**

```bash
yum install git
```

**1.2 Clone the Repository:**
Make sure to clone the repository into a directory with at least 60 GB of free disk space. This space is essential for offline installation, as the complete software stack RPMs will be downloaded into the same directory. Adequate space ensures a smooth and error-free installation and configuration process.

```bash
git clone https://github.com/OpenHPC-AI/OpenCHAI.git

# Go to the OpenCHAI directory to configure OpenCHAI.
cd ./OpenCHAI
```

**1.3 Follow the instructions below to configure the OpenCHAI Manager tool.** 

**1.3.0 Ensure that the OpenCHAI tar file is already downloaded and available in the OpenCHAI/hpcsuite_registry/hostmachine_reg directory for better experience.**

**a.) Offline Mode:** Copy the OpenCHAI stack for Alma Linux or Rocky Linux from your USB drive/local SSD/pen drive (which you are carrying) into the directory (./hpcsuite_registry/hostmachine_reg/) on the head node .If the stack is not available locally, follow option b. 

**b.) Online Mode:** During the OpenCHAI Manager Tool setup (Step 1.3.2), you can download the OpenCHAI packages from the network, 

or alternatively download them using the document below.

[HPC-Sangrah Vault](Documents/hpcsangrah.md)


**1.3.1 Ansible Inventory Setup**

Configure the Ansible inventory on the head node to enable communication with all service nodes in the HPC-AI cluster, including:

-HPC Master nodes

-Management nodes

-AI Master nodes

-Login nodes

-BMC nodes

This setup allows the head node to orchestrate tasks, deploy configurations, and manage the cluster using Ansible.
```python

#Update the inventory file with all service node details for your cluster, based on your environment configuration.

vim chai_setup/inventory_def.txt

```

**1.3.2 Proceed to CHAI-Manager Head Node Setup**

After completing all the above configurations, you can now begin the setup of the CHAI-Manager Head Node. This step initializes the primary control node responsible for managing the HPC-AI cluster services, deployments, and orchestration workflows.

```bash
#Once the inventory definition file is updated, set up the Chai Manager tool on the head node to deploy and configure the HPC-AI cluster
#If the OpenCHAI packages are already available at the correct location—either copied from a USB drive or downloaded from the network—the setup will proceed more smoothly. If not, don’t worry; the OpenCHAI setup provides an option to download them during installation.

bash ./configure_openchai_manager.sh
```

**1.3.3 Post-setup verification of communication between all OpenCHAI Manager service nodes in the cluster from the HeadNode**
- **Inventory Setup**
```bash
ansible-inventory --list
```
- **Ping ALL Cluster hosts in inventory**
```bash
ansible all -m ping
# Verify Cluster connection with ssh port, adjust ssh port according to your environment
ansible all -m ping -e "ansible_port=22"

# If you encounter any communication issues between the head node and the service nodes, update the chai_setup/inventory_def.txt file to match your environment.
# After making the changes, run the script below to establish and enable proper communication between the nodes.
bash update_inventory_def.sh
```
