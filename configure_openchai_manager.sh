#!/usr/bin/env bash
# -------------------------------------------------------------------
# Script Name : configure_openchai_manager.sh
# Purpose     : Configure OpenCHAI manager tool for cluster setup
# Author      : Satish Gupta
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
OPENCHAI_VERSION=""

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
        read -e -rp "$prompt" input || true
        input="${input//[$'\r\n']/}"
        input="$(echo "$input" | xargs)"

        if [[ -n "$input" ]]; then
            __out="$input"
            return 0
        else
            echo -e "${YELLOW}⚠️  Input cannot be empty. Try again or press Ctrl+C to exit.${RESET}"
        fi
    done
}

confirm_yes_no() {
    local prompt="$1"; local -n __out=$2
    local input=""
    while true; do
        read -e -rp "$prompt" input || true
        input="$(echo "${input,,}" | xargs)"

        case "$input" in
            y|yes)
                __out="yes"; return 0 ;;
            n|no)
                __out="no"; return 0 ;;
            "")
                echo -e "${YELLOW}⚠️  Please type yes or no.${RESET}" ;;
            *)
                echo -e "${YELLOW}⚠️  Invalid input. Type yes or no and press Enter.${RESET}" ;;
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
if [[ "${license_accept,,}" != "yes" ]]; then
    echo "License Agreement must be accepted to proceed with installation."
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

AVAILABLE_GB=$(df -BG --output=avail "$BASE_DIR_DEFAULT" 2>/dev/null | tail -1 | tr -dc '0-9' || true)

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
        if df -h --output=target,avail 2>/dev/null | awk 'NR>1 {gsub(/G/,"",$2); if ($2+0 >= 50) print "Path: "$1" | Available: "$2" " " GB"}'; then
            :
        fi
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

# Ensure base subdirs exist
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
DEF_OS_VERSION="${DETECTED_OS}"
notice "Default Selected OS version from Headnode: ${DETECTED_OS}"
echo
notice "You can adjust the OS version for the HPC-AI Master Nodes in the upcoming steps if it differs from the Headnode!"


# -------------------------------------------------------
# Auto-detect server values
# -------------------------------------------------------
DEF_OS_ARCH=$(uname -m)

if [[ ! -f /etc/os-release ]]; then
    echo -e "${RED}ERROR: /etc/os-release missing. Cannot detect OS version.${RESET}"
    exit 1
fi

OS_VERSION_ID_NUM=$(grep "^VERSION_ID" /etc/os-release | cut -d= -f2 | tr -d '"' | cut -d. -f1 || true)
DEF_RHEL_LABEL="rh${OS_VERSION_ID_NUM}"
DEF_EL_LABEL="el${OS_VERSION_ID_NUM}"
DEF_KERNEL=$(uname -r)
# -------------------------------------------------------
# Ask user for overrides
# -------------------------------------------------------
echo
echo "Press ENTER to accept default values."
echo

read -rp "Specify OS Architecture          [default: $DEF_OS_ARCH]: " USER_OS_ARCH
OS_ARCH="${USER_OS_ARCH:-$DEF_OS_ARCH}"

read -rp "Specify OS Version               [default: $DEF_OS_VERSION]: " USER_OS_VERSION
OS_VERSION="${USER_OS_VERSION:-$DEF_OS_VERSION}"

read -rp "Specify RHEL Label               [default: $DEF_RHEL_LABEL]: " USER_RHEL_LABEL
RHEL_LABEL="${USER_RHEL_LABEL:-$DEF_RHEL_LABEL}"

read -rp "Enterprise EL Label              [default: $DEF_EL_LABEL]: " USER_EL_LABEL
EL_LABEL="${USER_EL_LABEL:-$DEF_EL_LABEL}"

