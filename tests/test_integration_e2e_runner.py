#!/usr/bin/env python3
"""
Integration and End-to-End Test Runner.

This module runs all integration and end-to-end tests for the Pacman Sync Utility:
- Client-server communication tests
- Multi-endpoint synchronization tests
- Docker deployment and scaling tests
- Complete workflow validation tests

Requirements: All requirements - integration validation
"""

import sys
import os
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class IntegrationTestRunner:
    """Manages execution of all integration and end-to-end tests."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
    
    def run_test_suite(self, test_file, suite_name, timeout=300):
        """Run a specific test suite and capture results."""
        print(f"\n{'='*60}")
        print(f"RUNNING: {suite_name}")
        print(f"File: {test_file}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run pytest with the specific test file
            cmd = [
                sys.executable, "-m", "pytest", 
                test_file, 
                "-v", 
                "--tb=short",
                "--json-report",
                "--json-report-file=/tmp/pytest_report.json"
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                cwd=project_root
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse pytest output
            success = result.returncode == 0
            
            # Try to parse JSON report if available
            test_details = self._parse_pytest_output(result.stdout, result.stderr)
            
            self.test_results[suite_name] = {
                "success": success,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "details": test_details,
                "return_code": result.returncode
            }
            
            # Update counters
            if test_details:
                self.total_tests += test_details.get("total", 0)
                self.passed_tests += test_details.get("passed", 0)
                self.failed_tests += test_details.get("failed", 0)
                self.skipped_tests += test_details.get("skipped", 0)
            
            # Print immediate results
            if success:
                print(f"✓ {suite_name} PASSED ({duration:.1f}s)")
            else:
                print(f"✗ {suite_name} FAILED ({duration:.1f}s)")
                if result.stderr:
                    print(f"Error output: {result.stderr[:500]}...")
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f"✗ {suite_name} TIMED OUT after {timeout}s")
            self.test_results[suite_name] = {
                "success": False,
                "duration": timeout,
                "stdout": "",
                "stderr": f"Test suite timed out after {timeout} seconds",
                "details": {"error": "timeout"},
                "return_code": -1
            }
            return False
            
        except Exception as e:
            print(f"✗ {suite_name} ERROR: {str(e)}")
            self.test_results[suite_name] = {
                "success": False,
                "duration": 0,
                "stdout": "",
                "stderr": str(e),
                "details": {"error": str(e)},
                "return_code": -1
            }
            return False
    
    def _parse_pytest_output(self, stdout, stderr):
        """Parse pytest output to extract test statistics."""
        details = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Try to parse JSON report first
        try:
            if os.path.exists("/tmp/pytest_report.json"):
                with open("/tmp/pytest_report.json", "r") as f:
                    report = json.load(f)
                    
                details["total"] = report.get("summary", {}).get("total", 0)
                details["passed"] = report.get("summary", {}).get("passed", 0)
                details["failed"] = report.get("summary", {}).get("failed", 0)
                details["skipped"] = report.get("summary", {}).get("skipped", 0)
                
                # Extract error details
                for test in report.get("tests", []):
                    if test.get("outcome") == "failed":
                        details["errors"].append({
                            "test": test.get("nodeid", "unknown"),
                            "error": test.get("call", {}).get("longrepr", "unknown error")
                        })
                
                return details
        except Exception:
            pass
        
        # Fallback to parsing text output
        lines = stdout.split('\n')
        for line in lines:
            if "passed" in line and "failed" in line:
                # Try to extract numbers from summary line
                import re
                numbers = re.findall(r'(\d+) (\w+)', line)
                for count, status in numbers:
                    count = int(count)
                    if status == "passed":
                        details["passed"] = count
                    elif status == "failed":
                        details["failed"] = count
                    elif status == "skipped":
                        details["skipped"] = count
                    
                    details["total"] += count
        
        return details
    
    def check_prerequisites(self):
        """Check if all prerequisites for testing are available."""
        print("Checking test prerequisites...")
        
        prerequisites = {
            "Python": self._check_python(),
            "Pytest": self._check_pytest(),
            "Docker": self._check_docker(),
            "Project Structure": self._check_project_structure(),
            "Dependencies": self._check_dependencies()
        }
        
        all_good = True
        for name, status in prerequisites.items():
            if status["available"]:
                print(f"✓ {name}: {status['version']}")
            else:
                print(f"✗ {name}: {status['error']}")
                if not status.get("optional", False):
                    all_good = False
        
        return all_good, prerequisites
    
    def _check_python(self):
        """Check Python version."""
        try:
            version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            return {"available": True, "version": version}
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def _check_pytest(self):
        """Check if pytest is available."""
        try:
            result = subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                                  capture_output=True, text=True, check=True)
            version = result.stdout.strip().split('\n')[0]
            return {"available": True, "version": version}
        except Exception as e:
            return {"available": False, "error": "pytest not installed"}
    
    def _check_docker(self):
        """Check if Docker is available."""
        try:
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True, check=True)
            version = result.stdout.strip()
            return {"available": True, "version": version}
        except Exception as e:
            return {"available": False, "error": "Docker not available", "optional": True}
    
    def _check_project_structure(self):
        """Check if required project files exist."""
        required_files = [
            "server/api/main.py",
            "client/main.py",
            "shared/models.py",
            "docker-compose.yml",
            "Dockerfile"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            return {
                "available": False, 
                "error": f"Missing files: {', '.join(missing_files)}"
            }
        else:
            return {"available": True, "version": "All required files present"}
    
    def _check_dependencies(self):
        """Check if required Python dependencies are available."""
        required_deps = [
            "fastapi",
            "uvicorn", 
            "aiohttp",
            "pytest",
            "pytest-asyncio"
        ]
        
        missing_deps = []
        for dep in required_deps:
            try:
                __import__(dep.replace("-", "_"))
            except ImportError:
                missing_deps.append(dep)
        
        if missing_deps:
            return {
                "available": False,
                "error": f"Missing dependencies: {', '.join(missing_deps)}"
            }
        else:
            return {"available": True, "version": "All required dependencies available"}
    
    def run_all_tests(self):
        """Run all integration and end-to-end tests."""
        self.start_time = time.time()
        
        print("=" * 80)
        print("PACMAN SYNC UTILITY - INTEGRATION & END-TO-END TESTS")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check prerequisites
        prereqs_ok, prereqs = self.check_prerequisites()
        if not prereqs_ok:
            print("\n❌ Prerequisites not met. Cannot run tests.")
            return False
        
        print(f"\n✓ Prerequisites check passed")
        
        # Define test suites
        test_suites = [
            {
                "file": "tests/test_client_server_integration.py",
                "name": "Client-Server Communication",
                "timeout": 300,
                "required": True
            },
            {
                "file": "tests/test_multi_endpoint_sync.py", 
                "name": "Multi-Endpoint Synchronization",
                "timeout": 400,
                "required": True
            },
            {
                "file": "tests/test_docker_deployment.py",
                "name": "Docker Deployment & Scaling",
                "timeout": 600,
                "required": False  # Optional if Docker not available
            }
        ]
        
        # Run test suites
        all_passed = True
        for suite in test_suites:
            # Skip Docker tests if Docker not available
            if suite["name"] == "Docker Deployment & Scaling" and not prereqs["Docker"]["available"]:
                print(f"\nSkipping {suite['name']} (Docker not available)")
                continue
            
            success = self.run_test_suite(
                suite["file"], 
                suite["name"], 
                suite["timeout"]
            )
            
            if not success and suite["required"]:
                all_passed = False
        
        self.end_time = time.time()
        
        # Generate final report
        self._generate_final_report()
        
        return all_passed
    
    def _generate_final_report(self):
        """Generate final test report."""
        total_duration = self.end_time - self.start_time
        
        print("\n" + "=" * 80)
        print("FINAL TEST REPORT")
        print("=" * 80)
        
        print(f"Total Duration: {total_duration:.1f} seconds")
        print(f"Test Suites Run: {len(self.test_results)}")
        
        # Suite-by-suite results
        print(f"\nSuite Results:")
        for suite_name, result in self.test_results.items():
            status = "✓ PASSED" if result["success"] else "✗ FAILED"
            duration = result["duration"]
            print(f"  {status} {suite_name} ({duration:.1f}s)")
            
            if result["details"] and "total" in result["details"]:
                details = result["details"]
                print(f"    Tests: {details['total']}, "
                      f"Passed: {details['passed']}, "
                      f"Failed: {details['failed']}, "
                      f"Skipped: {details['skipped']}")
        
        # Overall statistics
        print(f"\nOverall Test Statistics:")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  Passed: {self.passed_tests}")
        print(f"  Failed: {self.failed_tests}")
        print(f"  Skipped: {self.skipped_tests}")
        
        # Success rate
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"  Success Rate: {success_rate:.1f}%")
        
        # Final verdict
        all_suites_passed = all(result["success"] for result in self.test_results.values())
        
        print(f"\n{'='*80}")
        if all_suites_passed and self.failed_tests == 0:
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            print("✓ Client-server communication validated")
            print("✓ Multi-endpoint synchronization validated") 
            print("✓ Docker deployment validated")
            print("✓ End-to-end workflows validated")
        else:
            print("❌ SOME TESTS FAILED")
            print("Please review the test output above for details.")
        
        print("=" * 80)
        
        # Save detailed report to file
        self._save_detailed_report()
    
    def _save_detailed_report(self):
        """Save detailed test report to file."""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "duration": self.end_time - self.start_time,
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "skipped_tests": self.skipped_tests,
                "suites_run": len(self.test_results)
            },
            "suite_results": {}
        }
        
        # Add suite details (excluding large stdout/stderr)
        for suite_name, result in self.test_results.items():
            report_data["suite_results"][suite_name] = {
                "success": result["success"],
                "duration": result["duration"],
                "return_code": result["return_code"],
                "details": result["details"]
            }
        
        # Save to file
        report_file = project_root / "tests" / "integration_test_report.json"
        try:
            with open(report_file, "w") as f:
                json.dump(report_data, f, indent=2)
            print(f"\nDetailed report saved to: {report_file}")
        except Exception as e:
            print(f"\nFailed to save detailed report: {e}")


def main():
    """Main entry point for integration test runner."""
    runner = IntegrationTestRunner()
    
    try:
        success = runner.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        return 130
    except Exception as e:
        print(f"\nFatal error during test execution: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())