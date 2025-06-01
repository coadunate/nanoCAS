#!/bin/bash

# nanoCAS Platform Detection and Setup Script
# This script detects the platform and sets up the appropriate environment for nanoCAS

# Function to display help message
show_help() {
    echo "nanoCAS Setup Script"
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help                 Show this help message"
    echo "  -e, --env [ENV]            Environment type: development, production (default: development)"
    echo "  -d, --distributed          Enable distributed computing mode"
    echo "  -s, --slurm                Configure for SLURM cluster environment"
    echo "  -p, --port [PORT]          Specify port for the backend server (default: 5007)"
    echo "  -f, --frontend-port [PORT] Specify port for the frontend server (default: 3000)"
    echo "  --no-docker                Skip Docker setup and use local installation"
    echo ""
    echo "Example:"
    echo "  ./setup.sh --env production --distributed"
}

# Default values
ENV="development"
DISTRIBUTED=false
SLURM=false
BACKEND_PORT=5007
FRONTEND_PORT=3000
USE_DOCKER=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            show_help
            exit 0
            ;;
        -e|--env)
            ENV="$2"
            shift
            shift
            ;;
        -d|--distributed)
            DISTRIBUTED=true
            shift
            ;;
        -s|--slurm)
            SLURM=true
            shift
            ;;
        -p|--port)
            BACKEND_PORT="$2"
            shift
            shift
            ;;
        -f|--frontend-port)
            FRONTEND_PORT="$2"
            shift
            shift
            ;;
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$ID
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
    echo "Detected OS: $OS"
    if [ "$OS" == "linux" ]; then
        echo "Linux distribution: $DISTRO"
    fi
}

# Check if Docker is available
check_docker() {
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        echo "Docker and Docker Compose are installed"
        return 0
    else
        echo "Docker and/or Docker Compose are not installed"
        return 1
    fi
}

# Check if Conda is available
check_conda() {
    if command -v conda &> /dev/null; then
        echo "Conda is installed"
        return 0
    else
        echo "Conda is not installed"
        return 1
    fi
}

# Check if SLURM is available
check_slurm() {
    if command -v sinfo &> /dev/null; then
        echo "SLURM is installed"
        return 0
    else
        echo "SLURM is not installed"
        return 1
    fi
}

# Setup Docker environment
setup_docker() {
    echo "Setting up Docker environment..."
    
    # Create .env file for docker-compose
    cat > .env << EOF
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
ENV=$ENV
EOF

    if [ "$DISTRIBUTED" = true ]; then
        echo "ENABLE_DISTRIBUTED=true" >> .env
    else
        echo "ENABLE_DISTRIBUTED=false" >> .env
    fi

    # Optional Twilio configuration
    if [ -n "$TWILIO_ACCOUNT_SID" ] && [ -n "$TWILIO_AUTH_TOKEN" ] && [ -n "$TWILIO_PHONE_NUMBER" ] && [ -n "$ALERT_RECIPIENT_PHONE" ]; then
        cat >> .env << EOF
TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN
TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER
ALERT_RECIPIENT_PHONE=$ALERT_RECIPIENT_PHONE
EOF
    fi

    # Start the containers
    if [ "$ENV" == "production" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    else
        docker-compose up -d
    fi
    
    echo "Docker setup complete. Services are running."
    echo "Frontend: http://localhost:$FRONTEND_PORT"
    echo "Backend: http://localhost:$BACKEND_PORT"
}

# Setup Conda environment
setup_conda() {
    echo "Setting up Conda environment..."
    
    # Create Conda environment
    conda env create -f environment.yml
    
    echo "Conda environment 'nanoCAS' created."
    echo "To activate the environment, run: conda activate nanoCAS"
    
    # Create .env file for local setup
    cat > .env << EOF
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
ENV=$ENV
EOF

    if [ "$DISTRIBUTED" = true ]; then
        echo "ENABLE_DISTRIBUTED=true" >> .env
    else
        echo "ENABLE_DISTRIBUTED=false" >> .env
    fi

    # Optional Twilio configuration
    if [ -n "$TWILIO_ACCOUNT_SID" ] && [ -n "$TWILIO_AUTH_TOKEN" ] && [ -n "$TWILIO_PHONE_NUMBER" ] && [ -n "$ALERT_RECIPIENT_PHONE" ]; then
        cat >> .env << EOF
TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN
TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER
ALERT_RECIPIENT_PHONE=$ALERT_RECIPIENT_PHONE
EOF
    fi
    
    echo "Local setup complete."
    echo "To start the backend server: cd server && python nanocas.py"
    echo "To start the frontend server: cd frontend && npm start"
}

# Setup for SLURM environment
setup_slurm() {
    echo "Setting up for SLURM environment..."
    
    # Create SLURM job submission script
    cat > slurm_submit.sh << EOF
#!/bin/bash
#SBATCH --job-name=nanoCAS
#SBATCH --output=nanoCAS_%j.log
#SBATCH --error=nanoCAS_%j.err
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# Load necessary modules
module load python/3.10
module load samtools
module load minimap2

# Activate Conda environment if using Conda
if command -v conda &> /dev/null; then
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate nanoCAS
fi

# Set environment variables
export FLASK_APP=nanocas.py
export FLASK_ENV=$ENV
export PORT=$BACKEND_PORT

# Start the server
cd server
python nanocas.py
EOF

    chmod +x slurm_submit.sh
    
    echo "SLURM setup complete."
    echo "To submit the job to SLURM: sbatch slurm_submit.sh"
}

# Setup for Windows
setup_windows() {
    echo "Setting up for Windows environment..."
    
    # Create batch file for Windows
    cat > setup_windows.bat << EOF
@echo off
echo Setting up nanoCAS on Windows...

REM Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH
    exit /b 1
)

REM Check if Node.js is installed
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Node.js is not installed or not in PATH
    exit /b 1
)