read -rp "Kernel Version                   [default: $DEF_KERNEL]: " USER_KERNEL
tmp="${USER_KERNEL:-$DEF_KERNEL}"; KERNEL_VERSION="${tmp%.*}"
echo
echo
# -------------------------
# Defining the Network Path for OpenCHAI Registry
# -------------------------
HOSTMACHINE_REG_NETWORK_URL="${OPENCHAI_VAULT_NETWORK_URL}/hostmachine_reg/${OS_VERSION}/"
CONTAINER_IMAGE_REG_NETWORK_URL="${OPENCHAI_VAULT_NETWORK_URL}/container_img_reg/${OS_VERSION}/"
mkdir -p "$HOSTMACHINE_REGISTRY_PATH/$OS_VERSION" || true
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
# -------------------------
# Tar file handling (local / network / manual / skip)
# -------------------------

info "Checking for OS tar files in: ${HOSTMACHINE_REGISTRY_PATH}"

# Helper: strip tar extensions safely
strip_tar_ext() {
    local f
    f=$(basename "$1")
    f="${f%.tar.gz}"
    f="${f%.tgz}"
    f="${f%.tar.xz}"
    f="${f%.tar}"
    echo "$f"
}

# Find all tar-like files
mapfile -t tar_files < <(
    find "$HOSTMACHINE_REGISTRY_PATH" -maxdepth 1 -type f \
        \( -iname "*.tar.gz" -o -iname "*.tgz" -o -iname "*.tar.xz" -o -iname "*.tar" \) \
        2>/dev/null || true
)

# Default value (always set)
OPENCHAI_VERSION="__SET_LATER__"

# ------------------------------------------------------------------
# Case 1: No local tar files found → Stream extract from network
# ------------------------------------------------------------------
if (( ${#tar_files[@]} == 0 )); then
    warn "No registry tar files found in ${HOSTMACHINE_REGISTRY_PATH}."

    echo
    echo "Options:"
    select ACTION in "Install tar manually" "Download from network" "Skip (handle later)"; do
        case "$REPLY" in
            1)
                warn "Manual installation selected."
                warn "Place the registry tar later in:"
                echo "  → ${HOSTMACHINE_REGISTRY_PATH}"
                OPENCHAI_VERSION="__SET_MANUALLY__"
                break
                ;;

            2)
                info "Fetching tar list from ${HOSTMACHINE_REG_NETWORK_URL} ..."

                mapfile -t files < <(
                    curl -fsSL ${CERT_FLAG_CURL} "$HOSTMACHINE_REG_NETWORK_URL" |
                    grep -oP 'href="([^"]+\.(tar\.gz|tgz|tar\.xz|tar))"' |
                    sed 's/href="//;s/"//' || true
                )

                if (( ${#files[@]} == 0 )); then
                    warn "No registry tar files found on network."
                    OPENCHAI_VERSION="__SET_LATER__"
                    break
                fi

                echo
                echo "Available registry tarballs:"
                select FILE in "${files[@]}"; do
                    [[ -n "$FILE" ]] && break
                done

                OPENCHAI_VERSION=$(strip_tar_ext "$FILE")
                DEST_DIR="${HOSTMACHINE_REGISTRY_PATH}/${OS_VERSION}"
                TAR_URL="${HOSTMACHINE_REG_NETWORK_URL}${FILE}"

                mkdir -p "$DEST_DIR"

                # Skip if already extracted
                if [[ -d "${DEST_DIR}/${OPENCHAI_VERSION}" ]]; then
                    notice "✔ Registry already present: ${OPENCHAI_VERSION}"
                    break
                fi

                # Detect compression
                case "$FILE" in
                    *.tar.gz|*.tgz) TAR_OPTS="-xzvf -" ;;
                    *.tar.xz)       TAR_OPTS="-xJvf -" ;;
                    *.tar)          TAR_OPTS="-xvf -" ;;
                    *)
                        warn "Unsupported archive format: $FILE"
                        OPENCHAI_VERSION="__SET_LATER__"
                        break
                        ;;
                esac

                info "Extracting ${FILE} directly into ${DEST_DIR}"

                if command -v wget >/dev/null 2>&1; then
                    wget -q -O - $CERT_FLAG_WGET "$TAR_URL" | \
                    tar $TAR_OPTS -C "$DEST_DIR" || {
                        warn "Extraction failed"
                        OPENCHAI_VERSION="__SET_LATER__"
                        break
                    }
                else
                    curl -fsSL ${CERT_FLAG_CURL} "$TAR_URL" | \
                    tar $TAR_OPTS -C "$DEST_DIR" || {
                        warn "Extraction failed"
                        OPENCHAI_VERSION="__SET_LATER__"
                        break
                    }
                fi

                notice "✅ Registry extracted successfully"
                info "Untar directory name: ${OPENCHAI_VERSION}"
                break
                ;;

            3)
                warn "Skipping registry handling. Will configure later."
                OPENCHAI_VERSION="__SET_LATER__"
                break
                ;;
        esac
    done

