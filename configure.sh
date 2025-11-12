#!/usr/bin/env bash
# -------------------------------------------------------------------
# Script Name : configure_openchai_manager.sh
# Purpose     : Configure OpenCHAI manager tool for cluster setup
# Author      : Satish Gupta (Optimized & Hardened)
# -------------------------------------------------------------------

set -euo pipefail

# -------------------------
# Color output
# -------------------------
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
RESET="\033[0m"

# -------------------------
# Logging
# -------------------------
DEFAULT_LOG="/var/log/openchai_config.log"
LOG="${DEFAULT_LOG}"
if [[ ! -w $(dirname "$LOG") ]]; then
    LOG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/openchai_config.log"
fi
exec 3>>"$LOG" || true
log() { printf '%s %s\n' "$(date --iso-8601=seconds)" "$*" | tee -a /dev/fd/3; }

# -------------------------
# Globals (default)
# -------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BASE_DIR_DEFAULT="$SCRIPT_DIR"
BASE_DIR=""
HOSTMACHINE_REGISTRY_PATH=""
CONTAINER_IMAGE_REGISTRY_PATH=""
OPENCHAI_VAULT_NETWORK_URL="https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/"
NO_CERT_CHECK="no"

# -------------------------
# Utility functions
# -------------------------
error_exit() {
    log "ERROR: $1"
    echo -e "${RED}❌ $1${RESET}" >&2
    exit 1
}

info() { log "INFO: $1"; echo -e "${CYAN}$1${RESET}"; }
notice() { log "NOTICE: $1"; echo -e "${GREEN}$1${RESET}"; }
warn() { log "WARN: $1"; echo -e "${YELLOW}$1${RESET}"; }

safe_input() {
    local prompt="$1"
    local -n __out=$2
    local input=""
    while true; do
        if read -e -rp "$prompt" input 2>/dev/null; then :; else read -r -p "$prompt" input; fi
        input="$(echo -n "$input" | tr -d '\r' | xargs)"
        [[ -n "$input" ]] && { __out="$input"; return 0; }
        warn "Input cannot be empty. Try again or press Ctrl-C to cancel."
    done
}

confirm_yes_no() {
    local prompt="$1"; local -n __out=$2; local input=""
    while true; do
        read -e -rp "$prompt" input || true
        input="$(echo -n "$input" | tr -d '\r' | xargs)"
        case "${input,,}" in
            y|yes) __out="yes"; return 0 ;;
            n|no)  __out="no";  return 0 ;;
            "") warn "Input cannot be empty. Please type yes or no." ;;
            *) warn "Please type yes or no." ;;
        esac
    done
}

# -------------------------
# Start
# -------------------------
info "Starting OpenCHAI Manager Configuration..."
log "Script started by $(whoami) at $(date +%s)"

