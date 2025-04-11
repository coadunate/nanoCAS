#!/bin/bash

# Test script for nanoCAS application
# This script tests the functionality of the nanoCAS application

echo "===== nanoCAS Application Test ====="
echo "Testing application components..."

# Create test directory
TEST_DIR="/tmp/nanocas_test"
mkdir -p $TEST_DIR

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Test 1: Check if required dependencies are installed
echo "Test 1: Checking dependencies..."

DEPENDENCIES=("python3" "pip3" "node" "npm")
MISSING_DEPS=()

for dep in "${DEPENDENCIES[@]}"; do
  if command_exists $dep; then
    echo "✅ $dep is installed"
  else
    echo "❌ $dep is not installed"
    MISSING_DEPS+=($dep)
  fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
  echo "⚠️ Some dependencies are missing. Please install them before proceeding."
else
  echo "✅ All basic dependencies are installed"
fi

# Test 2: Check if Docker is available (optional)
echo "Test 2: Checking Docker availability..."

if command_exists docker && command_exists docker-compose; then
  echo "✅ Docker and Docker Compose are installed"
  DOCKER_AVAILABLE=true
else
  echo "⚠️ Docker and/or Docker Compose are not installed"
  echo "  This is optional, as nanoCAS can run without Docker"
  DOCKER_AVAILABLE=false
fi

# Test 3: Check Python environment setup
echo "Test 3: Testing Python environment setup..."

# Create a temporary virtual environment
python3 -m venv $TEST_DIR/venv
source $TEST_DIR/venv/bin/activate

# Install requirements
if [ -f "server/requirements.txt" ]; then
  pip install -r server/requirements.txt > $TEST_DIR/pip_install.log 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully"
  else
    echo "❌ Failed to install Python dependencies"
    echo "  See $TEST_DIR/pip_install.log for details"
  fi
else
  echo "❌ requirements.txt not found"
fi

# Test 4: Check Node.js environment setup
echo "Test 4: Testing Node.js environment setup..."

if [ -f "frontend/package.json" ]; then
  # Just check if package.json is valid
  node -e "JSON.parse(require('fs').readFileSync('frontend/package.json'))" > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ package.json is valid"
  else
    echo "❌ package.json is invalid"
  fi
else
  echo "❌ package.json not found"
fi

# Test 5: Check server code
echo "Test 5: Testing server code..."

if [ -f "server/micas.py" ]; then
  # Syntax check
  python -m py_compile server/micas.py > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ Server code compiles successfully"
  else
    echo "❌ Server code has syntax errors"
  fi
else
  echo "❌ Server entry point (micas.py) not found"
fi

# Test 6: Check distributed computing setup
echo "Test 6: Testing distributed computing setup..."

if [ -f "server/app/main/utils/tasks.py" ]; then
  # Syntax check
  python -m py_compile server/app/main/utils/tasks.py > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ Distributed computing code compiles successfully"
  else
    echo "❌ Distributed computing code has syntax errors"
  fi
else
  echo "❌ Distributed computing module not found"
fi

# Test 7: Check setup scripts
echo "Test 7: Testing setup scripts..."

if [ -f "setup.sh" ] && [ -x "setup.sh" ]; then
  echo "✅ Bash setup script exists and is executable"
else
  echo "❌ Bash setup script is missing or not executable"
fi

if [ -f "setup.py" ]; then
  # Syntax check
  python -m py_compile setup.py > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ Python setup script compiles successfully"
  else
    echo "❌ Python setup script has syntax errors"
  fi
else
  echo "❌ Python setup script not found"
fi

# Test 8: Check Docker configuration
echo "Test 8: Testing Docker configuration..."

if [ -f "docker-compose.yml" ]; then
  if $DOCKER_AVAILABLE; then
    # Validate docker-compose file
    docker-compose config -q
    if [ $? -eq 0 ]; then
      echo "✅ docker-compose.yml is valid"
    else
      echo "❌ docker-compose.yml has errors"
    fi
  else
    echo "⚠️ Cannot validate docker-compose.yml (Docker not available)"
  fi
else
  echo "❌ docker-compose.yml not found"
fi

# Test 9: Check documentation
echo "Test 9: Testing documentation..."

if [ -f "README.md" ]; then
  # Check if README has minimum content
  README_SIZE=$(wc -c < README.md)
  if [ $README_SIZE -gt 1000 ]; then
    echo "✅ README.md exists and has substantial content"
  else
    echo "⚠️ README.md exists but may have insufficient content"
  fi
else
  echo "❌ README.md not found"
fi

# Clean up
deactivate
rm -rf $TEST_DIR

echo "===== Test Summary ====="
echo "The nanoCAS application has been tested for basic functionality."
echo "Please review any warnings or errors before deploying."
echo "For a complete test, deploy the application and verify all features."