# ------------------------------------------------------------------
# Case 2: Local tar files exist → Stream extract from file (no copy)
# ------------------------------------------------------------------
else
    echo
    echo "===================================================================="
    echo " 🧠 HPC-AI Cluster Setup: Select a Registry Tarball"
    echo "===================================================================="
    echo

    select local_tar in "${tar_files[@]}" "Skip extraction"; do
        [[ -z "$local_tar" ]] && continue

        if [[ "$local_tar" == "Skip extraction" ]]; then
            warn "Skipping extraction as requested."
            OPENCHAI_VERSION="__SET_LATER__"
            break
        fi

        FILE="$(basename "$local_tar")"
        OPENCHAI_VERSION=$(strip_tar_ext "$FILE")
        DEST_DIR="${HOSTMACHINE_REGISTRY_PATH}/${OS_VERSION}"

        mkdir -p "$DEST_DIR"

        # Skip if already extracted
        if [[ -d "${DEST_DIR}/${OPENCHAI_VERSION}" ]]; then
            notice "✔ Registry already present: ${OPENCHAI_VERSION}"
            break
        fi

        # Detect compression
        case "$FILE" in
            *.tar.gz|*.tgz) TAR_OPTS="-xzvf" ;;
            *.tar.xz)       TAR_OPTS="-xJvf" ;;
            *.tar)          TAR_OPTS="-xvf" ;;
            *)
                warn "Unsupported archive format: $FILE"
                OPENCHAI_VERSION="__SET_LATER__"
                break
                ;;
        esac

        info "Extracting ${FILE} directly into ${DEST_DIR}"

        tar $TAR_OPTS "$local_tar" -C "$DEST_DIR" || {
            warn "Extraction failed"
            OPENCHAI_VERSION="__SET_LATER__"
            break
        }

        notice "✅ Registry extracted successfully"
        info "Untar directory name: ${OPENCHAI_VERSION}"
        break
    done
fi

# ------------------------------------------------------------------
# Final validation (non-fatal)
# ------------------------------------------------------------------
echo
echo "Checking local registry for OpenCHAI version..."
echo "Path: ${HOSTMACHINE_REGISTRY_PATH}/$OS_VERSION"
echo "Version: ${OPENCHAI_VERSION}"

if [[ -d "${HOSTMACHINE_REGISTRY_PATH}/${OS_VERSION}/${OPENCHAI_VERSION}" ]]; then
    echo -e "${GREEN}✔ Version '${OPENCHAI_VERSION}' exists.${RESET}"
else
    echo -e "${YELLOW}⚠ Version directory not found."
    echo "  Update 'openchai_version' later in group_vars/all.yml.${RESET}"
fi


# -------------------------
# Inventory confirmation & copy
# -------------------------
SYSTEM_ANSIBLE_CFG="/etc/ansible/ansible.cfg"
ANSIBLE_CFG="$BASE_DIR/automation/ansible/ansible.cfg"
ALL_YML="$BASE_DIR/automation/ansible/group_vars/all.yml"
INVENTORY_SCRIPT="$BASE_DIR/automation/ansible/inventory/inventory.sh"
INVENTORY_DEF="$BASE_DIR/chai_setup/inventory_def.txt"
INVENTORY_TARGET="$BASE_DIR/automation/ansible/inventory/inventory_def.txt"
INVENTORY_LINE="inventory = $BASE_DIR/automation/ansible/inventory/inventory.sh"

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

