#!/usr/bin/env python3
"""
nanoCAS Unified Setup Script

This script provides a unified setup process for nanoCAS across different platforms
and environments. It handles dependency installation, environment configuration,
and application deployment.

Usage:
    python setup.py [options]

Options:
    --help, -h              Show this help message
    --env ENV               Set environment (development, production)
    --distributed           Enable distributed computing mode
    --slurm                 Configure for SLURM cluster environment
    --backend-port PORT     Specify backend server port (default: 5007)
    --frontend-port PORT    Specify frontend server port (default: 3000)
    --no-docker             Skip Docker setup and use local installation
    --install-deps          Install system dependencies
    --setup-redis           Setup Redis for distributed computing
    --setup-celery          Setup Celery for distributed computing
"""

import os
import sys
import platform
import subprocess
import argparse
import shutil
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('nanocas_setup.log')
    ]
)
logger = logging.getLogger('nanocas_setup')

# Default configuration
DEFAULT_CONFIG = {
    'env': 'development',
    'distributed': False,
    'slurm': False,
    'backend_port': 5007,
    'frontend_port': 3000,
    'use_docker': True,
    'install_deps': False,
    'setup_redis': False,
    'setup_celery': False
}

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='nanoCAS Setup Script')
    parser.add_argument('--env', choices=['development', 'production'], 
                        default='development', help='Environment type')
    parser.add_argument('--distributed', action='store_true', 
                        help='Enable distributed computing mode')
    parser.add_argument('--slurm', action='store_true', 
                        help='Configure for SLURM cluster environment')
    parser.add_argument('--backend-port', type=int, default=5007, 
                        help='Backend server port')
    parser.add_argument('--frontend-port', type=int, default=3000, 
                        help='Frontend server port')
    parser.add_argument('--no-docker', action='store_true', 
                        help='Skip Docker setup and use local installation')
    parser.add_argument('--install-deps', action='store_true', 
                        help='Install system dependencies')
    parser.add_argument('--setup-redis', action='store_true', 
                        help='Setup Redis for distributed computing')
    parser.add_argument('--setup-celery', action='store_true', 
                        help='Setup Celery for distributed computing')
    
    args = parser.parse_args()
    
    config = DEFAULT_CONFIG.copy()
    config.update({
        'env': args.env,
        'distributed': args.distributed,
        'slurm': args.slurm,
        'backend_port': args.backend_port,
        'frontend_port': args.frontend_port,
        'use_docker': not args.no_docker,
        'install_deps': args.install_deps,
        'setup_redis': args.setup_redis,
        'setup_celery': args.setup_celery
    })
    
    # If distributed is enabled, automatically setup Redis and Celery
    if config['distributed']:
        config['setup_redis'] = True
        config['setup_celery'] = True
    
    return config

def detect_platform():
    """Detect the operating system and platform details."""
    system = platform.system().lower()
    
    if system == 'linux':
        # Detect Linux distribution
        try:
            import distro
            distribution = distro.id()
        except ImportError:
            try:
                with open('/etc/os-release') as f:
                    os_release = {}
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            os_release[key] = value.strip('"')
                distribution = os_release.get('ID', 'unknown')
            except:
                distribution = 'unknown'
        
        # Check for SLURM
        has_slurm = shutil.which('sinfo') is not None
        
        return {
            'system': 'linux',
            'distribution': distribution,
            'has_slurm': has_slurm
        }
    
    elif system == 'darwin':
        # Detect macOS version
        mac_version = platform.mac_ver()[0]
        
        # Check for Homebrew
        has_homebrew = shutil.which('brew') is not None
        
        return {
            'system': 'macos',
            'version': mac_version,
            'has_homebrew': has_homebrew
        }
    
    elif system == 'windows':
        # Detect Windows version
        win_version = platform.version()
        
        # Check for WSL
        has_wsl = False
        try:
            with open('/proc/version') as f:
                if 'microsoft' in f.read().lower():
                    has_wsl = True
        except:
            pass
        
        return {
            'system': 'windows',
            'version': win_version,
            'has_wsl': has_wsl
        }
    
    else:
        return {
            'system': 'unknown',
            'version': platform.version()
        }

