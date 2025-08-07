#!/usr/bin/env python3
"""
Unit tests for pacman interface with mocked operations.

Tests pacman integration functionality including package state detection,
repository information extraction, and package operations without requiring
actual pacman installation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from client.pacman_interface import (
    PacmanInterface, PackageInfo, RepositoryInfo, PacmanError
)
from shared.models import PackageState, SystemState, Repository, RepositoryPackage


class TestPackageInfo:
    """Test PackageInfo data class."""
    
    def test_package_info_creation(self):
        """Test creating PackageInfo object."""
        package_info = PackageInfo(
            name="test-package",
            version="1.0.0-1",
            repository="core",
            installed_size=1024,
            dependencies=["dep1", "dep2"],
            description="Test package description"
        )
        
        assert package_info.name == "test-package"
        assert package_info.version == "1.0.0-1"
        assert package_info.repository == "core"
        assert package_info.installed_size == 1024
        assert package_info.dependencies == ["dep1", "dep2"]
        assert package_info.description == "Test package description"
    
    def test_package_info_to_package_state(self):
        """Test conversion to PackageState."""
        package_info = PackageInfo(
            name="test-package",
            version="1.0.0-1",
            repository="core",
            installed_size=1024,
            dependencies=["dep1", "dep2"]
        )
        
        package_state = package_info.to_package_state()
        
        assert isinstance(package_state, PackageState)
        assert package_state.package_name == "test-package"
        assert package_state.version == "1.0.0-1"
        assert package_state.repository == "core"
        assert package_state.installed_size == 1024
        assert package_state.dependencies == ["dep1", "dep2"]


class TestRepositoryInfo:
    """Test RepositoryInfo data class."""
    
    def test_repository_info_creation(self):
        """Test creating RepositoryInfo object."""
        packages = [
            RepositoryPackage("pkg1", "1.0.0", "core", "x86_64"),
            RepositoryPackage("pkg2", "2.0.0", "core", "x86_64")
        ]
        
        repo_info = RepositoryInfo(
            name="core",
            url="https://mirror.example.com/core",
            packages=packages,
            architecture="x86_64"
        )
        
        assert repo_info.name == "core"
        assert repo_info.url == "https://mirror.example.com/core"
        assert len(repo_info.packages) == 2
        assert repo_info.architecture == "x86_64"
    
    def test_repository_info_to_repository(self):
        """Test conversion to Repository model."""
        packages = [
            RepositoryPackage("pkg1", "1.0.0", "core", "x86_64")
        ]
        
        repo_info = RepositoryInfo(
            name="core",
            url="https://mirror.example.com/core",
            packages=packages,
            architecture="x86_64"
        )
        
        repository = repo_info.to_repository("endpoint-1")
        
        assert isinstance(repository, Repository)
        assert repository.endpoint_id == "endpoint-1"
        assert repository.repo_name == "core"
        assert repository.repo_url == "https://mirror.example.com/core"
        assert len(repository.packages) == 1


class TestPacmanInterface:
    """Test PacmanInterface main class."""
    
    @pytest.fixture
    def pacman_interface(self):
        """Create PacmanInterface instance."""
        return PacmanInterface()
    
    @pytest.fixture
    def mock_subprocess_run(self):
        """Create mock subprocess.run function."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_get_installed_packages_success(self, pacman_interface, mock_subprocess_run):
        """Test successful retrieval of installed packages."""
        # Mock pacman output
        mock_output = """test-package 1.0.0-1
core/test-package 1.0.0-1 [installed]
    Test package description
    Depends On: dep1  dep2
    Installed Size: 1024.00 KiB

another-package 2.0.0-1
extra/another-package 2.0.0-1 [installed]
    Another test package
    Depends On: None
    Installed Size: 2048.00 KiB"""
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            packages = await pacman_interface.get_installed_packages()
        
        assert len(packages) == 2
        assert packages[0]["name"] == "test-package"
        assert packages[0]["version"] == "1.0.0-1"
        assert packages[0]["repository"] == "core"
        assert packages[0]["dependencies"] == ["dep1", "dep2"]
        
        assert packages[1]["name"] == "another-package"
        assert packages[1]["version"] == "2.0.0-1"
        assert packages[1]["repository"] == "extra"
        assert packages[1]["dependencies"] == []
    
    @pytest.mark.asyncio
    async def test_get_installed_packages_pacman_error(self, pacman_interface, mock_subprocess_run):
        """Test get_installed_packages with pacman command error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error: failed to initialize alpm library"
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            with pytest.raises(PacmanError, match="failed to initialize"):
                await pacman_interface.get_installed_packages()
    
    @pytest.mark.asyncio
    async def test_get_repository_info_success(self, pacman_interface, mock_subprocess_run):
        """Test successful repository information retrieval."""
        # Mock pacman.conf content
        mock_conf_content = """[options]