# -------------------------------------------------------
# Print final values
# -------------------------------------------------------
echo
echo -e "${CYAN}-----------------------------------------------------"
echo "         Final Selected Base Variables"
echo "-----------------------------------------------------"
echo "OS Architecture        = $OS_ARCH"
echo "OS Version             = $OS_VERSION"
echo "RHEL Label             = $RHEL_LABEL"
echo "Enterprise EL Label    = $EL_LABEL"
echo "Kernel Version         = $KERNEL_VERSION"
echo "Base Directory         = $BASE_DIR"
echo "OpenCHAI Version       = $OPENCHAI_VERSION"
echo "-----------------------------------------------------${RESET}"
echo

# -------------------------------------------------------
# Update all.yml with selected values (only if file exists)
# -------------------------------------------------------
if [[ -f "$ALL_YML" ]]; then
    sed -i "s|^openchai_version:.*|openchai_version: $OPENCHAI_VERSION|" "$ALL_YML" || warn "Failed to update openchai_version"
    sed -i "s|^base_dir:.*|base_dir: $BASE_DIR|" "$ALL_YML" || warn "Failed to update base_dir"
    sed -i "s|^os_version:.*|os_version: $OS_VERSION|" "$ALL_YML" || warn "Failed to update os_version"
    sed -i "s|^os_arch:.*|os_arch: $OS_ARCH|" "$ALL_YML" || warn "Failed to update os_arch"
    sed -i "s|^rhel_linux_label:.*|rhel_linux_label: $RHEL_LABEL|" "$ALL_YML" || warn "Failed to update rhel_linux_label"
    sed -i "s|^enterprise_linux_label:.*|enterprise_linux_label: $EL_LABEL|" "$ALL_YML" || warn "Failed to update enterprise_linux_label"
    sed -i "s|^default_kernel_version:.*|default_kernel_version: \"$KERNEL_VERSION\"|" "$ALL_YML" || warn "Failed to update default_kernel_version"

    echo -e "${GREEN}✔ Base Variables Updated Successfully in all.yml${RESET}"
else
    warn "Group vars file not found at: $ALL_YML (skipping all.yml updates)"
fi


# ---------------------------
# Update the base_dir path value in chai_setup/modules
#----------------------------
SCRIPT_FILES=(
    "$BASE_DIR/chai_setup/update_group_var_all.sh"
    "$BASE_DIR/chai_setup/modules/"*.sh
    "$BASE_DIR/chai_setup/update_inventory_def.sh"
)

for file in "${SCRIPT_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "Updating: $file"

        # Replace ANY form of base_dir= with correct format
        sed -Ei \
            "s|^base_dir[ ]*=[ ]*.*|base_dir=\"${BASE_DIR}\"|" \
            "$file"
    fi
done

# -------------------------
# Update ansible / OpenCHAI paths
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

