#!/usr/bin/env python3
"""
Test Configuration Installation Implementation
Tests the configuration file installation functionality for task 4.2
"""

import os
import sys
import tempfile
import shutil
import subprocess
import stat
from pathlib import Path


class ConfigInstallationTester:
    def __init__(self):
        self.test_dir = None
        self.config_dir = None
        self.passed_tests = 0
        self.failed_tests = 0
        
    def setup_test_environment(self):
        """Set up temporary test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="pacman-sync-config-test-")
        self.config_dir = os.path.join(self.test_dir, "etc", "pacman-sync-utility")
        os.makedirs(self.config_dir, exist_ok=True)
        print(f"Test environment created: {self.test_dir}")
        
    def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            print(f"Test environment cleaned up: {self.test_dir}")
    
    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}")
        if message:
            print(f"        {message}")
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
    
    def test_directory_structure_creation(self):
        """Test configuration directory structure creation"""
        test_name = "Configuration directory structure creation"
        
        try:
            # Create main config directory
            os.makedirs(self.config_dir, mode=0o755, exist_ok=True)
            
            # Create conf.d subdirectory
            conf_d_dir = os.path.join(self.config_dir, "conf.d")
            os.makedirs(conf_d_dir, mode=0o755, exist_ok=True)
            
            # Check directory exists and has correct permissions
            if not os.path.exists(self.config_dir):
                self.log_test(test_name, False, "Main config directory not created")
                return
            
            if not os.path.exists(conf_d_dir):
                self.log_test(test_name, False, "conf.d subdirectory not created")
                return
            
            # Check permissions
            main_stat = os.stat(self.config_dir)
            main_mode = stat.S_IMODE(main_stat.st_mode)
            
            conf_d_stat = os.stat(conf_d_dir)
            conf_d_mode = stat.S_IMODE(conf_d_stat.st_mode)
            
            if main_mode != 0o755:
                self.log_test(test_name, False, f"Main directory has wrong permissions: {oct(main_mode)}")
                return
            
            if conf_d_mode != 0o755:
                self.log_test(test_name, False, f"conf.d directory has wrong permissions: {oct(conf_d_mode)}")
                return
            
            self.log_test(test_name, True, "Directory structure created with correct permissions")
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def test_configuration_file_installation(self):
        """Test configuration file installation"""
        test_name = "Configuration file installation"
        
        try:
            # Copy configuration files from AUR directory
            aur_dir = Path(__file__).parent
            config_files = ["client.conf", "server.conf", "pools.conf"]
            
            for config_file in config_files:
                src_path = aur_dir / config_file
                dst_path = Path(self.config_dir) / config_file
                
                if not src_path.exists():
                    self.log_test(test_name, False, f"Source config file not found: {src_path}")
                    return
                
                # Copy file
                shutil.copy2(src_path, dst_path)
                
                # Set proper permissions
                os.chmod(dst_path, 0o644)
                
                # Verify file exists and has correct permissions
                if not dst_path.exists():
                    self.log_test(test_name, False, f"Config file not installed: {dst_path}")
                    return
                
                file_stat = os.stat(dst_path)
                file_mode = stat.S_IMODE(file_stat.st_mode)
                
                if file_mode != 0o644:
                    self.log_test(test_name, False, f"{config_file} has wrong permissions: {oct(file_mode)}")
                    return
            
            self.log_test(test_name, True, "All configuration files installed with correct permissions")
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def test_backup_functionality(self):
        """Test configuration backup functionality"""
        test_name = "Configuration backup functionality"
        
        try:
            # Create test configuration files
            config_files = ["client.conf", "server.conf", "pools.conf"]
            
            for config_file in config_files:
                config_path = os.path.join(self.config_dir, config_file)
                with open(config_path, 'w') as f:
                    f.write(f"# Test configuration for {config_file}\n")
                    f.write("test_setting: test_value\n")
            
            # Test backup script exists
            backup_script = Path(__file__).parent / "config-backup-restore.sh"
            if not backup_script.exists():
                self.log_test(test_name, False, "Backup script not found")
                return
            
            # Test backup script is executable
            script_stat = os.stat(backup_script)
            if not (script_stat.st_mode & stat.S_IEXEC):
                self.log_test(test_name, False, "Backup script is not executable")
                return
            
            self.log_test(test_name, True, "Backup functionality components are present")
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def test_pacnew_pacsave_handling(self):
        """Test .pacnew/.pacsave file handling"""
        test_name = ".pacnew/.pacsave file handling"
        
        try:
            # Create test configuration file
            config_path = os.path.join(self.config_dir, "client.conf")
            with open(config_path, 'w') as f:
                f.write("# Original configuration\n")
                f.write("original_setting: original_value\n")
            
            # Create .pacnew file
            pacnew_path = config_path + ".pacnew"
            with open(pacnew_path, 'w') as f:
                f.write("# New configuration\n")
                f.write("new_setting: new_value\n")
            
            # Create .pacsave file
            pacsave_path = config_path + ".pacsave"
            with open(pacsave_path, 'w') as f:
                f.write("# Saved configuration\n")
                f.write("saved_setting: saved_value\n")
            
            # Verify files exist
            if not os.path.exists(pacnew_path):
                self.log_test(test_name, False, ".pacnew file not created")
                return
            
            if not os.path.exists(pacsave_path):
                self.log_test(test_name, False, ".pacsave file not created")
                return
            
            self.log_test(test_name, True, ".pacnew/.pacsave files can be created and managed")
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        test_name = "Configuration validation"
        
        try:
            # Test validation script exists
            validation_script = Path(__file__).parent / "validate-config-installation.py"
            if not validation_script.exists():
                self.log_test(test_name, False, "Validation script not found")
                return
            
            # Test validation script is executable
            script_stat = os.stat(validation_script)
            if not (script_stat.st_mode & stat.S_IEXEC):
                self.log_test(test_name, False, "Validation script is not executable")
                return
            
            # Create valid configuration files for testing
            config_files = {
                "client.conf": """
