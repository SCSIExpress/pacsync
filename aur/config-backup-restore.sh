#!/bin/bash
# Configuration Backup and Restore Utility
# Handles .pacnew/.pacsave file management for pacman-sync-utility

CONFIG_DIR="/etc/pacman-sync-utility"
BACKUP_DIR="/var/backups/pacman-sync-utility/config"
CONFIG_FILES=("client.conf" "server.conf" "pools.conf")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 {backup|restore|merge|check|list}"
    echo ""
    echo "Commands:"
    echo "  backup   - Create backup of current configuration files"
    echo "  restore  - Restore configuration files from backup"
    echo "  merge    - Interactive merge of .pacnew files"
    echo "  check    - Check for .pacnew/.pacsave files"
    echo "  list     - List available backups"
    echo ""
    exit 1
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        chmod 755 "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

backup_configs() {
    log_info "Creating configuration backup..."
    
    create_backup_dir
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_SUBDIR="$BACKUP_DIR/$TIMESTAMP"
    
    mkdir -p "$BACKUP_SUBDIR"
    
    for config_file in "${CONFIG_FILES[@]}"; do
        config_path="$CONFIG_DIR/$config_file"
        
        if [ -f "$config_path" ]; then
            cp "$config_path" "$BACKUP_SUBDIR/"
            log_success "Backed up $config_file"
        else
            log_warning "Configuration file not found: $config_path"
        fi
    done
    
    # Create backup metadata
    cat > "$BACKUP_SUBDIR/backup_info.txt" << EOF
Backup created: $(date)
Hostname: $(hostname)
User: $(whoami)
Package version: $(pacman -Q pacman-sync-utility 2>/dev/null || echo "unknown")
EOF
    
    log_success "Backup created in: $BACKUP_SUBDIR"
}

list_backups() {
    log_info "Available configuration backups:"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warning "No backup directory found"
        return 1
    fi
    
    backup_count=0
    for backup_dir in "$BACKUP_DIR"/*; do
        if [ -d "$backup_dir" ]; then
            backup_name=$(basename "$backup_dir")
            if [ -f "$backup_dir/backup_info.txt" ]; then
                backup_date=$(grep "Backup created:" "$backup_dir/backup_info.txt" | cut -d: -f2-)
                echo "  $backup_name -$backup_date"
            else
                echo "  $backup_name"
            fi
            backup_count=$((backup_count + 1))
        fi
    done
    
    if [ $backup_count -eq 0 ]; then
        log_warning "No backups found"
        return 1
    fi
    
    echo ""
    log_info "Total backups: $backup_count"
}

restore_configs() {
    log_info "Restoring configuration from backup..."
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "No backup directory found"
        return 1
    fi
    
    # Find the most recent backup
    latest_backup=$(ls -1t "$BACKUP_DIR" | head -n1)
    
    if [ -z "$latest_backup" ]; then
        log_error "No backups found"
        return 1
    fi
    
    backup_path="$BACKUP_DIR/$latest_backup"
    log_info "Restoring from: $backup_path"
    
    # Create current backup before restoring
    log_info "Creating backup of current configuration before restore..."
    backup_configs
    
    for config_file in "${CONFIG_FILES[@]}"; do
        backup_file="$backup_path/$config_file"
        config_path="$CONFIG_DIR/$config_file"
        
        if [ -f "$backup_file" ]; then
            cp "$backup_file" "$config_path"
            chmod 644 "$config_path"
            chown root:root "$config_path"
            log_success "Restored $config_file"
        else
            log_warning "Backup file not found: $backup_file"
        fi
    done
    
    log_success "Configuration restored from backup"
}

check_pacnew_files() {
    log_info "Checking for .pacnew and .pacsave files..."
    
    found_files=false
    
    for config_file in "${CONFIG_FILES[@]}"; do
        pacnew_file="$CONFIG_DIR/$config_file.pacnew"
        pacsave_file="$CONFIG_DIR/$config_file.pacsave"
        
        if [ -f "$pacnew_file" ]; then
            log_warning "Found .pacnew file: $pacnew_file"
            found_files=true
        fi
        
        if [ -f "$pacsave_file" ]; then
            log_warning "Found .pacsave file: $pacsave_file"
            found_files=true
        fi
    done
    
    if [ "$found_files" = false ]; then
        log_success "No .pacnew or .pacsave files found"
    else
        echo ""
        log_info "Use '$0 merge' to interactively merge .pacnew files"
    fi
}

merge_pacnew_files() {
    log_info "Interactive merge of .pacnew files..."
    
    if ! command -v vimdiff >/dev/null 2>&1; then
        log_error "vimdiff not found. Please install vim or use manual merge."
        return 1
    fi
    
    found_pacnew=false
    
    for config_file in "${CONFIG_FILES[@]}"; do
        config_path="$CONFIG_DIR/$config_file"
        pacnew_file="$config_path.pacnew"
        
        if [ -f "$pacnew_file" ]; then
            found_pacnew=true
            
            echo ""
            log_info "Merging $config_file..."
            echo "Current file: $config_path"
            echo "New file:     $pacnew_file"
            echo ""
            
            read -p "Do you want to merge this file? [y/N]: " -n 1 -r
            echo
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # Create backup before merge
                cp "$config_path" "$config_path.backup.$(date +%s)"
                
                # Launch vimdiff for interactive merge
                vimdiff "$config_path" "$pacnew_file"
                
                read -p "Merge completed. Remove .pacnew file? [y/N]: " -n 1 -r
                echo
                
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    rm "$pacnew_file"
                    log_success "Removed $pacnew_file"
                fi
            else
                log_info "Skipped merging $config_file"
            fi
        fi
    done
    
    if [ "$found_pacnew" = false ]; then
        log_info "No .pacnew files found to merge"
    fi
}

# Main script logic
case "$1" in
    backup)
        backup_configs
        ;;
    restore)
        restore_configs
        ;;
    merge)
        merge_pacnew_files
        ;;
    check)
        check_pacnew_files
        ;;
    list)
        list_backups
        ;;
    *)
        usage
        ;;
esac