# 2) Update group_vars/all.yml base_dir (already handled above; keep additional safety)
if [[ -f "$ALL_YML" ]]; then
    sed -i "s|^base_dir: .*|base_dir: $BASE_DIR|" "$ALL_YML" || warn "Unable to modify $ALL_YML"
    sed -i "s|^os_version: .*|os_version: $OS_VERSION|" "$ALL_YML" || warn "Unable to modify $ALL_YML"
    sed -i "s|^openchai_version: .*|openchai_version: $OPENCHAI_VERSION|" "$ALL_YML" || warn "Unable to modify $ALL_YML"
    notice "Updated: $ALL_YML"
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

    if grep -q "^[[:space:]]*inventory[[:space:]]*=" "$SYSTEM_ANSIBLE_CFG"; then
        sed -i "s|^[[:space:]]*inventory[[:space:]]*=.*|$INVENTORY_LINE|" "$SYSTEM_ANSIBLE_CFG" \
            || warn "Could not update inventory line in $SYSTEM_ANSIBLE_CFG"
    else
        if grep -q "^\[defaults\]" "$SYSTEM_ANSIBLE_CFG"; then
            sed -i "/^\[defaults\]/a $INVENTORY_LINE" "$SYSTEM_ANSIBLE_CFG" \
                || warn "Could not append inventory to $SYSTEM_ANSIBLE_CFG"
        else
            {
                echo "[defaults]"
                echo "$INVENTORY_LINE"
            } >> "$SYSTEM_ANSIBLE_CFG" || warn "Could not create [defaults] in $SYSTEM_ANSIBLE_CFG"
        fi
    fi
    grep -qxF 'host_key_checking = False' "$SYSTEM_ANSIBLE_CFG" 2>/dev/null || echo 'host_key_checking = False' >> "$SYSTEM_ANSIBLE_CFG" || warn "Could not add host_key_checking"
    chmod +x "$BASE_DIR/automation/ansible/inventory/inventory.sh" 2>/dev/null || true
    cp -ar "$BASE_DIR/automation/ansible/group_vars" /etc/ansible/ 2>/dev/null || warn "Could not copy group_vars to /etc/ansible/"
    notice "System-wide Ansible configuration updated: $SYSTEM_ANSIBLE_CFG"
else
    warn "System-wide Ansible config not found at: $SYSTEM_ANSIBLE_CFG (skipping)"
fi

notice "OpenCHAI manager tool configuration paths updated successfully!"

# =====================================================
# Container Image Selection or Network Fetch (Non-breaking & Hardened)
# =====================================================
CONTAINER_IMAGE_REGISTRY_PATH="$BASE_DIR/hpcsuite_registry/container_img_reg"
PYTHON_SELECTOR="$BASE_DIR/automation/python/container_img_selector.py"
CONTAINER_REGISTRY_URL="${CONTAINER_IMAGE_REG_NETWORK_URL}"

# Ensure Python selector path if present
if [[ -f "$PYTHON_SELECTOR" ]]; then
    sed -i "s|^LOCAL_DIR *=.*|LOCAL_DIR = \"${CONTAINER_IMAGE_REGISTRY_PATH}\"|" "$PYTHON_SELECTOR" || warn "Cannot update python selector path"
fi

echo ""
info "Checking local container image registry at: ${CONTAINER_IMAGE_REGISTRY_PATH}"
mkdir -p "$CONTAINER_IMAGE_REGISTRY_PATH" || error_exit "Unable to create container image registry path."

# ---------------------------------------------------------
# Scan for existing container image directories
# ---------------------------------------------------------
mapfile -t app_dirs < <(find "$CONTAINER_IMAGE_REGISTRY_PATH" -mindepth 1 -maxdepth 1 -type d 2>/dev/null || true)