def check_dependencies():
    """Check if required dependencies are installed."""
    dependencies = {
        'python': shutil.which('python3') or shutil.which('python'),
        'pip': shutil.which('pip3') or shutil.which('pip'),
        'node': shutil.which('node'),
        'npm': shutil.which('npm'),
        'docker': shutil.which('docker'),
        'docker-compose': shutil.which('docker-compose'),
        'conda': shutil.which('conda'),
        'samtools': shutil.which('samtools'),
        'minimap2': shutil.which('minimap2'),
        'redis-server': shutil.which('redis-server'),
        'celery': shutil.which('celery')
    }
    
    return dependencies

def install_dependencies(platform_info, config):
    """Install required dependencies based on the platform."""
    logger.info("Installing dependencies...")
    
    if platform_info['system'] == 'linux':
        if platform_info['distribution'] in ['ubuntu', 'debian']:
            try:
                subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                subprocess.run([
                    'sudo', 'apt-get', 'install', '-y',
                    'python3', 'python3-pip', 'python3-venv',
                    'nodejs', 'npm',
                    'samtools', 'minimap2'
                ], check=True)
                
                if config['setup_redis']:
                    subprocess.run([
                        'sudo', 'apt-get', 'install', '-y', 'redis-server'
                    ], check=True)
                    subprocess.run(['sudo', 'systemctl', 'enable', 'redis-server'], check=True)
                    subprocess.run(['sudo', 'systemctl', 'start', 'redis-server'], check=True)
                
                logger.info("Dependencies installed successfully on Ubuntu/Debian")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing dependencies: {e}")
                return False
        
        elif platform_info['distribution'] in ['fedora', 'centos', 'rhel']:
            try:
                subprocess.run(['sudo', 'dnf', 'install', '-y',
                               'python3', 'python3-pip',
                               'nodejs', 'npm',
                               'samtools', 'minimap2'], check=True)
                
                if config['setup_redis']:
                    subprocess.run(['sudo', 'dnf', 'install', '-y', 'redis'], check=True)
                    subprocess.run(['sudo', 'systemctl', 'enable', 'redis'], check=True)
                    subprocess.run(['sudo', 'systemctl', 'start', 'redis'], check=True)
                
                logger.info("Dependencies installed successfully on Fedora/CentOS/RHEL")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing dependencies: {e}")
                return False
        
        else:
            logger.warning(f"Unsupported Linux distribution: {platform_info['distribution']}")
            logger.warning("Please install dependencies manually")
            return False
    
    elif platform_info['system'] == 'macos':
        if platform_info['has_homebrew']:
            try:
                subprocess.run(['brew', 'install', 'python', 'node', 'samtools', 'minimap2'], check=True)
                
                if config['setup_redis']:
                    subprocess.run(['brew', 'install', 'redis'], check=True)
                    subprocess.run(['brew', 'services', 'start', 'redis'], check=True)
                
                logger.info("Dependencies installed successfully on macOS")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing dependencies: {e}")
                return False
        else:
            logger.warning("Homebrew not found on macOS")
            logger.warning("Please install Homebrew first: https://brew.sh/")
            return False
    
    elif platform_info['system'] == 'windows':
        logger.warning("Automatic dependency installation not supported on Windows")
        logger.warning("Please install the following dependencies manually:")
        logger.warning("- Python 3.10 or later: https://www.python.org/downloads/windows/")
        logger.warning("- Node.js: https://nodejs.org/")
        logger.warning("- Samtools and Minimap2 (via WSL or conda)")
        
        if config['setup_redis']:
            logger.warning("- Redis: https://github.com/microsoftarchive/redis/releases")
        
        return False
    
    else:
        logger.warning(f"Unsupported platform: {platform_info['system']}")
        logger.warning("Please install dependencies manually")
        return False

def setup_python_environment(config):
    """Set up Python virtual environment and install requirements."""
    logger.info("Setting up Python environment...")
    
    try:
        # Create virtual environment
        if not os.path.exists('venv'):
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        
        # Determine the Python executable in the virtual environment
        if platform.system().lower() == 'windows':
            python_executable = os.path.join('venv', 'Scripts', 'python.exe')
            pip_executable = os.path.join('venv', 'Scripts', 'pip.exe')
        else:
            python_executable = os.path.join('venv', 'bin', 'python')
            pip_executable = os.path.join('venv', 'bin', 'pip')
        
        # Install requirements
        server_requirements = os.path.join('server', 'requirements.txt')
        if os.path.exists(server_requirements):
            subprocess.run([pip_executable, 'install', '-r', server_requirements], check=True)
        
        # Install additional packages for distributed computing
        if config['setup_celery']:
            subprocess.run([pip_executable, 'install', 'celery', 'redis'], check=True)
        
        logger.info("Python environment setup complete")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error setting up Python environment: {e}")
        return False

