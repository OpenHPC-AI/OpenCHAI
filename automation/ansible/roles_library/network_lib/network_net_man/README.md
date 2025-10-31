Purpose:
Manages the NetworkManager service and ensures the package is installed (if desired).

Variables:
Variable        Default Description
nm_package_name NetworkManager  Package name for installation
nm_service_name NetworkManager  Service name
nm_service_state        started Desired state (started, stopped, restarted)
nm_service_enabled      true    Whether to enable on boot
nm_install_if_missing   true    Install package if missing
