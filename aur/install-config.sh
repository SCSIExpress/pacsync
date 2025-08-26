#!/bin/bash
# Configuration installation script for Pacman Sync Utility AUR package
# This script handles proper installation and setup of configuration files

set -e

# Configuration paths
CONFIG_DIR="/etc/pacman-sync-utility"
DATA_DIR="/var/lib/pacman-sync-utility"
LOG_DIR="/var/lib/pacman-sync-utility/logs"

# Source files (from package build directory)
SOURCE_DIR="${1:-/usr/share/pacman-sync-utility/config}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to install configuration file with backup
install_config_file() {
    local source_file="$1"
    local dest_file="$2"
    local file_mode="${3:-644}"
    
    if [[ ! -f "$source_file" ]]; then
        log_error "Source configuration file not found: $source_file"
        return 1
    fi
    
    # Create destination directory if it doesn't exist
    mkdir -p "$(dirname "$dest_file")"
    
    # If destination exists, create backup
    if [[ -f "$dest_file" ]]; then
        log_warn "Configuration file exists: $dest_file"
        log_info "Creating backup: $dest_file.pacnew"
        cp "$source_file" "$dest_file.pacnew"
        chmod "$file_mode" "$dest_file.pacnew"
    else
        log_info "Installing configuration file: $dest_file"
        cp "$source_file" "$dest_file"
        chmod "$file_mode" "$dest_file"
    fi
}

# Function to create directory with proper permissions
create_directory() {
    local dir_path="$1"
    local dir_mode="${2:-755}"
    local owner="${3:-root}"
    local group="${4:-root}"
    
    if [[ ! -d "$dir_path" ]]; then
        log_info "Creating directory: $dir_path"
        mkdir -p "$dir_path"
    fi
    
    chmod "$dir_mode" "$dir_path"
    chown "$owner:$group" "$dir_path"
}

# Function to generate JWT secret key
generate_jwt_secret() {
    local config_file="$CONFIG_DIR/server.conf"
    
    if [[ -f "$config_file" ]]; then
        # Check if JWT secret needs to be generated
        if grep -q "CHANGE_THIS_SECRET_KEY_ON_INSTALL" "$config_file"; then
            log_info "Generating JWT secret key..."
            
            # Generate a secure random key
            local jwt_secret
            jwt_secret=$(openssl rand -hex 32)
            
            # Replace the placeholder with the generated secret
            sed -i "s/CHANGE_THIS_SECRET_KEY_ON_INSTALL/$jwt_secret/g" "$config_file"
            
            log_info "JWT secret key generated and installed"
        else
            log_info "JWT secret key already configured"
        fi
    else
        log_error "Server configuration file not found: $config_file"
        return 1
    fi
}

# Function to set up file permissions
setup_permissions() {
    log_info "Setting up file permissions..."
    
    # Configuration files - readable by all, writable by root
    find "$CONFIG_DIR" -type f -name "*.conf" -exec chmod 644 {} \;
    
    # Data directory - accessible by pacman-sync user if it exists
    if id "pacman-sync" &>/dev/null; then
        chown -R pacman-sync:pacman-sync "$DATA_DIR"
        chmod 755 "$DATA_DIR"
        chmod 755 "$LOG_DIR"
    else
        log_warn "User 'pacman-sync' not found, using root ownership"
        chmod 755 "$DATA_DIR"
        chmod 755 "$LOG_DIR"
    fi
}

# Function to validate configuration files
validate_configuration() {
    log_info "Validating configuration files..."
    
    # Check if validation script exists
    local validator_script="/usr/bin/pacman-sync-validate-config"
    if [[ -x "$validator_script" ]]; then
        if "$validator_script" --config-dir "$CONFIG_DIR"; then
            log_info "Configuration validation passed"
        else
            log_error "Configuration validation failed"
            return 1
        fi
    else
        log_warn "Configuration validator not found, skipping validation"
    fi
}

# Main installation function
main() {
    log_info "Installing Pacman Sync Utility configuration files..."
    
    # Create necessary directories
    create_directory "$CONFIG_DIR" 755 root root
    create_directory "$DATA_DIR" 755 root root
    create_directory "$LOG_DIR" 755 root root
    create_directory "/var/log/pacman-sync-utility" 755 root root
    
    # Install configuration files
    install_config_file "$SOURCE_DIR/server.conf" "$CONFIG_DIR/server.conf" 644
    install_config_file "$SOURCE_DIR/client.conf" "$CONFIG_DIR/client.conf" 644
    install_config_file "$SOURCE_DIR/pools.conf" "$CONFIG_DIR/pools.conf" 644
    
    # Generate JWT secret key
    generate_jwt_secret
    
    # Set up proper permissions
    setup_permissions
    
    # Validate configuration
    validate_configuration
    
    log_info "Configuration installation completed successfully!"
    
    # Print post-installation information
    echo
    echo "Configuration files installed to: $CONFIG_DIR"
    echo "Data directory created at: $DATA_DIR"
    echo "Log directory created at: $LOG_DIR"
    echo
    echo "To customize the configuration:"
    echo "  - Edit $CONFIG_DIR/server.conf for server settings"
    echo "  - Edit $CONFIG_DIR/client.conf for client settings"
    echo "  - Edit $CONFIG_DIR/pools.conf for pool definitions"
    echo
    echo "To start the services:"
    echo "  - systemctl enable --now pacman-sync-server"
    echo "  - systemctl --user enable --now pacman-sync-client"
}

# Check if running as root for system-wide installation
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root for system-wide installation"
    exit 1
fi

# Run main function
main "$@"