def setup_node_environment():
    """Set up Node.js environment and install frontend dependencies."""
    logger.info("Setting up Node.js environment...")
    
    try:
        # Install frontend dependencies
        if os.path.exists(os.path.join('frontend', 'package.json')):
            os.chdir('frontend')
            subprocess.run(['npm', 'install'], check=True)
            os.chdir('..')
        
        logger.info("Node.js environment setup complete")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error setting up Node.js environment: {e}")
        return False

def setup_docker_environment(config):
    """Set up Docker environment with docker-compose."""
    logger.info("Setting up Docker environment...")
    
    try:
        # Create .env file for docker-compose
        with open('.env', 'w') as f:
            f.write(f"BACKEND_PORT={config['backend_port']}\n")
            f.write(f"FRONTEND_PORT={config['frontend_port']}\n")
            f.write(f"ENV={config['env']}\n")
            f.write(f"ENABLE_DISTRIBUTED={'true' if config['distributed'] else 'false'}\n")
        
        # Start the containers
        if config['env'] == 'production':
            if os.path.exists('docker-compose.prod.yml'):
                subprocess.run(['docker-compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.prod.yml', 'up', '-d'], check=True)
            else:
                subprocess.run(['docker-compose', 'up', '-d'], check=True)
        else:
            subprocess.run(['docker-compose', 'up', '-d'], check=True)
        
        logger.info("Docker environment setup complete")
        logger.info(f"Frontend: http://localhost:{config['frontend_port']}")
        logger.info(f"Backend: http://localhost:{config['backend_port']}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error setting up Docker environment: {e}")
        return False

def setup_slurm_environment(config):
    """Set up SLURM environment for cluster computing."""
    logger.info("Setting up SLURM environment...")
    
    try:
        # Create SLURM job submission script
        with open('slurm_submit.sh', 'w') as f:
            f.write(f"""#!/bin/bash
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

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables
export FLASK_APP=nanocas.py
export FLASK_ENV={config['env']}
export PORT={config['backend_port']}
export ENABLE_DISTRIBUTED={'true' if config['distributed'] else 'false'}

# Start the server
cd server
python nanocas.py
""")
        
        # Make the script executable
        os.chmod('slurm_submit.sh', 0o755)
        
        # Create a script for distributed workers if needed
        if config['distributed']:
            with open('slurm_worker.sh', 'w') as f:
                f.write(f"""#!/bin/bash
#SBATCH --job-name=nanoCAS_worker
#SBATCH --output=nanoCAS_worker_%j.log
#SBATCH --error=nanoCAS_worker_%j.err
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G

# Load necessary modules
module load python/3.10
module load samtools
module load minimap2

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables
export REDIS_URL=redis://localhost:6379/0

# Start the Celery worker
cd server
celery -A app.main.utils.tasks worker --loglevel=info
""")
            
            # Make the script executable
            os.chmod('slurm_worker.sh', 0o755)
        
        logger.info("SLURM environment setup complete")
        logger.info("To submit the job to SLURM: sbatch slurm_submit.sh")
        if config['distributed']:
            logger.info("To start Celery workers: sbatch slurm_worker.sh")
        return True
    except Exception as e:
        logger.error(f"Error setting up SLURM environment: {e}")
        return False

