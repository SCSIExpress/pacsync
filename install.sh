#!/bin/bash

# Pacman Sync Utility - Installation Script
# This script installs the Pacman Sync Utility server and/or client components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
INSTALL_SERVER=false
INSTALL_CLIENT=false
INSTALL_SYSTEMD=false
INSTALL_DIR="/opt/pacman-sync"
CONFIG_DIR="/etc/pacman-sync"
DATA_DIR="/var/lib/pacman-sync"
LOG_DIR="/var/log/pacman-sync"
USER="pacman-sync"
GROUP="pacman-sync"
PYTHON_VERSION="3.8"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --server                Install server components
    --client                Install client components
    --systemd               Install systemd service files
    --install-dir DIR       Installation directory [default: /opt/pacman-sync]
    --config-dir DIR        Configuration directory [default: /etc/pacman-sync]
    --data-dir DIR          Data directory [default: /var/lib/pacman-sync]
    --log-dir DIR           Log directory [default: /var/log/pacman-sync]
    --user USER             System user [default: pacman-sync]
    --group GROUP           System group [default: pacman-sync]
    --python-version VER    Minimum Python version [default: 3.8]
    -h, --help              Show this help message

Examples:
    $0 --server --systemd                    # Install server with systemd service
    $0 --client                              # Install client only
    $0 --server --client --systemd           # Install both server and client
    $0 --server --install-dir /usr/local/pacman-sync  # Custom install directory

