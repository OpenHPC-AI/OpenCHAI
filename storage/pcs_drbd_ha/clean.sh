#!/bin/bash
pcs cluster destroy --force
umount /drbd;drbdadm down rudra_drbd ; wipefs -a /dev/data_vg/drbd; mkfs.ext4 /dev/data_vg/drbd; mount /dev/data_vg/drbd /drbd; lsblk;