Architecture = x86_64

[core]
Server = https://mirror.example.com/core/$arch/$repo

[extra]
Server = https://mirror.example.com/extra/$arch/$repo"""
        
        # Mock repository package lists
        mock_core_output = """core/package1 1.0.0-1
    Core package 1
core/package2 2.0.0-1
    Core package 2"""
        
        mock_extra_output = """extra/package3 3.0.0-1
    Extra package 3"""
        
        def mock_subprocess_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            
            if "pacman.conf" in str(args):
                mock_result.stdout = mock_conf_content
            elif "core" in str(args):
                mock_result.stdout = mock_core_output
            elif "extra" in str(args):
                mock_result.stdout = mock_extra_output
            else:
                mock_result.stdout = ""
            
            mock_result.stderr = ""
            return mock_result
        
        mock_subprocess_run.side_effect = mock_subprocess_side_effect
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            with patch('builtins.open', mock_open_multiple_files({
                '/etc/pacman.conf': mock_conf_content
            })):
                repositories = await pacman_interface.get_repository_info()
        
        assert len(repositories) == 2
        
        # Check core repository
        core_repo = next(repo for repo in repositories if repo["repo_name"] == "core")
        assert core_repo["repo_url"] == "https://mirror.example.com/core/$arch/$repo"
        assert len(core_repo["packages"]) == 2
        
        # Check extra repository
        extra_repo = next(repo for repo in repositories if repo["repo_name"] == "extra")
        assert extra_repo["repo_url"] == "https://mirror.example.com/extra/$arch/$repo"
        assert len(extra_repo["packages"]) == 1
    
    @pytest.mark.asyncio
    async def test_install_packages_success(self, pacman_interface, mock_subprocess_run):
        """Test successful package installation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "resolving dependencies...\npackages installed successfully"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            result = await pacman_interface.install_packages(["package1", "package2"])
        
        assert result == True
        
        # Verify correct command was called
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0]
        assert "pacman" in call_args[0]
        assert "-S" in call_args
        assert "package1" in call_args
        assert "package2" in call_args
    
    @pytest.mark.asyncio
    async def test_install_packages_failure(self, pacman_interface, mock_subprocess_run):
        """Test package installation failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error: target not found: nonexistent-package"
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            with pytest.raises(PacmanError, match="target not found"):
                await pacman_interface.install_packages(["nonexistent-package"])
    
    @pytest.mark.asyncio
    async def test_remove_packages_success(self, pacman_interface, mock_subprocess_run):
        """Test successful package removal."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "packages removed successfully"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            result = await pacman_interface.remove_packages(["package1", "package2"])
        
        assert result == True
        
        # Verify correct command was called
        call_args = mock_subprocess_run.call_args[0]
        assert "pacman" in call_args[0]
        assert "-R" in call_args
        assert "package1" in call_args
        assert "package2" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_packages_not_installed(self, pacman_interface, mock_subprocess_run):
        """Test package removal when package is not installed."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error: target not found: not-installed-package"
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            with pytest.raises(PacmanError, match="target not found"):
                await pacman_interface.remove_packages(["not-installed-package"])
    
    @pytest.mark.asyncio
    async def test_update_packages_success(self, pacman_interface, mock_subprocess_run):
        """Test successful package update."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "packages updated successfully"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            result = await pacman_interface.update_packages(["package1", "package2"])
        
        assert result == True
        
        # Verify correct command was called
        call_args = mock_subprocess_run.call_args[0]
        assert "pacman" in call_args[0]
        assert "-S" in call_args  # Update uses -S with package names
        assert "package1" in call_args
        assert "package2" in call_args
    
    @pytest.mark.asyncio
    async def test_sync_repositories_success(self, pacman_interface, mock_subprocess_run):
        """Test successful repository synchronization."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "synchronizing package databases..."
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            result = await pacman_interface.sync_repositories()
        
        assert result == True
        
        # Verify correct command was called
        call_args = mock_subprocess_run.call_args[0]
        assert "pacman" in call_args[0]
        assert "-Sy" in call_args
    
    @pytest.mark.asyncio
    async def test_sync_repositories_network_error(self, pacman_interface, mock_subprocess_run):
        """Test repository sync with network error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error: failed retrieving file 'core.db' from mirror"
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            with pytest.raises(PacmanError, match="failed retrieving file"):
                await pacman_interface.sync_repositories()
    
    @pytest.mark.asyncio
    async def test_get_system_state_success(self, pacman_interface):
        """Test successful system state retrieval."""
        # Mock installed packages
        mock_packages = [
            {
                "name": "package1",
                "version": "1.0.0-1",
                "repository": "core",
                "installed_size": 1024,
                "dependencies": ["dep1"]
            },
            {
                "name": "package2", 
                "version": "2.0.0-1",
                "repository": "extra",
                "installed_size": 2048,
                "dependencies": []
            }
        ]
        
        with patch.object(pacman_interface, 'get_installed_packages', return_value=mock_packages):
            with patch.object(pacman_interface, 'get_pacman_version', return_value="6.0.1"):
                with patch.object(pacman_interface, 'get_architecture', return_value="x86_64"):
                    system_state = await pacman_interface.get_system_state("endpoint-1")
        
        assert isinstance(system_state, SystemState)
        assert system_state.endpoint_id == "endpoint-1"
        assert len(system_state.packages) == 2
        assert system_state.pacman_version == "6.0.1"
        assert system_state.architecture == "x86_64"
        
        # Check package conversion
        assert system_state.packages[0].package_name == "package1"
        assert system_state.packages[0].version == "1.0.0-1"
        assert system_state.packages[1].package_name == "package2"
        assert system_state.packages[1].version == "2.0.0-1"
    
    @pytest.mark.asyncio
    async def test_get_pacman_version_success(self, pacman_interface, mock_subprocess_run):
        """Test successful pacman version retrieval."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Pacman v6.0.1 - libalpm v13.0.1"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            version = await pacman_interface.get_pacman_version()
        
        assert version == "6.0.1"
    
    @pytest.mark.asyncio
    async def test_get_architecture_success(self, pacman_interface, mock_subprocess_run):
        """Test successful architecture retrieval."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "x86_64"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        with patch('client.pacman_interface.asyncio.create_subprocess_exec', mock_subprocess_run):
            architecture = await pacman_interface.get_architecture()
        
        assert architecture == "x86_64"
    
    def test_parse_package_info_success(self, pacman_interface):
        """Test successful package info parsing."""
        package_output = """test-package 1.0.0-1
