# OpenCHAI
The OpenCHAI Manager Tool is a unified and modular automation framework designed to simplify and accelerate the deployment, configuration, and management of HPC and AI clusters. It seamlessly integrates provisioning, centralized authentication and authorization, automation, workload scheduling, orchestration, and monitoring by leveraging industry-standard tools such as xCAT, OpenLDAP, Ansible, SLURM, Kubernetes, Nagios, Ganglia, and Chakshu-Front.

# OpenCHAI Deployment and Quickstart Guide
The Quickstart is intended for deployment on **dedicated nodes or virtual machines (VMs)** running an **RPM-based Linux distribution** with an **x86_64 architecture**.

A **minimum high-availability (HA) master node configuration** requires **three stateful nodes** — two permanent and one temporary (which can also be made permanent if desired) — along with at least **one stateful compute node** and an **optional stateful GPU node**.

**Hardware Requirements**

Both master nodes must include a **25 GB `/drbd` partition** to enable data replication and synchronization between them. Additionally, ensure that the **head node** has at least **60 GB of free disk space** in the directory where the **OpenCHAI repository and the `rpm-stack`** will be cloned to support offline installation.


# OpenCHAI Manager Tool Setup

This chapter provides a straightforward, step-by-step guide for installing the Open CDAC HPC-AI Manager Tool (OpenCHAI) on **bare-metal cluster hardware**. It focuses on a quick installation process with minimal explanation of each step. By following these instructions, a moderately experienced cluster administrator can set up and configure a standard cluster environment efficiently—without needing to go through the entire OpenCHAI Administrator Manual or its detailed sections.

The quick installation steps are outlined below:

### **1.1  Installing The Head Node**

Install the git package 

```python
yum install git
```

Clone the Repository:
Make sure to clone the repository into a directory with at least 100 GB of free disk space. This space is essential for offline installation, as the complete software stack RPMs will be downloaded into the same directory. Adequate space ensures a smooth and error-free installation and configuration process.

```python
git clone https://github.com/OpenHPC-AI/OpenCHAI.git
```

Run the configuration script to set up the Manager tool after pulling the **rpm-stack** into the OpenCHAI directory.

```bash
$ cd ./OpenCHAI
```


Pull the **rpm-stack** either from your USB drive (local SSD drive or pen drive) to **./OpenCHAI/rpm-stack** on the head node, or download it directly from the online source using:

```bash
wget https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/v1.0/alma8.9/rpm-stack.tar
```

Make sure the **rpm-stack** is pulled !

```python

#Update the inventory file with all service node details for your cluster, based on your environment configuration.

$ vim chai_setup/inventory_def.txt

#Once the inventory definition file is updated, set up the Chai Manager tool on the head node to deploy and configure the HPC-AI cluster

$ bash ./configure.sh

```




