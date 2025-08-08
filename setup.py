#!/usr/bin/env python3
"""
Setup script for Pacman Sync Utility

This script provides a unified interface for setting up, configuring,
and managing the Pacman Sync Utility installation.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PacmanSyncSetup:
    """Main setup and management class for Pacman Sync Utility."""
    
    def __init__(self):
        self.project_root = project_root
        self.setup_status = {}
        
    def run_setup(self, action: str, **kwargs) -> bool:
        """
        Run setup action.
        
        Args:
            action: Setup action to perform
            **kwargs: Additional arguments for the action
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Running setup action: {action}")
        
        actions = {
            "install": self._install,
            "configure": self._configure,
            "start": self._start_services,
            "stop": self._stop_services,
            "status": self._check_status,
            "validate": self._validate_deployment,
            "integrate": self._integrate_components,
            "uninstall": self._uninstall,
            "update": self._update,
            "backup": self._backup,
            "restore": self._restore,
        }
        
        if action not in actions:
            logger.error(f"Unknown action: {action}")
            return False
        
        try:
            return actions[action](**kwargs)
        except Exception as e:
            logger.error(f"Setup action failed: {e}")
            return False
    
    def _install(self, components: List[str], **kwargs) -> bool:
        """Install components using the installation script."""
        logger.info(f"Installing components: {', '.join(components)}")
        
        install_script = self.project_root / "install.sh"
        if not install_script.exists():
            logger.error("Installation script not found")
            return False
        
        # Build command arguments
        cmd = ["sudo", "bash", str(install_script)]
        
        if "server" in components:
            cmd.append("--server")
        if "client" in components:
            cmd.append("--client")
        if kwargs.get("systemd", False):
            cmd.append("--systemd")
        
        # Add custom directories if specified
        for arg_name in ["install_dir", "config_dir", "data_dir", "log_dir"]:
            if arg_name in kwargs:
                cmd.extend([f"--{arg_name.replace('_', '-')}", kwargs[arg_name]])
        
        try:
            result = subprocess.run(cmd, check=True)
            logger.info("Installation completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Installation failed: {e}")
            return False
    
    def _configure(self, **kwargs) -> bool:
        """Configure the system with custom settings."""
        logger.info("Configuring system...")
        
        success = True
        
        # Configure server if requested
        if kwargs.get("server", False):
            success &= self._configure_server(**kwargs)
        
        # Configure client if requested
        if kwargs.get("client", False):
            success &= self._configure_client(**kwargs)
        
        return success
    
    def _configure_server(self, **kwargs) -> bool:
        """Configure server settings."""
        logger.info("Configuring server...")
        
        config_file = Path(kwargs.get("server_config", "/etc/pacman-sync/server.conf"))
        template_file = self.project_root / "config" / "server.conf.template"
        
        if not template_file.exists():
            logger.error("Server configuration template not found")
            return False
        
        try:
            # Read template
            with open(template_file, 'r') as f:
                config_content = f.read()
            
            # Apply customizations
            customizations = {
                "CHANGE_THIS_SECRET_KEY": kwargs.get("jwt_secret", self._generate_secret_key()),
                "localhost:8080": kwargs.get("server_url", "localhost:8080"),
                "/var/lib/pacman-sync": kwargs.get("data_dir", "/var/lib/pacman-sync"),
                "/var/log/pacman-sync": kwargs.get("log_dir", "/var/log/pacman-sync"),
            }
            
            for old_value, new_value in customizations.items():
                config_content = config_content.replace(old_value, new_value)
            
            # Write configuration
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Server configuration written to: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Server configuration failed: {e}")
            return False
    
    def _configure_client(self, **kwargs) -> bool:
        """Configure client settings."""
        logger.info("Configuring client...")
        
        config_file = Path(kwargs.get("client_config", "~/.config/pacman-sync/client.conf")).expanduser()
        template_file = self.project_root / "config" / "client.conf.template"
        
        if not template_file.exists():
            logger.error("Client configuration template not found")
            return False
        
        try:
            # Read template
            with open(template_file, 'r') as f:
                config_content = f.read()
            
            # Apply customizations
            customizations = {
                "http://localhost:8080": kwargs.get("server_url", "http://localhost:8080"),
                "endpoint_name = ": f"endpoint_name = {kwargs.get('endpoint_name', os.uname().nodename)}",
            }
            
            for old_value, new_value in customizations.items():
                config_content = config_content.replace(old_value, new_value)
            
            # Write configuration
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Client configuration written to: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Client configuration failed: {e}")
            return False
    
    def _start_services(self, services: List[str], **kwargs) -> bool:
        """Start system services."""
        logger.info(f"Starting services: {', '.join(services)}")
        
        success = True
        
        for service in services:
            try:
                if service == "server":
                    subprocess.run(["sudo", "systemctl", "start", "pacman-sync-server"], check=True)
                    subprocess.run(["sudo", "systemctl", "enable", "pacman-sync-server"], check=True)
                elif service == "client":
                    subprocess.run(["systemctl", "--user", "start", "pacman-sync-client"], check=True)
                    subprocess.run(["systemctl", "--user", "enable", "pacman-sync-client"], check=True)
                
                logger.info(f"Service started: {service}")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to start service {service}: {e}")
                success = False
        
        return success
    
    def _stop_services(self, services: List[str], **kwargs) -> bool:
        """Stop system services."""
        logger.info(f"Stopping services: {', '.join(services)}")
        
        success = True
        
        for service in services:
            try:
                if service == "server":
                    subprocess.run(["sudo", "systemctl", "stop", "pacman-sync-server"], check=True)
                elif service == "client":
                    subprocess.run(["systemctl", "--user", "stop", "pacman-sync-client"], check=True)
                
                logger.info(f"Service stopped: {service}")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to stop service {service}: {e}")
                success = False
        
        return success
    
    def _check_status(self, **kwargs) -> bool:
        """Check system status."""
        logger.info("Checking system status...")
        
        print("\n" + "="*60)
        print("PACMAN SYNC UTILITY STATUS")
        print("="*60)
        
        # Check services
        services = [
            ("Server", "pacman-sync-server", False),
            ("Client", "pacman-sync-client", True)
        ]
        
        for name, service, is_user in services:
            try:
                cmd = ["systemctl"]
                if is_user:
                    cmd.append("--user")
                cmd.extend(["is-active", service])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                status = result.stdout.strip()
                
                status_symbol = "✓" if status == "active" else "✗"
                print(f"{status_symbol} {name} Service: {status}")
                
            except Exception as e:
                print(f"✗ {name} Service: error ({e})")
        
        # Check server connectivity
        try:
            import aiohttp
            import asyncio
            
            async def check_server():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get("http://localhost:8080/health/live", timeout=5) as response:
                            return response.status == 200
                except:
                    return False
            
            server_accessible = asyncio.run(check_server())
            status_symbol = "✓" if server_accessible else "✗"
            print(f"{status_symbol} Server API: {'accessible' if server_accessible else 'not accessible'}")
            
        except ImportError:
            print("? Server API: cannot check (aiohttp not available)")
        
        # Check configuration files
        config_files = [
            "/etc/pacman-sync/server.conf",
            "~/.config/pacman-sync/client.conf"
        ]
        
        for config_file in config_files:
            path = Path(config_file).expanduser()
            exists = path.exists()
            status_symbol = "✓" if exists else "✗"
            print(f"{status_symbol} Config: {config_file} ({'exists' if exists else 'missing'})")
        
        print("="*60)
        
        return True
    
    def _validate_deployment(self, **kwargs) -> bool:
        """Validate deployment using validation script."""
        logger.info("Validating deployment...")
        
        validation_script = self.project_root / "scripts" / "validate-deployment.py"
        if not validation_script.exists():
            logger.error("Validation script not found")
            return False
        
        try:
            cmd = ["python3", str(validation_script)]
            
            if "components" in kwargs:
                cmd.extend(["--components"] + kwargs["components"])
            
            if "server_url" in kwargs:
                cmd.extend(["--server-url", kwargs["server_url"]])
            
            result = subprocess.run(cmd, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def _integrate_components(self, **kwargs) -> bool:
        """Integrate components using integration script."""
        logger.info("Integrating components...")
        
        integration_script = self.project_root / "scripts" / "integrate-components.py"
        if not integration_script.exists():
            logger.error("Integration script not found")
            return False
        
        try:
            cmd = ["python3", str(integration_script)]
            
            if "components" in kwargs:
                cmd.extend(["--components"] + kwargs["components"])
            
            if kwargs.get("verify_only", False):
                cmd.append("--verify-only")
            
            result = subprocess.run(cmd, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Integration failed: {e}")
            return False
    
    def _uninstall(self, **kwargs) -> bool:
        """Uninstall the system."""
        logger.info("Uninstalling system...")
        
        # Stop services first
        self._stop_services(["server", "client"])
        
        # Remove systemd services
        try:
            subprocess.run(["sudo", "systemctl", "disable", "pacman-sync-server"], check=False)
            subprocess.run(["systemctl", "--user", "disable", "pacman-sync-client"], check=False)
            
            service_files = [
                "/etc/systemd/system/pacman-sync-server.service",
                "/etc/systemd/user/pacman-sync-client.service"
            ]
            
            for service_file in service_files:
                if os.path.exists(service_file):
                    os.remove(service_file)
            
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            
        except Exception as e:
            logger.warning(f"Service cleanup warning: {e}")
        
        # Remove installation directories
        directories_to_remove = [
            "/opt/pacman-sync",
            "/etc/pacman-sync"
        ]
        
        if kwargs.get("remove_data", False):
            directories_to_remove.extend([
                "/var/lib/pacman-sync",
                "/var/log/pacman-sync"
            ])
        
        for directory in directories_to_remove:
            try:
                subprocess.run(["sudo", "rm", "-rf", directory], check=True)
                logger.info(f"Removed directory: {directory}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to remove {directory}: {e}")
        
        # Remove wrapper scripts
        wrapper_scripts = [
            "/usr/local/bin/pacman-sync-server",
            "/usr/local/bin/pacman-sync-client",
            "/usr/local/bin/pacman-sync"
        ]
        
        for script in wrapper_scripts:
            try:
                if os.path.exists(script):
                    os.remove(script)
                    logger.info(f"Removed script: {script}")
            except Exception as e:
                logger.warning(f"Failed to remove {script}: {e}")
        
        logger.info("Uninstallation completed")
        return True
    
    def _update(self, **kwargs) -> bool:
        """Update the system."""
        logger.info("Updating system...")
        
        # This would typically pull updates from git and reinstall
        # For now, we'll just run the integration to ensure everything is up to date
        return self._integrate_components(**kwargs)
    
    def _backup(self, backup_path: str, **kwargs) -> bool:
        """Backup system configuration and data."""
        logger.info(f"Creating backup at: {backup_path}")
        
        backup_dir = Path(backup_path)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup configuration
        config_dirs = [
            "/etc/pacman-sync",
            "~/.config/pacman-sync"
        ]
        
        for config_dir in config_dirs:
            source = Path(config_dir).expanduser()
            if source.exists():
                dest = backup_dir / "config" / source.name
                try:
                    subprocess.run(["cp", "-r", str(source), str(dest.parent)], check=True)
                    logger.info(f"Backed up configuration: {source}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to backup {source}: {e}")
        
        # Backup data
        if kwargs.get("include_data", True):
            data_dirs = [
                "/var/lib/pacman-sync",
                "~/.local/share/pacman-sync"
            ]
            
            for data_dir in data_dirs:
                source = Path(data_dir).expanduser()
                if source.exists():
                    dest = backup_dir / "data" / source.name
                    try:
                        subprocess.run(["cp", "-r", str(source), str(dest.parent)], check=True)
                        logger.info(f"Backed up data: {source}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to backup {source}: {e}")
        
        logger.info("Backup completed")
        return True
    
    def _restore(self, backup_path: str, **kwargs) -> bool:
        """Restore system from backup."""
        logger.info(f"Restoring from backup: {backup_path}")
        
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            logger.error(f"Backup directory not found: {backup_path}")
            return False
        
        # Restore configuration
        config_backup = backup_dir / "config"
        if config_backup.exists():
            for config_dir in config_backup.iterdir():
                if config_dir.name == "pacman-sync":
                    dest = Path("/etc/pacman-sync")
                    try:
                        subprocess.run(["sudo", "cp", "-r", str(config_dir), str(dest.parent)], check=True)
                        logger.info(f"Restored configuration: {dest}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to restore configuration: {e}")
        
        # Restore data
        if kwargs.get("include_data", True):
            data_backup = backup_dir / "data"
            if data_backup.exists():
                for data_dir in data_backup.iterdir():
                    if data_dir.name == "pacman-sync":
                        dest = Path("/var/lib/pacman-sync")
                        try:
                            subprocess.run(["sudo", "cp", "-r", str(data_dir), str(dest.parent)], check=True)
                            logger.info(f"Restored data: {dest}")
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Failed to restore data: {e}")
        
        logger.info("Restore completed")
        return True
    
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key."""
        try:
            result = subprocess.run(["openssl", "rand", "-hex", "32"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # Fallback to Python's secrets module
            import secrets
            return secrets.token_hex(32)


def main():
    """Main entry point for setup script."""
    parser = argparse.ArgumentParser(
        description="Pacman Sync Utility Setup and Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s install --server --client --systemd    # Full installation
  %(prog)s configure --server --client            # Configure both components
  %(prog)s start --services server client         # Start services
  %(prog)s status                                  # Check system status
  %(prog)s validate                                # Validate deployment
  %(prog)s backup /path/to/backup                  # Create backup
  %(prog)s uninstall --remove-data                # Complete uninstall
        """
    )
    
    parser.add_argument(
        "action",
        choices=["install", "configure", "start", "stop", "status", "validate", "integrate", "uninstall", "update", "backup", "restore"],
        help="Action to perform"
    )
    
    # Installation options
    install_group = parser.add_argument_group("Installation")
    install_group.add_argument("--server", action="store_true", help="Include server component")
    install_group.add_argument("--client", action="store_true", help="Include client component")
    install_group.add_argument("--systemd", action="store_true", help="Install systemd services")
    install_group.add_argument("--install-dir", help="Custom installation directory")
    install_group.add_argument("--config-dir", help="Custom configuration directory")
    install_group.add_argument("--data-dir", help="Custom data directory")
    install_group.add_argument("--log-dir", help="Custom log directory")
    
    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument("--server-config", help="Server configuration file path")
    config_group.add_argument("--client-config", help="Client configuration file path")
    config_group.add_argument("--server-url", help="Server URL")
    config_group.add_argument("--endpoint-name", help="Client endpoint name")
    config_group.add_argument("--jwt-secret", help="JWT secret key")
    
    # Service management
    service_group = parser.add_argument_group("Services")
    service_group.add_argument("--services", nargs="+", choices=["server", "client"], help="Services to manage")
    
    # Validation and integration
    validation_group = parser.add_argument_group("Validation")
    validation_group.add_argument("--components", nargs="+", help="Components to validate/integrate")
    validation_group.add_argument("--verify-only", action="store_true", help="Verify only, don't make changes")
    
    # Backup and restore
    backup_group = parser.add_argument_group("Backup/Restore")
    backup_group.add_argument("--backup-path", help="Backup directory path")
    backup_group.add_argument("--include-data", action="store_true", help="Include data in backup/restore")
    backup_group.add_argument("--remove-data", action="store_true", help="Remove data during uninstall")
    
    # General options
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create setup manager
    setup = PacmanSyncSetup()
    
    # Prepare arguments
    kwargs = {}
    
    # Add all arguments to kwargs
    for arg_name, arg_value in vars(args).items():
        if arg_value is not None and arg_name != "action":
            kwargs[arg_name] = arg_value
    
    # Handle special cases
    if args.action in ["install", "start", "stop"]:
        components = []
        if args.server:
            components.append("server")
        if args.client:
            components.append("client")
        if not components and args.action == "install":
            components = ["server", "client"]  # Default to both
        kwargs["components"] = components
        
        if args.services:
            kwargs["services"] = args.services
        elif args.action in ["start", "stop"]:
            kwargs["services"] = components
    
    if args.action in ["backup", "restore"] and args.backup_path:
        kwargs["backup_path"] = args.backup_path
    
    try:
        # Run setup action
        success = setup.run_setup(args.action, **kwargs)
        
        if success:
            print(f"\n✓ Setup action '{args.action}' completed successfully!")
            return 0
        else:
            print(f"\n✗ Setup action '{args.action}' failed!")
            return 1
            
    except KeyboardInterrupt:
        print(f"\nSetup action '{args.action}' cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Setup error: {e}")
        print(f"\n✗ Setup error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())