core/test-package 1.0.0-1 [installed]
    Test package description
    Depends On: dep1  dep2
    Installed Size: 1024.00 KiB"""
        
        package_info = pacman_interface._parse_package_info(package_output)
        
        assert package_info.name == "test-package"
        assert package_info.version == "1.0.0-1"
        assert package_info.repository == "core"
        assert package_info.dependencies == ["dep1", "dep2"]
        assert package_info.installed_size == 1024
        assert "Test package description" in package_info.description
    
    def test_parse_package_info_no_dependencies(self, pacman_interface):
        """Test package info parsing with no dependencies."""
        package_output = """standalone-package 1.0.0-1
core/standalone-package 1.0.0-1 [installed]
    Standalone package
    Depends On: None
    Installed Size: 512.00 KiB"""
        
        package_info = pacman_interface._parse_package_info(package_output)
        
        assert package_info.name == "standalone-package"
        assert package_info.dependencies == []
    
    def test_parse_repository_config_success(self, pacman_interface):
        """Test successful repository configuration parsing."""
        config_content = """[options]
Architecture = x86_64

[core]
Server = https://mirror1.example.com/core/$arch/$repo
Server = https://mirror2.example.com/core/$arch/$repo

[extra]
Server = https://mirror.example.com/extra/$arch/$repo