EOF
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root for system installation"
        print_info "Use 'sudo $0' to run with root privileges"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (${PYTHON_VERSION//./, }) else 1)"; then
        print_error "Python $PYTHON_VERSION or higher is required (found $python_version)"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed"
        exit 1
    fi
    
    # Check systemctl if systemd installation requested
    if $INSTALL_SYSTEMD && ! command -v systemctl &> /dev/null; then
        print_error "systemctl is not available (systemd required for --systemd option)"
        exit 1
    fi
    
    # Check Qt dependencies for client
    if $INSTALL_CLIENT; then
        if ! python3 -c "import PyQt6" 2>/dev/null; then
            print_warning "PyQt6 not found. It will be installed as a dependency."
        fi
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create system user and group
create_system_user() {
    if $INSTALL_SERVER; then
        print_info "Creating system user and group..."
        
        # Create group if it doesn't exist
        if ! getent group "$GROUP" >/dev/null 2>&1; then
            groupadd --system "$GROUP"
            print_success "Created group: $GROUP"
        fi
        
        # Create user if it doesn't exist
        if ! getent passwd "$USER" >/dev/null 2>&1; then
            useradd --system --gid "$GROUP" --home-dir "$DATA_DIR" \
                    --shell /bin/false --comment "Pacman Sync Utility" "$USER"
            print_success "Created user: $USER"
        fi
    fi
}

# Function to create directories
create_directories() {
    print_info "Creating directories..."
    
    # Installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Configuration directory
    mkdir -p "$CONFIG_DIR"
    
    if $INSTALL_SERVER; then
        # Server directories
        mkdir -p "$DATA_DIR"
        mkdir -p "$LOG_DIR"
        
        # Set ownership for server directories
        chown "$USER:$GROUP" "$DATA_DIR" "$LOG_DIR"
        chmod 755 "$DATA_DIR" "$LOG_DIR"
    fi
    
    if $INSTALL_CLIENT; then
        # Client configuration directory
        mkdir -p "$CONFIG_DIR/client"
        chmod 755 "$CONFIG_DIR/client"
    fi
    
    print_success "Directories created"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_info "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    if $INSTALL_SERVER; then
        print_info "Installing server dependencies..."
        pip install -r server-requirements.txt
    fi
    
    if $INSTALL_CLIENT; then
        print_info "Installing client dependencies..."
        pip install -r requirements.txt
    fi
    
    deactivate
    print_success "Python dependencies installed"
}

# Function to copy application files
copy_application_files() {
    print_info "Copying application files..."
    
    # Copy shared components
    cp -r shared/ "$INSTALL_DIR/"
    
    if $INSTALL_SERVER; then
        # Copy server components
        cp -r server/ "$INSTALL_DIR/"
        
        # Set ownership
        chown -R "$USER:$GROUP" "$INSTALL_DIR/server" "$INSTALL_DIR/shared"
    fi
    
    if $INSTALL_CLIENT; then
        # Copy client components
        cp -r client/ "$INSTALL_DIR/"
        
        # Make client executable accessible to all users
        chmod 755 "$INSTALL_DIR/client"
    fi
    
    # Copy documentation
    cp README.md "$INSTALL_DIR/"
    cp -r docs/ "$INSTALL_DIR/" 2>/dev/null || true
    
    print_success "Application files copied"
}

# Function to create configuration files
create_configuration_files() {
    print_info "Creating configuration files..."
    
    if $INSTALL_SERVER; then
        # Server configuration
        cat > "$CONFIG_DIR/server.conf" << EOF
# Pacman Sync Utility Server Configuration

[database]
type = internal
# For PostgreSQL, uncomment and configure:
# type = postgresql
# url = postgresql://user:password@localhost:5432/pacman_sync

[server]
host = 0.0.0.0
port = 8080
environment = production
log_level = INFO
cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

[security]
jwt_secret_key = $(openssl rand -hex 32)
jwt_expiration_hours = 24
enable_rate_limiting = true
api_rate_limit = 100
admin_tokens = []

[features]
enable_repository_analysis = true
auto_cleanup_old_states = true

[paths]
data_dir = $DATA_DIR
log_dir = $LOG_DIR
EOF
        
        chown "$USER:$GROUP" "$CONFIG_DIR/server.conf"
        chmod 640 "$CONFIG_DIR/server.conf"
    fi
    
    if $INSTALL_CLIENT; then
        # Client configuration template
        cat > "$CONFIG_DIR/client/client.conf" << EOF
# Pacman Sync Utility Client Configuration

[server]
url = http://localhost:8080
# api_key = your-api-key-here

[client]
endpoint_name = $(hostname)
# pool_id = default-pool
auto_sync = false
update_interval = 300

[ui]
show_notifications = true
minimize_to_tray = true
enable_system_tray = true

[logging]
log_level = INFO
# log_file = /var/log/pacman-sync/client.log
EOF
        
        chmod 644 "$CONFIG_DIR/client/client.conf"
    fi
    
    print_success "Configuration files created"
}

# Function to create systemd service files
create_systemd_services() {
    if $INSTALL_SYSTEMD; then
        print_info "Creating systemd service files..."
        
        if $INSTALL_SERVER; then
            # Server service
            cat > /etc/systemd/system/pacman-sync-server.service << EOF
[Unit]
Description=Pacman Sync Utility Server
Documentation=file://$INSTALL_DIR/README.md
After=network.target
Wants=network.target

[Service]
Type=exec
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
Environment=PYTHONPATH=$INSTALL_DIR
Environment=CONFIG_FILE=$CONFIG_DIR/server.conf
ExecStart=$INSTALL_DIR/venv/bin/python -m server.main
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
TimeoutStopSec=30

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR $LOG_DIR
CapabilityBoundingSet=

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
        fi
        
        if $INSTALL_CLIENT; then
            # Client service (user service template)
            mkdir -p /etc/systemd/user
            cat > /etc/systemd/user/pacman-sync-client.service << EOF
[Unit]
Description=Pacman Sync Utility Client
Documentation=file://$INSTALL_DIR/README.md
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=exec
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
Environment=PYTHONPATH=$INSTALL_DIR
Environment=CONFIG_FILE=$CONFIG_DIR/client/client.conf
Environment=DISPLAY=:0
ExecStart=$INSTALL_DIR/venv/bin/python -m client.main
Restart=always
RestartSec=10
TimeoutStopSec=30

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=false

[Install]
WantedBy=default.target
EOF
        fi
        
        # Reload systemd
        systemctl daemon-reload
        
        print_success "Systemd service files created"
    fi
}

# Function to create wrapper scripts
create_wrapper_scripts() {
    print_info "Creating wrapper scripts..."
    
    if $INSTALL_SERVER; then
        # Server wrapper script
        cat > /usr/local/bin/pacman-sync-server << EOF
#!/bin/bash
cd "$INSTALL_DIR"
export PYTHONPATH="$INSTALL_DIR"
export CONFIG_FILE="$CONFIG_DIR/server.conf"
exec "$INSTALL_DIR/venv/bin/python" -m server.main "\$@"
EOF
        chmod 755 /usr/local/bin/pacman-sync-server
    fi
    
    if $INSTALL_CLIENT; then
        # Client wrapper script
        cat > /usr/local/bin/pacman-sync-client << EOF
#!/bin/bash
cd "$INSTALL_DIR"
export PYTHONPATH="$INSTALL_DIR"
export CONFIG_FILE="$CONFIG_DIR/client/client.conf"
exec "$INSTALL_DIR/venv/bin/python" -m client.main "\$@"
EOF
        chmod 755 /usr/local/bin/pacman-sync-client
        
        # Create symlink for convenience
        ln -sf /usr/local/bin/pacman-sync-client /usr/local/bin/pacman-sync
    fi
    
    print_success "Wrapper scripts created"
}

# Function to set up log rotation
setup_log_rotation() {
    if $INSTALL_SERVER; then
        print_info "Setting up log rotation..."
        
        cat > /etc/logrotate.d/pacman-sync << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $GROUP
    postrotate
        systemctl reload pacman-sync-server 2>/dev/null || true
    endscript
}
EOF
        
        print_success "Log rotation configured"
    fi
}

# Function to display post-installation instructions
show_post_install_instructions() {
    print_success "Installation completed successfully!"
    echo
    print_info "Post-installation steps:"
    echo
    
    if $INSTALL_SERVER; then
        echo "Server:"
        echo "  1. Review and customize the configuration: $CONFIG_DIR/server.conf"
        echo "  2. For PostgreSQL, create database and update configuration"
        echo "  3. Start the server:"
        if $INSTALL_SYSTEMD; then
            echo "     sudo systemctl enable --now pacman-sync-server"
        else
            echo "     pacman-sync-server"
        fi
        echo "  4. Access web UI at: http://localhost:8080"
        echo
    fi
    
    if $INSTALL_CLIENT; then
        echo "Client:"
        echo "  1. Review and customize the configuration: $CONFIG_DIR/client/client.conf"
        echo "  2. Configure server URL and endpoint name"
        echo "  3. Start the client:"
        if $INSTALL_SYSTEMD; then
            echo "     systemctl --user enable --now pacman-sync-client"
        else
            echo "     pacman-sync-client"
        fi
        echo "  4. Check system tray for sync status icon"
        echo
        echo "Command-line usage:"
        echo "  pacman-sync --status          # Check sync status"
        echo "  pacman-sync --sync            # Sync to latest"
        echo "  pacman-sync --set-latest      # Set current as latest"
        echo "  pacman-sync --revert          # Revert to previous"
        echo
    fi
    
    echo "Documentation: $INSTALL_DIR/README.md"
    echo "Configuration: $CONFIG_DIR/"
    if $INSTALL_SERVER; then
        echo "Data directory: $DATA_DIR"
        echo "Log directory: $LOG_DIR"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            INSTALL_SERVER=true
            shift
            ;;
        --client)
            INSTALL_CLIENT=true
            shift
            ;;
        --systemd)
            INSTALL_SYSTEMD=true
            shift
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --group)
            GROUP="$2"
            shift 2
            ;;
        --python-version)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate arguments
if ! $INSTALL_SERVER && ! $INSTALL_CLIENT; then
    print_error "Must specify --server and/or --client"
    show_usage
    exit 1
fi

# Check if running as root
check_root

# Run installation steps
print_info "Starting Pacman Sync Utility installation..."
print_info "Server: $INSTALL_SERVER, Client: $INSTALL_CLIENT, Systemd: $INSTALL_SYSTEMD"

check_prerequisites
create_system_user
create_directories
install_python_dependencies
copy_application_files
create_configuration_files
create_systemd_services
create_wrapper_scripts
setup_log_rotation
show_post_install_instructions