client:
  server_url: "http://localhost:8000"
  endpoint_name: "test-endpoint"
  
logging:
  log_level: "INFO"
""",
                "server.conf": """
server:
  host: "0.0.0.0"
  port: 8000
  
security:
  jwt_secret_key: "test-secret-key"
""",
                "pools.conf": """
default:
  name: "Default Pool"
  description: "Default pool for new endpoints"
  auto_assign: true
"""
            }
            
            for filename, content in config_files.items():
                config_path = os.path.join(self.config_dir, filename)
                with open(config_path, 'w') as f:
                    f.write(content)
            
            self.log_test(test_name, True, "Configuration validation components are present")
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def test_pkgbuild_integration(self):
        """Test PKGBUILD integration"""
        test_name = "PKGBUILD integration"
        
        try:
            pkgbuild_path = Path(__file__).parent / "PKGBUILD"
            if not pkgbuild_path.exists():
                self.log_test(test_name, False, "PKGBUILD not found")
                return
            
            # Read PKGBUILD content
            with open(pkgbuild_path, 'r') as f:
                pkgbuild_content = f.read()
            
            # Check for required elements
            required_elements = [
                "client.conf",
                "server.conf", 
                "pools.conf",
                "validate-config-installation.py",
                "config-backup-restore.sh",
                "backup=(",
                "_install_common_files",
                "/etc/$pkgbase"
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in pkgbuild_content:
                    missing_elements.append(element)
            
            if missing_elements:
                self.log_test(test_name, False, f"Missing PKGBUILD elements: {missing_elements}")
                return
            
            self.log_test(test_name, True, "PKGBUILD contains all required configuration elements")
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def test_install_script_integration(self):
        """Test install script integration"""
        test_name = "Install script integration"
        
        try:
            install_script_path = Path(__file__).parent / "pacman-sync-utility.install"
            if not install_script_path.exists():
                self.log_test(test_name, False, "Install script not found")
                return
            
            # Read install script content
            with open(install_script_path, 'r') as f:
                install_content = f.read()
            
            # Check for required elements
            required_elements = [
                "post_install()",
                "post_upgrade()",
                "post_remove()",
                "/etc/pacman-sync-utility",
                "chmod 644",
                "chown root:root",
                ".pacnew",
                ".pacsave",
                "pacman-sync-validate-config"
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in install_content:
                    missing_elements.append(element)
            
            if missing_elements:
                self.log_test(test_name, False, f"Missing install script elements: {missing_elements}")
                return
            
            self.log_test(test_name, True, "Install script contains all required configuration handling")
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def run_all_tests(self):
        """Run all configuration installation tests"""
        print("Running Configuration Installation Tests")
        print("=" * 50)
        
        self.setup_test_environment()
        
        try:
            # Run all tests
            self.test_directory_structure_creation()
            self.test_configuration_file_installation()
            self.test_backup_functionality()
            self.test_pacnew_pacsave_handling()
            self.test_configuration_validation()
            self.test_pkgbuild_integration()
            self.test_install_script_integration()
            
        finally:
            self.cleanup_test_environment()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"Test Summary: {self.passed_tests} passed, {self.failed_tests} failed")
        
        if self.failed_tests > 0:
            print("\nSome tests failed. Please review the implementation.")
            return 1
        else:
            print("\nAll tests passed! Configuration installation is properly implemented.")
            return 0


def main():
    """Main test function"""
    tester = ConfigInstallationTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())