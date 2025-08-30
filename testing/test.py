#!/usr/bin/env python3
"""Odoo Module Testing Suite"""
import subprocess
import sys
import os
import re

MODULE = "tada_admin"

def test():
    """Test module installation"""
    # Start postgres if not running
    subprocess.run("docker rm -f odoo_pg 2>/dev/null; docker run -d --name odoo_pg -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo postgres:15", shell=True)
    
    # Test module installation  
    script_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(os.path.dirname(script_dir), MODULE)
    print(f"Module path: {module_path}")
    
    # Build custom image with dependencies
    build_result = subprocess.run([
        "docker", "build", "-t", "odoo-with-deps", 
        os.path.dirname(__file__)
    ], capture_output=True, text=True)
    
    if build_result.returncode != 0:
        print(f"Failed to build Docker image: {build_result.stderr}")
        return False
    
    result = subprocess.run([
        "docker", "run", "--rm", "--link", "odoo_pg:db",
        "-v", f"{module_path}:/mnt/extra-addons/{MODULE}:ro",
        "odoo-with-deps",
        "--database=test", 
        "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons",
        f"--init={MODULE}", 
        "--stop-after-init", 
        "--no-http",
        "--log-level=warn"
    ], capture_output=True, text=True)
    
    # Save complete logs to file
    log_file = os.path.join(os.path.dirname(__file__), 'test.log')
    
    with open(log_file, 'w') as f:
        f.write("=== ODOO MODULE TEST LOG (Complete) ===\n")
        f.write(f"Exit code: {result.returncode}\n")
        f.write(f"Module path: {module_path}\n\n")
        f.write("=== STDOUT ===\n")
        f.write(result.stdout)
        f.write("\n\n=== STDERR ===\n")
        f.write(result.stderr)
    
    success = result.returncode == 0 and "ERROR" not in result.stderr and "CRITICAL" not in result.stderr
    
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"Log saved to: {log_file}")
    
    if not success and "ImportError" in result.stderr:
        error_match = re.search(r'ImportError: (.+)', result.stderr)
        if error_match:
            print(f"Issue Found: {error_match.group(1)}")
    elif not success:
        print("Error details:")
        print(result.stderr[-500:])
    
    return success