echo "Have you read and accepted the software License Agreement? (yes/no)"
read -r license_accept
if [[ \"$license_accept\" != \"yes\" ]]; then
    echo \"License Agreement must be accepted to proceed with installation.\"
    exit 1
fi

info "Checking for Ansible installation..."
if ! command -v ansible >/dev/null 2>&1; then
    warn "Ansible not found. Installing..."
    PKG_MGR=$(command -v dnf || command -v yum || true)
    [[ -z "$PKG_MGR" ]] && error_exit "No supported package manager found."
    sudo $PKG_MGR -y install epel-release || true
    sudo $PKG_MGR -y install ansible-core ansible || error_exit "Failed to install Ansible."
    notice "Ansible installed successfully."
else
    notice "Ansible is already installed."
fi

# -------------------------
# Base directory check with disk space validation
# -------------------------

info "Default OpenCHAI base directory detected as: ${BASE_DIR_DEFAULT}"

# Check available space (in GB) using df
AVAILABLE_GB=$(df -BG --output=avail "$BASE_DIR_DEFAULT" 2>/dev/null | tail -1 | tr -dc '0-9')

if [[ -z "$AVAILABLE_GB" ]]; then
    warn "Unable to detect available disk space for ${BASE_DIR_DEFAULT}. Proceeding with manual confirmation."
else
    if (( AVAILABLE_GB >= 50 )); then
        info "✅ ${BASE_DIR_DEFAULT} has sufficient free space (${AVAILABLE_GB} GB available)."
        confirm_yes_no "Use default base directory (${BASE_DIR_DEFAULT})? (yes/no): " use_default
        if [[ "$use_default" == "yes" ]]; then
            BASE_DIR="$BASE_DIR_DEFAULT"
        fi
    else
        warn "⚠️  ${BASE_DIR_DEFAULT} has insufficient space (${AVAILABLE_GB} GB < 50 GB required)."
        echo
        info "Scanning available mount points for directories with ≥50 GB free space..."
        echo "---------------------------------------------------------"
        df -h --output=target,avail | awk 'NR>1 {if ($2+0 >= 50) print "Path: "$1" | Available: "$2" GB"}'
        echo "---------------------------------------------------------"

        safe_input "Enter a suitable directory path (absolute path) for OpenCHAI installation: " BASE_DIR
        BASE_DIR="${BASE_DIR%/}"
        if [[ ! -d "$BASE_DIR" ]]; then
            confirm_yes_no "Directory '$BASE_DIR' not found. Create it? (yes/no): " create_base
            [[ "$create_base" == "yes" ]] && mkdir -p "$BASE_DIR" || error_exit "Cannot proceed without directory."
        fi
    fi
fi

# Fallback if BASE_DIR not set
if [[ -z "$BASE_DIR" ]]; then
    safe_input "Enter the BASE directory of your OpenCHAI deployment (absolute path): " BASE_DIR
    BASE_DIR="${BASE_DIR%/}"
    if [[ ! -d "$BASE_DIR" ]]; then
        confirm_yes_no "Directory '$BASE_DIR' not found. Create it? (yes/no): " create_base
        [[ "$create_base" == "yes" ]] && mkdir -p "$BASE_DIR" || error_exit "Cannot proceed without directory."
    fi
fi

HOSTMACHINE_REGISTRY_PATH="$BASE_DIR/hpcsuite_registry/hostmachine_reg"
CONTAINER_IMAGE_REGISTRY_PATH="$BASE_DIR/hpcsuite_registry/container_img_reg"
mkdir -p "$HOSTMACHINE_REGISTRY_PATH" "$CONTAINER_IMAGE_REGISTRY_PATH" || true

log "Using BASE_DIR=${BASE_DIR}"
info "Using base directory: ${BASE_DIR}"


# -------------------------
# OS Detection
# -------------------------

info "Detecting local operating system..."
if [[ -f /etc/os-release ]]; then
    OS_NAME=$(awk -F= '/^NAME/{print $2}' /etc/os-release | tr -d '"')
    OS_VERSION_ID=$(awk -F= '/^VERSION_ID/{print $2}' /etc/os-release | tr -d '"')
else
    OS_NAME="Unknown"; OS_VERSION_ID="Unknown"
fi

case "$OS_NAME" in
    *AlmaLinux*) DETECTED_OS="alma${OS_VERSION_ID}" ;;
    *Rocky*)     DETECTED_OS="rocky${OS_VERSION_ID}" ;;
    *CentOS*)    DETECTED_OS="centos${OS_VERSION_ID}" ;;
    *Red\ Hat*)  DETECTED_OS="rhel${OS_VERSION_ID}" ;;
    *)           DETECTED_OS="unknown" ;;
esac

info "Detected OS: ${OS_NAME} ${OS_VERSION_ID}"
info "Suggested OS option: ${DETECTED_OS}"
confirm_yes_no "Proceed with detected OS version (${DETECTED_OS})? (yes/no): " os_version
OS_VERSION="${DETECTED_OS}"
notice "Selected OS version: ${DETECTED_OS}"

# -------------------------
# Defining the Network Path for OpenCHAI Registry
# -------------------------

HOSTMACHINE_REG_NETWORK_URL="${OPENCHAI_VAULT_NETWORK_URL}/hostmachine_reg/${OS_VERSION}/"
CONTAINER_IMAGE_REG_NETWORK_URL="${OPENCHAI_VAULT_NETWORK_URL}/container_img_reg/${OS_VERSION}/"