REM Create Python virtual environment
python -m venv venv
call venv\Scripts\activate.bat
pip install -r server\requirements.txt

REM Install frontend dependencies
cd frontend
npm install
cd ..

REM Create .env file
echo BACKEND_PORT=$BACKEND_PORT > .env
echo FRONTEND_PORT=$FRONTEND_PORT >> .env
echo ENV=$ENV >> .env
echo ENABLE_DISTRIBUTED=$DISTRIBUTED >> .env

echo Setup complete.
echo To start the backend server: call venv\Scripts\activate.bat ^& cd server ^& python nanocas.py
echo To start the frontend server: cd frontend ^& npm start
EOF

    echo "Windows setup script created: setup_windows.bat"
}

# Main execution
echo "nanoCAS Setup Script"
echo "===================="

# Detect the operating system
detect_os

# Create necessary directories
mkdir -p ~/.nanocas

# Proceed with setup based on environment
if [ "$USE_DOCKER" = true ] && check_docker; then
    setup_docker
elif check_conda; then
    setup_conda
else
    echo "Neither Docker nor Conda is available. Installing dependencies directly..."
    
    if [ "$OS" == "linux" ]; then
        if [ "$DISTRO" == "ubuntu" ] || [ "$DISTRO" == "debian" ]; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv nodejs npm samtools minimap2
        elif [ "$DISTRO" == "fedora" ] || [ "$DISTRO" == "centos" ] || [ "$DISTRO" == "rhel" ]; then
            sudo dnf install -y python3 python3-pip nodejs npm samtools minimap2
        else
            echo "Unsupported Linux distribution. Please install dependencies manually."
        fi
    elif [ "$OS" == "macos" ]; then
        if command -v brew &> /dev/null; then
            brew install python node samtools minimap2
        else
            echo "Homebrew not found. Please install dependencies manually."
        fi
    elif [ "$OS" == "windows" ]; then
        setup_windows
        exit 0
    else
        echo "Unsupported operating system. Please install dependencies manually."
        exit 1
    fi
    
    # Create Python virtual environment
    python3 -m venv venv
    source venv/bin/activate
    pip install -r server/requirements.txt
    
    # Install frontend dependencies
    cd frontend
    npm install
    cd ..
    
    # Create .env file
    cat > .env << EOF
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
ENV=$ENV
EOF

    if [ "$DISTRIBUTED" = true ]; then
        echo "ENABLE_DISTRIBUTED=true" >> .env
    else
        echo "ENABLE_DISTRIBUTED=false" >> .env
    fi
    
    echo "Local setup complete."
    echo "To start the backend server: source venv/bin/activate && cd server && python nanocas.py"
    echo "To start the frontend server: cd frontend && npm start"
fi

# Setup for SLURM if requested
if [ "$SLURM" = true ]; then
    if check_slurm; then
        setup_slurm
    else
        echo "SLURM is not available on this system. Skipping SLURM setup."
    fi
fi

echo "nanoCAS setup completed successfully!"
