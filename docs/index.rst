OpenCHAI Cluster Manager
=======================

OpenCHAI Cluster Manager is an open-source platform designed to simplify the deployment, configuration, and lifecycle management of High-Performance Computing (HPC) and Artificial Intelligence (AI) clusters. It addresses the operational complexity inherent in modern HPC-AI environments by providing a unified, automated, and repeatable approach to cluster bring-up and management.

HPC and AI software ecosystems consist of tightly coupled components, diverse runtime dependencies, and environment-specific configurations. OpenCHAI reduces the engineering overhead associated with these challenges by standardizing workflows, automating infrastructure operations, and enabling consistent deployments across development, validation, and production environments.

The OpenCHAI platform is built using industry-proven automation technologies, with Ansible serving as the primary orchestration engine, complemented by Python and Bash utilities. Cluster deployment and configuration are centrally managed from a designated control node running a Linux operating system.

Using declarative playbooks, OpenCHAI provisions and configures a wide range of node roles, including:

-HPC Master nodes

-Management nodes

-AI Master nodes

-Login nodes

-BMC nodes

Platform Capabilities
---------------------

OpenCHAI integrates multiple infrastructure and operations components into a cohesive management framework, including:

- Bare-metal provisioning and node lifecycle management  
- Centralized authentication and authorization services  
- Automated configuration management  
- Workload scheduling and orchestration  
- Monitoring, observability, and operational visibility  

The platform leverages established open-source technologies such as xCAT, OpenLDAP, Ansible, SLURM, Kubernetes, Nagios, Ganglia, and Chakshu-Front to deliver a scalable and extensible solution for enterprise and research environments.

Open Source and Community
-------------------------

OpenCHAI is developed and maintained as an open-source project. The source code, issue tracking, and contribution workflows are hosted on `GitHub <https://github.com/OpenHPC-AI/OpenCHAI>`_.. Users and contributors are encouraged to participate by reviewing the codebase, reporting issues, submitting enhancements, and engaging with the community.

Table of Contents

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   Overview/index
   Releases/index
   Architecture/index
   Upgrade/index

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   Learning Environment/index
   Operational Environment/index
   Operational Best Practices/index

.. toctree::
   :maxdepth: 2
   :caption: Tasks

   Quick Start Guide/index

.. toctree::
   :maxdepth: 2
   :caption: Concepts

   xCAT
   OpenLDAP
   Slurm
   

   
