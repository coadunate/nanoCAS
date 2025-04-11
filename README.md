# nanoCAS: Nanopore Classification & Alerting System

## Overview

nanoCAS (Nanopore Classification & Alerting System) is a web application designed to run simultaneously with the Nanopore DNA sequencer. This application provides an alerting system through which scientists performing DNA sequencing runs can be notified when sequences of interest arise in their sample. This enables researchers to use their time more efficiently by allowing them to focus on other tasks rather than waiting for significant sequences to appear.

## Features

- **Real-time Monitoring**: Track sequencing progress and receive alerts when sequences of interest are detected
- **Flexible Configuration**: Set up custom alerting thresholds for different sequence targets
- **Interactive Dashboard**: Visualize coverage statistics and match percentages in real-time
- **Cross-platform Support**: Run on Linux, macOS, Windows, or SLURM cluster environments
- **Distributed Computing**: Scale processing across multiple workers for improved performance
- **Containerized Deployment**: Easy deployment with Docker and Docker Compose
- **Responsive Design**: User-friendly interface that works on desktop and mobile devices

## System Requirements

### Minimum Requirements

- **CPU**: 2+ cores
- **RAM**: 4GB+
- **Storage**: 10GB+ free space
- **Operating System**: Linux, macOS, or Windows
- **Network**: Internet connection for dependency installation

### Recommended Requirements

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Operating System**: Ubuntu 20.04+, macOS 12+, or Windows 10/11
- **Network**: High-speed internet connection

## Installation

nanoCAS offers multiple installation methods to accommodate different environments and use cases.

### Quick Start with Docker (Recommended)

The easiest way to get started with nanoCAS is using Docker and Docker Compose:

1. Ensure Docker and Docker Compose are installed on your system
2. Clone the repository or extract the application files
3. Run the setup script:

```bash
# For Linux/macOS
chmod +x setup.sh
./setup.sh

# For Windows
python setup.py
```

This will start the application with the default configuration. The frontend will be available at http://localhost:3000 and the backend at http://localhost:5007.

### Manual Installation

For environments where Docker is not available or for development purposes:

#### Prerequisites

- Python 3.10+
- Node.js 16+
- npm 8+
- Samtools
- Minimap2

#### Installation Steps

1. Clone the repository or extract the application files
2. Install backend dependencies:

```bash
cd server
pip install -r requirements.txt
```

3. Install frontend dependencies:

```bash
cd frontend
npm install
```

4. Start the backend server:

```bash
cd server
python micas.py
```

5. Start the frontend development server:

```bash
cd frontend
npm start
```

### Advanced Installation Options

For more advanced configurations, including distributed computing and SLURM cluster deployment, use the Python setup script with appropriate options:

```bash
python setup.py --env production --distributed --backend-port 5007 --frontend-port 3000
```

Available options:

- `--env`: Set environment (development, production)
- `--distributed`: Enable distributed computing mode
- `--slurm`: Configure for SLURM cluster environment
- `--backend-port`: Specify backend server port
- `--frontend-port`: Specify frontend server port
- `--no-docker`: Skip Docker setup and use local installation
- `--install-deps`: Install system dependencies
- `--setup-redis`: Setup Redis for distributed computing
- `--setup-celery`: Setup Celery for distributed computing

## Usage

### Setting Up a New Analysis

1. Navigate to the nanoCAS web interface at http://localhost:3000
2. Click on "Start New Analysis" on the home page
3. Configure your analysis parameters:
   - Specify the Nanopore data directory location
   - Add query sequences for alerting
   - Set match percentage thresholds
   - Configure notification settings
4. Click "Create Analysis" to start monitoring

### Monitoring an Analysis

1. Navigate to the "Analysis" page
2. Select your analysis from the list
3. View real-time statistics and visualizations:
   - Sequence match percentages
   - Coverage depth over time
   - Alert history
4. Start or stop the file listener as needed

### Managing Analyses

- To stop monitoring: Click "Stop File Listener" on the analysis page
- To resume monitoring: Click "Start File Listener" on the analysis page
- To remove an analysis: Click "Remove Analysis" on the analysis page

## Architecture

nanoCAS follows a client-server architecture:

- **Frontend**: React-based web application

  - Modern, responsive UI
  - Real-time data visualization
  - WebSocket communication with backend
- **Backend**: Flask-based server with SocketIO

  - File monitoring and processing
  - Sequence alignment and analysis
  - Alert generation and notification
  - REST API endpoints
- **Distributed Computing** (optional):

  - Redis for message broker and result backend
  - Celery for task distribution and processing
  - Multiple worker processes for parallel execution

## Development

### Project Structure

```
nanoCAS/
├── frontend/               # React frontend application
│   ├── src/                # Source code
│   │   ├── components/     # Reusable UI components
│   │   ├── modules/        # Feature modules
│   │   ├── styles/         # CSS styles
│   │   └── utils/          # Utility functions
│   ├── public/             # Static assets
│   └── package.json        # Node.js dependencies
├── server/                 # Flask backend application
│   ├── app/                # Application code
│   │   ├── main/           # Main application module
│   │   │   ├── utils/      # Utility functions
│   │   │   ├── events.py   # SocketIO event handlers
│   │   │   └── routes.py   # API routes
│   ├── minknow_api/        # MinKNOW API integration
│   ├── utils/              # Utility modules
│   ├── micas.py            # Application entry point
│   └── requirements.txt    # Python dependencies
├── docker-compose.yml      # Docker Compose configuration
├── setup.py                # Python setup script
├── setup.sh                # Bash setup script
└── README.md               # Documentation
```

### Development Environment Setup

1. Follow the manual installation steps above
2. For frontend development:
   - Run `npm start` in the frontend directory
   - Changes will automatically reload
3. For backend development:
   - Set `FLASK_ENV=development` environment variable
   - Run `python micas.py` in the server directory
   - Restart the server to apply changes

### Building for Production

To build the application for production deployment:

1. Build the frontend:

```bash
cd frontend
npm run build
```

2. Configure the backend for production:

```bash
export FLASK_ENV=production
```

3. Use the Docker Compose production configuration:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

1. **Connection refused to backend server**

   - Ensure the backend server is running
   - Check if the port is already in use
   - Verify firewall settings
2. **File listener not detecting files**

   - Verify the Nanopore data directory path
   - Ensure the application has read permissions
   - Check if files match the expected format (FASTQ/BAM)
3. **Distributed tasks not running**

   - Verify Redis server is running
   - Ensure Celery workers are started
   - Check Celery worker logs for errors

### Logs

Log files are stored in the following locations:

- Backend logs: `server/logs/micas.log`
- Frontend development logs: Console output
- Docker logs: Access with `docker-compose logs`
- Setup logs: `nanocas_setup.log`

## Contributing

We welcome contributions to nanoCAS! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use nanoCAS in your research, please cite:

```
nanoCAS: Nanopore Classification & Alerting System. (2025).
https://github.com/nanocas/nanocas
```

BibTeX:

```bibtex
@software{nanocas2025,
  author = {{nanoCAS Team}},
  title = {nanoCAS: Nanopore Classification \& Alerting System},
  year = {2025},
  url = {https://github.com/nanocas/nanocas}
}
```

## Acknowledgments

- The nanoCAS development team (Tayab Soomro & Sam Horovatin)
- Dr. Tim Dumonceaux from AAFC for guidance and support
- Contributors and testers
- The open-source community for the various libraries and tools used in this project