if (( ${#app_dirs[@]} == 0 )); then
    warn "No application directories found in ${CONTAINER_IMAGE_REGISTRY_PATH}"
    echo ""
    confirm_yes_no "Do you want to fetch container images from the network? (yes/no): " netopt
    if [[ "$netopt" == "yes" ]]; then
        info "Launching Python container image selector..."
        if command -v python3 >/dev/null 2>&1; then
            python3 "$PYTHON_SELECTOR" || warn "Python image selector failed or aborted by user."
        else
            warn "python3 not available; cannot run image selector."
        fi
    else
        notice "Skipping container image setup. You can add images later under ${CONTAINER_IMAGE_REGISTRY_PATH}."
    fi
else
    info "Found ${#app_dirs[@]} application directory(ies):"
    for dir in "${app_dirs[@]}"; do
        echo " - $(basename "$dir")"
    done
fi

echo ""
info "Proceeding to verify and collect container images..."
echo ""

# ---------------------------------------------------------
# Collect all local container images
# ---------------------------------------------------------
declare -A IMG_MAP
declare -A LOCAL_IMG_NAMES
index=1
found_local=0

for app_dir in "${app_dirs[@]}"; do
    app_name=$(basename "$app_dir")
    mapfile -t local_imgs < <(find "$app_dir" -type f \( -iname "*.img" -o -iname "*.tar" -o -iname "*.tar.gz" -o -iname "*.tgz" \) 2>/dev/null || true)

    if (( ${#local_imgs[@]} == 0 )); then
        warn "No images found in $app_name"
        continue
    fi

    echo ""
    echo "🧩 [$app_name] Found ${#local_imgs[@]} image(s):"
    for img in "${local_imgs[@]}"; do
        base_img=$(basename "$img")
        echo "   [$index] $base_img"
        IMG_MAP[$index]="$img"
        LOCAL_IMG_NAMES["$base_img"]=1
        ((index++))
        found_local=1
    done
done

# ---------------------------------------------------------
# Handle missing or absent local images
# ---------------------------------------------------------
if (( found_local == 0 )); then
    warn "No local container images found in any registry directories."
    echo ""
    confirm_yes_no "Would you like to fetch container images from the network instead? (yes/no): " use_net
    if [[ "$use_net" == "yes" ]]; then
        info "Launching Python container image selector..."
        if command -v python3 >/dev/null 2>&1; then
            python3 "$PYTHON_SELECTOR" || warn "Python selector aborted or failed."
        else
            warn "python3 not available; cannot run selector."
        fi
    else
        notice "No images configured. Continuing setup without container image fetch."
    fi
fi

confirm_yes_no "Do you want to fetch missing images from the network? (yes/no): " fetch_net
if [[ "$fetch_net" == "yes" ]]; then
    info "Fetching container image list from ${CONTAINER_REGISTRY_URL} ..."
    if ! command -v curl >/dev/null 2>&1; then
        warn "curl not available; cannot fetch network images via curl. Attempting Python selector."
        if command -v python3 >/dev/null 2>&1; then
            python3 "$PYTHON_SELECTOR" || warn "Python fallback aborted or failed."
        else
            warn "Neither curl nor python3 available to fetch images."
        fi
    else
        mapfile -t net_imgs < <(
            curl -fsSL $CERT_FLAG_CURL "$CONTAINER_REGISTRY_URL" \
            | grep -Eo 'href="[^"]+\.(tar\.gz|tar|tgz|img)"' \
            | sed -E 's/href="([^"]+)"/\1/' \
            || true
        )

        if (( ${#net_imgs[@]} == 0 )); then
            warn "No images found using curl parser. Falling back to Python selector..."
            if command -v python3 >/dev/null 2>&1; then
                python3 "$PYTHON_SELECTOR" || warn "Python fallback aborted or failed."
            else
                warn "python3 not available for fallback."
            fi
        else
            total=${#net_imgs[@]}
            info "Found $total image(s) in network repository."
            for net_img in "${net_imgs[@]}"; do
                base_net_img=$(basename "$net_img")
                if [[ -n "${LOCAL_IMG_NAMES[$base_net_img]:-}" ]]; then
                    notice "⏭️  Skipping $base_net_img (already present locally)"
                    continue
                fi
                info "⬇️  Downloading $base_net_img ..."
                if command -v wget >/dev/null 2>&1; then
                    wget -q --show-progress $CERT_FLAG_WGET \
                        "${CONTAINER_REGISTRY_URL}${net_img}" \
                        -O "${CONTAINER_IMAGE_REGISTRY_PATH}/${base_net_img}" \
                        || warn "⚠️  Failed to download $base_net_img"
                else
                    curl -fsSL ${CERT_FLAG_CURL} -o "${CONTAINER_IMAGE_REGISTRY_PATH}/${base_net_img}" "${CONTAINER_REGISTRY_URL}${net_img}" \
                        || warn "⚠️  Failed to download $base_net_img"
                fi
            done
            notice "✅ Network image synchronization complete."
        fi
    fi
else
    notice "⏭️  Network image fetch skipped by user."
fi

echo ""
info "Proceeding to next setup phase..."
echo ""

# -------------------------
# Done
# -------------------------
info "Configuration completed successfully."
notice "Log file: ${LOG}"
log "Script finished successfully."

exit 0