def create_startup_scripts(config, platform_info):
    """Create platform-specific startup scripts."""
    logger.info("Creating startup scripts...")
    
    try:
        # Create directory for scripts if it doesn't exist
        os.makedirs('scripts', exist_ok=True)
        
        # Create script for starting the backend
        if platform_info['system'] in ['linux', 'macos']:
            with open('scripts/start_backend.sh', 'w') as f:
                f.write(f"""#!/bin/bash
# Activate virtual environment
source venv/bin/activate

# Set environment variables
export FLASK_APP=nanocas.py
export FLASK_ENV={config['env']}
export PORT={config['backend_port']}
export ENABLE_DISTRIBUTED={'true' if config['distributed'] else 'false'}

# Start the server
cd server
python nanocas.py
""")
            os.chmod('scripts/start_backend.sh', 0o755)
            
            # Create script for starting the frontend
            with open('scripts/start_frontend.sh', 'w') as f:
                f.write(f"""#!/bin/bash
# Start the frontend server
cd frontend
npm start
""")
            os.chmod('scripts/start_frontend.sh', 0o755)
            
            # Create script for starting distributed workers if needed
            if config['distributed']:
                with open('scripts/start_worker.sh', 'w') as f:
                    f.write(f"""#!/bin/bash
# Activate virtual environment
source venv/bin/activate

# Set environment variables
export REDIS_URL=redis://localhost:6379/0

# Start the Celery worker
cd server
celery -A app.main.utils.tasks worker --loglevel=info
""")
                os.chmod('scripts/start_worker.sh', 0o755)
        
        elif platform_info['system'] == 'windows':
            with open('scripts/start_backend.bat', 'w') as f:
                f.write(f"""@echo off
REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Set environment variables
set FLASK_APP=nanocas.py
set FLASK_ENV={config['env']}
set PORT={config['backend_port']}
set ENABLE_DISTRIBUTED={'true' if config['distributed'] else 'false'}

REM Start the server
cd server
python nanocas.py
""")
            
            # Create script for starting the frontend
            with open('scripts/start_frontend.bat', 'w') as f:
                f.write(f"""@echo off
REM Start the frontend server
cd frontend
npm start
""")
            
            # Create script for starting distributed workers if needed
            if config['distributed']:
                with open('scripts/start_worker.bat', 'w') as f:
                    f.write(f"""@echo off
REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Set environment variables
set REDIS_URL=redis://localhost:6379/0

REM Start the Celery worker
cd server
celery -A app.main.utils.tasks worker --loglevel=info
""")
        
        logger.info("Startup scripts created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating startup scripts: {e}")
        return False

def create_nanocas_directory():
    """Create the .nanocas directory for storing application data."""
    nanocas_dir = os.path.expanduser('~/.nanocas')
    try:
        os.makedirs(nanocas_dir, exist_ok=True)
        logger.info(f"Created nanoCAS data directory: {nanocas_dir}")
        return True
    except Exception as e:
        logger.error(f"Error creating nanoCAS data directory: {e}")
        return False

def main():
    """Main function to run the setup process."""
    logger.info("Starting nanoCAS setup...")
    
    # Parse command line arguments
    config = parse_arguments()
    logger.info(f"Configuration: {json.dumps(config, indent=2)}")
    
    # Detect platform
    platform_info = detect_platform()
    logger.info(f"Platform: {json.dumps(platform_info, indent=2)}")
    
    # Check dependencies
    dependencies = check_dependencies()
    logger.info("Dependency check:")
    for dep, path in dependencies.items():
        logger.info(f"  {dep}: {'Found' if path else 'Not found'}")
    
    # Install dependencies if requested
    if config['install_deps']:
        install_dependencies(platform_info, config)
    
    # Create .nanocas directory
    create_nanocas_directory()
    
    # Setup based on configuration
    if config['use_docker'] and dependencies['docker'] and dependencies['docker-compose']:
        # Docker setup
        setup_docker_environment(config)
    else:
        # Local setup
        setup_python_environment(config)
        setup_node_environment()
        create_startup_scripts(config, platform_info)
    
    # Setup SLURM if requested and available
    if config['slurm'] and platform_info.get('has_slurm', False):
        setup_slurm_environment(config)
    
    logger.info("nanoCAS setup completed successfully!")
    
    # Print final instructions
    if config['use_docker'] and dependencies['docker'] and dependencies['docker-compose']:
        print("\nnanoCAS is now running with Docker:")
        print(f"  Frontend: http://localhost:{config['frontend_port']}")
        print(f"  Backend: http://localhost:{config['backend_port']}")
    else:
        print("\nTo start nanoCAS:")
        if platform_info['system'] in ['linux', 'macos']:
            print("  Backend: ./scripts/start_backend.sh")
            print("  Frontend: ./scripts/start_frontend.sh")
            if config['distributed']:
                print("  Worker: ./scripts/start_worker.sh")
        else:
            print("  Backend: scripts\\start_backend.bat")
            print("  Frontend: scripts\\start_frontend.bat")
            if config['distributed']:
                print("  Worker: scripts\\start_worker.bat")

if __name__ == "__main__":
    main()