# -------------------------
# Host key / SSL check option
# -------------------------
confirm_yes_no "Do you want to disable SSL/host key checking for downloads? (yes/no): " no_cert
[[ "$no_cert" == "yes" ]] && NO_CERT_CHECK="yes"
CERT_FLAG_WGET=""
CERT_FLAG_CURL=""
if [[ "$NO_CERT_CHECK" == "yes" ]]; then
    CERT_FLAG_WGET="--no-check-certificate"
    CERT_FLAG_CURL="-k"
    warn "⚠️ SSL/host key checking disabled for this session."
fi

# -------------------------
# Tar file handling (local / network)
# -------------------------
info "Checking for OS tar files in: ${HOSTMACHINE_REGISTRY_PATH}"
tar_files=($(find "$HOSTMACHINE_REGISTRY_PATH" -maxdepth 1 -type f \( -iname "*.tar*" -o -iname "*.tgz" \) 2>/dev/null || true))

if (( ${#tar_files[@]} == 0 )); then
    warn "No tar files found in ${HOSTMACHINE_REGISTRY_PATH}."
    echo -e "\nOptions:"
    select ACTION in "Install tar manually" "Download from network" "Skip (handle later)"; do
        case "$REPLY" in
            1) error_exit "Place OS tar manually in ${HOSTMACHINE_REGISTRY_PATH} and rerun."; ;;
            2)
                info "Fetching tar list from ${HOSTMACHINE_REG_NETWORK_URL} ..."
                mapfile -t files < <(curl -fsSL $CERT_FLAG_CURL "$HOSTMACHINE_REG_NETWORK_URL" | grep -oP 'href="([^"]+\.(tar\.gz|tar|tgz))"' | sed 's/href="//;s/"//' || true)
                (( ${#files[@]} == 0 )) && error_exit "No tar files found in network repository."
                select FILE in "${files[@]}"; do
                    [[ -n "$FILE" ]] && break || warn "Invalid choice."
                done
                info "Downloading ${FILE} ..."
                wget -q --show-progress $CERT_FLAG_WGET "${HOSTMACHINE_REG_NETWORK_URL}${FILE}" -O "${HOSTMACHINE_REGISTRY_PATH}/${FILE}"  || error_exit "Download failed."
                tar -xzvf "${HOSTMACHINE_REGISTRY_PATH}/${FILE}" -C "$HOSTMACHINE_REGISTRY_PATH" || tar -xvf "${HOSTMACHINE_REGISTRY_PATH}/${FILE}" -C "$HOSTMACHINE_REGISTRY_PATH"
                notice "Downloaded and extracted ${FILE}"
                break ;;
            3) warn "Skipping tar handling. You must add it manually later."; break ;;
            *) warn "Invalid option. Choose 1-3." ;;
        esac
    done
else
    select local_tar in "${tar_files[@]}"; do
        [[ -n "$local_tar" ]] && { tar -xzf "$local_tar" -C "$BASE_DIR"; notice "Extracted ${local_tar}"; break; }
        warn "Invalid selection."
    done
fi


# =====================================================
# 🧩 Step 4: Container Image Selection or Network Fetch
# =====================================================

CONTAINER_IMAGE_REGISTRY_PATH="$BASE_DIR/hpcsuite_registry/container_img_reg"
PYTHON_SELECTOR="./automation/python/container_img_selector.py"

echo ""
info "Checking local container image registry at: ${CONTAINER_IMAGE_REGISTRY_PATH}"
mkdir -p "$CONTAINER_IMAGE_REGISTRY_PATH" || true

# Scan local registry

mapfile -t app_dirs < <(find "$CONTAINER_IMAGE_REGISTRY_PATH" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)

if (( ${#app_dirs[@]} == 0 )); then
    warn "No application directories found in ${CONTAINER_IMAGE_REGISTRY_PATH}"
    echo ""
    read -rp "Do you want to fetch container images from the network? (yes/no): " netopt
    if [[ "$netopt" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        info "Launching Python container image selector..."
        python3 "$PYTHON_SELECTOR"
    else
        notice "Skipping container image setup. You can add images later under ${CONTAINER_IMAGE_REGISTRY_PATH}."
    fi
    return 0
fi

# Collect local images

declare -A IMG_MAP
index=1
found_local=0

echo ""
info "Scanning local container image directories..."

for app_dir in "${app_dirs[@]}"; do
    app_name=$(basename "$app_dir")
    mapfile -t local_imgs < <(find "$app_dir" -type f \( -iname "*.img" -o -iname "*.tar" -o -iname "*.tar.gz" -o -iname "*.tgz" \) 2>/dev/null)

    if (( ${#local_imgs[@]} == 0 )); then
        warn "No images found in $app_name"
        continue
    fi

    echo ""
    echo "🧩[$app_name] Found ${#local_imgs[@]} image(s):"
    for img in "${local_imgs[@]}"; do
        echo "   [$index] $(basename "$img")"
        IMG_MAP[$index]="$img"
        ((index++))
        found_local=1
    done
done

if (( found_local == 0 )); then
    warn "No local container images found in any registry directories."
    echo ""
    read -rp "Would you like to fetch container images from the network instead? (yes/no): " use_net
    if [[ "$use_net" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        info "Launching Python container image selector..."
        python3 "$PYTHON_SELECTOR"
    else
        notice "Skipped. You can manually place images under ${CONTAINER_IMAGE_REGISTRY_PATH}."
    fi
    return 0
fi

# Select image

echo ""
read -rp "➡️  Enter the number of the container image to use (or press Enter to skip): " choice

if [[ -n "$choice" && -n "${IMG_MAP[$choice]}" ]]; then
    selected_img="${IMG_MAP[$choice]}"
    info "Selected local container image: $selected_img"

    echo ""
    read -rp "Do you want to extract/load this image into the system now? (yes/no): " extract_choice
    if [[ "$extract_choice" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        info "Loading container image..."
        # Attempt gzip extraction first; fallback to tar
        if ! tar -xzf "$selected_img" -C "$BASE_DIR" 2>/dev/null; then
            info "Falling back to uncompressed extraction..."
            tar -xf "$selected_img" -C "$BASE_DIR" || warn "⚠️ Extraction failed for ${selected_img}"
        fi
        notice "Completed loading container image: $(basename "$selected_img")"
    else
        notice "Extraction skipped. Image remains in registry: $selected_img"
    fi

else
    warn "No valid image selection made."
    echo ""
    read -rp "Would you like to load container images from the network instead? (yes/no): " use_net2
    if [[ "$use_net2" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        info "Launching Python container image selector..."
        python3 "$PYTHON_SELECTOR"
    else
        notice "Skipped. You can manually add or load images later under ${CONTAINER_IMAGE_REGISTRY_PATH}."
    fi
fi

# -------------------------
# Step 5: Inventory confirmation & copy
# -------------------------
SYSTEM_ANSIBLE_CFG="/etc/ansible/ansible.cfg"
ANSIBLE_CFG="$BASE_DIR/automation/ansible/ansible.cfg"
ALL_YML="$BASE_DIR/automation/ansible/group_vars/all.yml"
INVENTORY_SCRIPT="$BASE_DIR/automation/ansible/inventory/inventory.sh"
INVENTORY_DEF="$BASE_DIR/chai_setup/inventory_def.txt"
INVENTORY_TARGET="$BASE_DIR/automation/ansible/inventory/inventory_def.txt"

echo ""
info "Inventory file check"
confirm_yes_no "Have you updated the inventory file ($INVENTORY_DEF) according to your environment? (yes/no): " inv_confirm
if [[ "$inv_confirm" == "yes" ]]; then
    if [[ ! -f "$INVENTORY_DEF" ]]; then
        error_exit "Inventory definition file not found: $INVENTORY_DEF"
    fi
    mkdir -p "$(dirname "$INVENTORY_TARGET")" || true
    cp -f "$INVENTORY_DEF" "$INVENTORY_TARGET" || error_exit "Failed to copy $INVENTORY_DEF to $INVENTORY_TARGET"
    notice "Copied: $INVENTORY_DEF → $INVENTORY_TARGET"
else
    error_exit "Please update the inventory file before continuing."
fi

# -------------------------
# Step 6: Update ansible / OpenCHAI paths
# -------------------------
info "Configuring OpenCHAI manager tool paths..."
echo "Detected base directory: ${BASE_DIR}"

# 1) Update local ansible.cfg (automation)
if [[ -f "$ANSIBLE_CFG" ]]; then
    sed -i "s|inventory *= .*inventory.sh|inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh|" "$ANSIBLE_CFG" || warn "Unable to modify $ANSIBLE_CFG"
    notice "Updated: $ANSIBLE_CFG"
else
    warn "File not found: $ANSIBLE_CFG"
fi

# 2) Update group_vars/all.yml base_dir
if [[ -f "$ALL_YML" ]]; then
    sed -i "s|base_dir: .*|base_dir: $BASE_DIR|" "$ALL_YML" || warn "Unable to modify $ALL_YML"
    notice "Updated: $ALL_YML"
else
    warn "File not found: $ALL_YML"
fi

# 3) Update inventory script base_dir
if [[ -f "$INVENTORY_SCRIPT" ]]; then
    sed -i "s|^base_dir=.*|base_dir=\"$BASE_DIR\"|" "$INVENTORY_SCRIPT" || warn "Unable to modify $INVENTORY_SCRIPT"
    chmod +x "$INVENTORY_SCRIPT" || warn "Unable to chmod +x $INVENTORY_SCRIPT"
    notice "Updated: $INVENTORY_SCRIPT"
else
    warn "File not found: $INVENTORY_SCRIPT"
fi

# 4) Update system-wide /etc/ansible/ansible.cfg
if [[ -f "$SYSTEM_ANSIBLE_CFG" ]]; then
    info "Checking system Ansible configuration: $SYSTEM_ANSIBLE_CFG"
    if grep -q "^inventory" "$SYSTEM_ANSIBLE_CFG" 2>/dev/null || true; then
        sed -i "s|^[[:space:]]*inventory[[:space:]]*=.*|inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh|" "$SYSTEM_ANSIBLE_CFG" || warn "Could not update inventory line in $SYSTEM_ANSIBLE_CFG"
    else
        if grep -q "^\[defaults\]" "$SYSTEM_ANSIBLE_CFG" 2>/dev/null || true; then
            sed -i "/^\[defaults\]/a inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh" "$SYSTEM_ANSIBLE_CFG" || warn "Could not append inventory to $SYSTEM_ANSIBLE_CFG"
        else
            {
                echo "[defaults]"
                echo "inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh"
            } >> "$SYSTEM_ANSIBLE_CFG" || warn "Could not create [defaults] in $SYSTEM_ANSIBLE_CFG"
        fi
    fi
    # ensure host_key_checking disabled for usability
    grep -qxF 'host_key_checking = False' "$SYSTEM_ANSIBLE_CFG" || echo 'host_key_checking = False' >> "$SYSTEM_ANSIBLE_CFG" || warn "Could not add host_key_checking"
    chmod +x "$BASE_DIR/automation/ansible/inventory/inventory.sh" || true
    cp -ar "$BASE_DIR/automation/ansible/group_vars" /etc/ansible/ 2>/dev/null || warn "Could not copy group_vars to /etc/ansible/"
    notice "System-wide Ansible configuration updated: $SYSTEM_ANSIBLE_CFG"
else
    warn "System-wide Ansible config not found at: $SYSTEM_ANSIBLE_CFG (skipping)"
fi

notice "OpenCHAI manager tool configuration paths updated successfully!"

# -------------------------
# Done
# -------------------------
info "Configuration completed successfully."
notice "Log file: ${LOG}"
log "Script finished successfully."

exit 0


# -------------------------
# Ansible tweaks
# -------------------------
SYSTEM_ANSIBLE_CFG="/etc/ansible/ansible.cfg"
mkdir -p "$(dirname "$SYSTEM_ANSIBLE_CFG")"
grep -qxF 'host_key_checking = False' "$SYSTEM_ANSIBLE_CFG" 2>/dev/null || echo 'host_key_checking = False' >> "$SYSTEM_ANSIBLE_CFG"

notice "Configuration complete."
log "Script finished successfully."
exit 0