[community]
# Commented out
# Server = https://mirror.example.com/community/$arch/$repo"""
        
        repositories = pacman_interface._parse_repository_config(config_content)
        
        assert len(repositories) == 2  # core and extra (community is commented)
        
        core_repo = next(repo for repo in repositories if repo["name"] == "core")
        assert len(core_repo["servers"]) == 2
        assert "mirror1.example.com" in core_repo["servers"][0]
        assert "mirror2.example.com" in core_repo["servers"][1]
        
        extra_repo = next(repo for repo in repositories if repo["name"] == "extra")
        assert len(extra_repo["servers"]) == 1
        assert "mirror.example.com" in extra_repo["servers"][0]
    
    def test_parse_size_string_success(self, pacman_interface):
        """Test successful size string parsing."""
        test_cases = [
            ("1024.00 KiB", 1024),
            ("2.50 MiB", 2621),  # 2.5 * 1024
            ("1.00 GiB", 1048576),  # 1 * 1024 * 1024
            ("512 B", 0),  # Less than 1 KiB
            ("invalid", 0)  # Invalid format
        ]
        
        for size_string, expected_kib in test_cases:
            result = pacman_interface._parse_size_string(size_string)
            assert result == expected_kib
    
    def test_validate_package_names_success(self, pacman_interface):
        """Test package name validation."""
        valid_names = ["package1", "package-with-dashes", "package_with_underscores"]
        
        # Should not raise exception
        pacman_interface._validate_package_names(valid_names)
    
    def test_validate_package_names_invalid(self, pacman_interface):
        """Test package name validation with invalid names."""
        invalid_names = ["package with spaces", "package;with;semicolons", ""]
        
        with pytest.raises(ValueError, match="Invalid package name"):
            pacman_interface._validate_package_names(invalid_names)
    
    def test_validate_package_names_empty_list(self, pacman_interface):
        """Test package name validation with empty list."""
        with pytest.raises(ValueError, match="No packages specified"):
            pacman_interface._validate_package_names([])


def mock_open_multiple_files(files_dict):
    """Helper function to mock opening multiple files."""
    def mock_open_func(filename, *args, **kwargs):
        if filename in files_dict:
            return MagicMock(read=lambda: files_dict[filename])
        else:
            raise FileNotFoundError(f"No such file: {filename}")
    
    return mock_open_func


class TestPacmanError:
    """Test PacmanError exception class."""
    
    def test_pacman_error_creation(self):
        """Test creating PacmanError."""
        error = PacmanError("Test error message", 1, "stdout", "stderr")
        
        assert str(error) == "Test error message"
        assert error.return_code == 1
        assert error.stdout == "stdout"
        assert error.stderr == "stderr"
    
    def test_pacman_error_minimal(self):
        """Test creating PacmanError with minimal parameters."""
        error = PacmanError("Test error")
        
        assert str(error) == "Test error"
        assert error.return_code is None
        assert error.stdout is None
        assert error.stderr is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])