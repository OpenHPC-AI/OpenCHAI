# OpenCHAI
The OpenCHAI Manager Tool is a unified, modular automation framework designed to simplify and accelerate the deployment, configuration, and management of HPC and AI clusters. It integrates provisioning, orchestration, workload scheduling, and monitoring using industry-standard tools like xCAT, Ansible, SLURM, and Kubernetes.

# OpenCHAI Deployment and Quickstart Guide
The Quickstart is intended for deployment on **dedicated nodes or virtual machines (VMs)** running an **RPM-based Linux distribution** with an **x86_64 architecture**.

A **minimum high-availability (HA) master node configuration** requires **three stateful nodes** — two permanent and one temporary (which can also be made permanent if desired) — along with at least **one stateful compute node** and an **optional stateful GPU node**.

Both master nodes must include a **25 GB `/drbd` partition** to support data replication and synchronization between them.


# OpenCHAI Manager Tool Setup
Install the git package 

```python
yum install git
```

Clone the Repository:
Ensure that you clone the repository into a directory with at least 100 GB of free disk space. This space is required for the offline installation, as the complete software stack RPMs will be downloaded into the same directory. Having sufficient space ensures a smooth installation and configuration experience.

```python
git clone https://github.com/OpenHPC-AI/OpenCHAI.git
```

Run the configuration script to set up the Manager tool after pulling the **rpm-stack** into the OpenCHAI directory.

```bash
$ cd ./OpenCHAI
```


Pull the **rpm-stack** either from your local SSD drive or pen drive to **./OpenCHAI/rpm-stack** on the head node, or download it directly from the online source using:

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




