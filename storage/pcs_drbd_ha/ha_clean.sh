#!/bin/bash

# Configuration
DRBD_RESOURCE="rudra_drbd"
DRBD_DEVICE="/dev/data_vg/drbd"
MOUNT_POINT="/drbd"

# Colors for logging
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
error_exit() { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }

echo "--- Starting Production Cluster & DRBD Cleanup ---"

# 1. Destroy PCS Cluster
log "Destroying PCS cluster..."
pcs cluster destroy --force || error_exit "Failed to destroy PCS cluster."

# 2. Unmount Filesystem
if mountpoint -q "$MOUNT_POINT"; then
    log "Unmounting $MOUNT_POINT..."
    umount -l "$MOUNT_POINT" || error_exit "Failed to unmount $MOUNT_POINT. Is it busy?"
else
    log "$MOUNT_POINT is not mounted. Skipping."
fi

# 3. Bring Down DRBD
log "Tearing down DRBD resource: $DRBD_RESOURCE..."
drbdadm down "$DRBD_RESOURCE" && log "DRBD resource $DRBD_RESOURCE is down." || log "DRBD already down or failed to stop."

# 4. Wipe Signatures (Safety Check)
log "Wiping signatures on $DRBD_DEVICE..."
wipefs -a "$DRBD_DEVICE" || error_exit "Failed to wipe signatures on $DRBD_DEVICE."

# 5. Re-create Filesystem
log "Formatting $DRBD_DEVICE with ext4..."
mkfs.ext4 -F "$DRBD_DEVICE" || error_exit "Failed to format $DRBD_DEVICE."

# 6. Remount and Verify
log "Remounting $MOUNT_POINT..."
mount "$DRBD_DEVICE" "$MOUNT_POINT" || error_exit "Failed to remount $MOUNT_POINT."

log "Cleanup complete. Current block device status:"
lsblk "$DRBD_DEVICE"

echo "--- Finished ---"