def run_unit_tests():
    """Run Odoo internal unit tests for the module"""
    print("Running Odoo internal unit tests...")
    
    # Start postgres if not running
    subprocess.run("docker rm -f odoo_pg 2>/dev/null; docker run -d --name odoo_pg -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo postgres:15", shell=True)
    
    # Get module path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(os.path.dirname(script_dir), MODULE)
    
    # Run Odoo with test-enable flag
    # Build custom image with dependencies
    build_result = subprocess.run([
        "docker", "build", "-t", "odoo-with-deps", 
        os.path.dirname(__file__)
    ], capture_output=True, text=True)
    
    if build_result.returncode != 0:
        print(f"Failed to build Docker image: {build_result.stderr}")
        return False
    
    result = subprocess.run([
        "docker", "run", "--rm", "--link", "odoo_pg:db",
        "-v", f"{module_path}:/mnt/extra-addons/{MODULE}:ro",
        "odoo-with-deps",
        "--database=test_unit", 
        "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons",
        f"--init={MODULE}", 
        "--test-enable",  # Enable unit tests
        "--stop-after-init", 
        "--no-http",
        "--log-level=test"  # Focus on test output
    ], capture_output=True, text=True)
    
    # Save complete logs to file
    log_file = os.path.join(os.path.dirname(__file__), 'test_unit.log')
    
    with open(log_file, 'w') as f:
        f.write("=== ODOO UNIT TEST LOG (Complete) ===\n")
        f.write(f"Exit code: {result.returncode}\n")
        f.write(f"Module path: {module_path}\n\n")
        f.write("=== STDOUT ===\n")
        f.write(result.stdout)
        f.write("\n\n=== STDERR ===\n")
        f.write(result.stderr)
    
    # Check for test failures
    success = result.returncode == 0
    test_failures = re.findall(r'(ERROR|FAIL): (\w+)', result.stdout)
    
    print(f"Unit Test Result: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"Log saved to: {log_file}")
    
    if test_failures:
        print(f"Failed tests: {len(test_failures)}")
        for failure_type, test_name in test_failures[:5]:  # Show first 5 failures
            print(f"  - {failure_type}: {test_name}")
        if len(test_failures) > 5:
            print(f"  ... and {len(test_failures) - 5} more failures")
    
    return success

def run_module_tests():
    """Run tests only for our specific module"""
    print(f"Running tests only for {MODULE} module...")
    
    # Start postgres if not running
    subprocess.run("docker rm -f odoo_pg 2>/dev/null; docker run -d --name odoo_pg -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo postgres:15", shell=True)
    
    # Get module path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(os.path.dirname(script_dir), MODULE)
    
    # Run Odoo with test-enable flag and test-tags to run only our module tests
    # Build custom image with dependencies
    build_result = subprocess.run([
        "docker", "build", "-t", "odoo-with-deps", 
        os.path.dirname(__file__)
    ], capture_output=True, text=True)
    
    if build_result.returncode != 0:
        print(f"Failed to build Docker image: {build_result.stderr}")
        return False
    
    result = subprocess.run([
        "docker", "run", "--rm", "--link", "odoo_pg:db",
        "-v", f"{module_path}:/mnt/extra-addons/{MODULE}:ro",
        "odoo-with-deps",
        "--database=test_module", 
        "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons",
        f"--init={MODULE}", 
        "--test-enable",  # Enable unit tests
        f"--test-tags={MODULE}",  # Run only tests for our module
        "--stop-after-init", 
        "--no-http",
        "--log-level=test"  # Focus on test output
    ], capture_output=True, text=True)
    
    # Save logs to file
    log_file = os.path.join(os.path.dirname(__file__), 'test_module.log')
    
    # Get last 300 lines from stdout and stderr
    stdout_lines = result.stdout.split('\n')[-200:] if result.stdout else []
    stderr_lines = result.stderr.split('\n')[-200:] if result.stderr else []
    
    with open(log_file, 'w') as f:
        f.write("=== TADA B2B2C MODULE TEST LOG ===\n")
        f.write(f"Exit code: {result.returncode}\n")
        f.write(f"Module path: {module_path}\n\n")
        f.write("=== STDOUT ===\n")
        f.write('\n'.join(stdout_lines))
        f.write("\n\n=== STDERR ===\n")
        f.write('\n'.join(stderr_lines))
    
    # Check for test failures specific to our module
    success = result.returncode == 0
    test_failures = re.findall(rf'(ERROR|FAIL): ({MODULE}\.\w+)', result.stdout)
    
    print(f"Module Test Result: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"Log saved to: {log_file}")
    
    if test_failures:
        print(f"Failed tests: {len(test_failures)}")
        for failure_type, test_name in test_failures[:5]:  # Show first 5 failures
            print(f"  - {failure_type}: {test_name}")
        if len(test_failures) > 5:
            print(f"  ... and {len(test_failures) - 5} more failures")
    else:
        # Check if any tests were run
        if "No tests found" in result.stdout or "No tests found" in result.stderr:
            print(f"No tests found for the {MODULE} module.")
    
    return success

def run_all_tests():
    """Run both installation and unit tests"""
    print("=== Running Module Installation Test ===")
    install_success = test()
    print("\n=== Running Unit Tests ===")
    unit_success = run_unit_tests()
    
    print("\n=== Test Summary ===")
    print(f"Installation Test: {'✅ PASS' if install_success else '❌ FAIL'}")
    print(f"Unit Tests: {'✅ PASS' if unit_success else '❌ FAIL'}")
    
    return install_success and unit_success

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Odoo module tests')
    parser.add_argument('--test-type', choices=['install', 'unit', 'all'], 
                        default='all', help='Type of test to run')
    args = parser.parse_args()
    
    success = False
    if args.test_type == 'install':
        print("Running installation test only...")
        success = test()
    elif args.test_type == 'unit':
        print("Running unit tests only...")
        success = run_module_tests()
    else:  # 'all'
        print("Running all tests...")
        success = test()
    
    exit(0 if success else 1)