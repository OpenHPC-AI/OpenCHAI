Quickstart Guide
================

The Quickstart guide is intended for deployment on **dedicated nodes or virtual machines (VMs)**
running an **RPM-based Linux distribution** on **x86_64 architecture**.

A minimum **high-availability (HA) master node configuration** requires:

- **Three stateful nodes** (two permanent and one temporary; the temporary node may also be made permanent)
- **At least one stateless compute node**
- **Optional stateless GPU node**

----

Hardware Requirements
---------------------

Both master nodes must include a **25 GB `/drbd` partition** to support data replication and
synchronization for high availability. In addition, ensure the head node has **at least 60 GB of free disk space**
in the directory where the OpenCHAI repository and RPM stack are cloned.
This space is required for **offline installation**.

Minimum hardware requirements for testing:

- **Head Node**
  - 4 CPU cores
  - 4 GB RAM  
  - *(Recommended: 8 CPU cores and 8 GB RAM)*

- **Master Nodes**
  - 8–12 CPU cores
  - 8 GB RAM (each)

----

OpenCHAI Manager Tool Setup
==========================

This section provides a **step-by-step guide** for installing the **Open CDAC HPC-AI Manager Tool
(OpenCHAI)** on a **bare-metal server**.

The guide focuses on a **quick installation workflow** with minimal explanation. A moderately
experienced cluster administrator can use these steps to deploy and configure a standard
HPC-AI cluster without referring to the full OpenCHAI Administrator Manual.

----

Installing the Head Node
------------------------

Install Git
~~~~~~~~~~~

Install the Git package on the head node:

.. code-block:: bash

   yum install git

Clone the OpenCHAI Repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the repository into a directory with **at least 60 GB of free disk space**.
This space is required to store the **offline software stack RPMs**.

.. code-block:: bash

   git clone https://github.com/OpenHPC-AI/OpenCHAI.git

   # Navigate to the OpenCHAI directory
   cd OpenCHAI

----

Configure the OpenCHAI Manager Tool
-----------------------------------

Ensure OpenCHAI Stack Availability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ensure that the **OpenCHAI stack tar file** is available in the following directory
for an improved setup experience:

::

   OpenCHAI/hpcsuite_registry/hostmachine_reg/

**Offline Mode**

Copy the OpenCHAI software stack for **Alma Linux** or **Rocky Linux**
from a USB drive, local SSD, or other removable media into:

::

   ./hpcsuite_registry/hostmachine_reg/

**Online Mode**

During the OpenCHAI Manager Tool setup, packages can be downloaded
directly from the network if they are not available locally.

Alternatively, refer to the document below for manual downloads:

`HPC-Sangrah Vault <../../documentation/releases/hpcsangrah.md>`_

----

Ansible Inventory Setup
~~~~~~~~~~~~~~~~~~~~~~~

Configure the Ansible inventory on the head node to enable communication
with all service nodes in the HPC-AI cluster, including:

- HPC master nodes
- Management nodes
- AI master nodes
- Login nodes
- BMC nodes

Edit the inventory file according to your environment:

.. code-block:: bash

   vim chai_setup/inventory_def.txt

----

Proceed with CHAI Manager Head Node Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the inventory is configured, initialize the **CHAI Manager Head Node**.
This step prepares the primary control node for managing cluster services
and orchestration workflows.

.. code-block:: bash

   bash ./configure_openchai_manager.sh

If OpenCHAI packages are already available locally, the setup proceeds faster.
Otherwise, the installer provides an option to download them during execution.

----

Post-Setup Verification
-----------------------

Verify inventory configuration:

.. code-block:: bash

   ansible-inventory --list

Verify connectivity with all cluster hosts:

.. code-block:: bash

   ansible all -m ping

   # Verify connectivity using a specific SSH port
   ansible all -m ping -e "ansible_port=22"

If communication issues occur, update the inventory file and reapply:

.. code-block:: bash

   bash ./chai_setup/update_inventory_def.sh

----

Update Cluster Environment Variables
------------------------------------

Update all HPC-AI cluster environment variables:

.. code-block:: bash

   bash ./chai_setup/update_group_var_all.sh

.. note::

   Ensure **public network access** is enabled on all service nodes
   so that missing packages can be installed from public repositories.

----

HPC-AI Head Node Setup
---------------------

Run the head node setup script:

.. code-block:: bash

   bash ./servicenodes/headnode_node_setup.sh

----

HPC Cluster Nodes Deployment and Configuration
----------------------------------------------

To deploy and configure HPC master nodes, execute:

.. code-block:: bash

   bash ./servicenodes/hpc_master_ha_node_setup.sh
