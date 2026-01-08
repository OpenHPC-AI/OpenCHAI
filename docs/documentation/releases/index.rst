Releases
========

The OpenCHAI project maintains release branches for multiple versions.
OpenCHAI versions follow the **x.y.z** versioning scheme, where:

- **x** denotes the major version
- **y** denotes the minor version
- **z** denotes the patch version

----

Release History
---------------

.. toctree::
   :maxdepth: 1
   :caption: Available Releases

   v1.25.0/index


Installing OpenCHAI Packages
============================

Multiple **OpenCHAI software stacks** are available for download, supporting
different **operating system versions** and **OpenCHAI releases**.

Supported operating systems include:

- AlmaLinux 8.9
- Rocky Linux 9.4
- Rocky Linux 9.6

You can browse all available OpenCHAI package options at:

`OpenCHAI Package Vault <https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/>`_

----

Available OpenCHAI Versions
---------------------------

The following OpenCHAI package variants are available for download:

- ``openchai_ha_full_v1.24.0.tgz``
- ``openchai_ha_base_v1.24.0.tgz``
- ``openchai_ha_full_v1.25.0.tgz``
- ``openchai_ha_base_v1.25.0.tgz``

Select the **operating system** and **OpenCHAI version** appropriate for your
deployment environment.

----

Example: Download OpenCHAI Packages
-----------------------------------

The following examples demonstrate downloading OpenCHAI packages for
**AlmaLinux 8.9** and **Rocky Linux 9.6**.
The same procedure can be followed for other supported versions.

----

For AlmaLinux 8.9
-----------------

Create the destination directory:

.. code-block:: bash

   mkdir -p ./hpcsuite_registry/hostmachine_reg/alma8.9

Download and extract the OpenCHAI package:

.. code-block:: bash

   wget -qO- \
   https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/hostmachine_reg/alma8.9/openchai_ha_full_v1.25.0.tgz \
   | tar -xzvf - -C "./hpcsuite_registry/hostmachine_reg/alma8.9"

Verify that the OpenCHAI stack has been extracted correctly:

.. code-block:: bash

   ls -lh ../OpenCHAI/hpcsuite_registry/hostmachine_reg/alma8.9/

----

For Rocky Linux 9.6
------------------

Create the destination directory:

.. code-block:: bash

   mkdir -p ./hpcsuite_registry/hostmachine_reg/rocky9.6

Download and extract the OpenCHAI package:

.. code-block:: bash

   wget -qO- \
   https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/hostmachine_reg/rocky9.6/openchai_ha_full_v1.25.0.tgz \
   | tar -xzvf - -C "./hpcsuite_registry/hostmachine_reg/rocky9.6"

Verify that the OpenCHAI stack has been extracted correctly:

.. code-block:: bash

   ls -lh ../OpenCHAI/hpcsuite_registry/hostmachine_reg/rocky9.6/

----

Notes
-----

- Ensure the OpenCHAI stack is placed under the correct
  ``hpcsuite_registry/hostmachine_reg/`` directory.
- The extracted packages are required for **offline installation**
  during OpenCHAI Manager setup.
- Network access is required only if packages are not available locally.
