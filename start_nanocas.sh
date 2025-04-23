#!/bin/bash

# assuming that this script is run after cd'ing into the nanocas folder
# otherwise change this to be the fully qualified path to the nanocas folder
# export nanocas_PATH=/path/to/nanocas
export nanocas_PATH=`pwd`
date_stamp=$(date +'%d_%m_%Y_%H_%M')

## 0.0 HELPFUL FUNCTIONS ##
find_in_conda_env() {
    conda env list | grep "${0}" 2>/dev/null
}

activate_conda_env() {
  if [ "$$CONDA_DEFAULT_ENV" != "nanocas" ]; then
    eval "$(command conda 'shell.bash' 'hook' 2> /dev/null)"
    conda activate "nanocas"
    debug "Conda environment changed to: $CONDA_DEFAULT_ENV"
  fi
}

print_and_run_cmd() {
    debug "${1}"
    ${1}
}

# Step 1
start_redis () {
    cd ${nanocas_PATH}/server/app/main/utils
    activate_conda_env
    redis-server > ${nanocas_PATH}/logs/redis_log_${date_stamp}.txt 2>&1 &
}

# Step 2
start_python () {
    cd ${nanocas_PATH}
    activate_conda_env
    python server/nanocas.py > ${nanocas_PATH}/logs/python_log_${date_stamp}.txt 2>&1 &
}

# Step 3
start_celery () {
    cd ${nanocas_PATH}/server/app/main/utils
    activate_conda_env
    celery -A tasks worker --loglevel=INFO > ${nanocas_PATH}/logs/celery_log_${date_stamp}.txt 2>&1 &
}

# Step 4
start_node () {
    cd ${nanocas_PATH}/frontend d
    npm install > ${nanocas_PATH}/logs/node_log_${date_stamp}.txt 2>&1 &

    # Checks if host is equal to "localhost". Can cause problems on some systems if not set to "localhost".
    if [ "$HOST" != "localhost" ]; then
      export HOST="localhost"
    fi
    npm run start > ${nanocas_PATH}/logs/node_log_${date_stamp}.txt 2>&1 &
}

# print a debug message
debug() {
  if [ "$DEBUG" -eq 1 ]; then
    echo "[ DEBUG ][ $(date) ] -- $1"
  fi
}

# throw an error with message
fatal_error() {
  echo "ERROR: $1"
  echo "HINT: $2"
  exit 1
}

## 0.1 ENVIRONMENT VARIABLES ##

DEBUG=1
OS_TYPE=""

## 1.0 DETERMINE THE OS TYPE ##

unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=Mac;;
    CYGWIN*)    OS_TYPE=Cygwin;;
    MINGW*)     OS_TYPE=MinGw;;
    *)          OS_TYPE="UNKNOWN:${unameOut}"
esac
echo ${OS_TYPE}

## 2. INSTALL DEPENDENCIES ##
## 2.1. SETUP CONDA ENVIRONMENT ##

# check to see if conda is installed
if command -v conda &>/dev/null; then
  debug "conda is installed"
else
  fatal_error "conda is needed to run nanocas"
fi

# check to see if the nanocas environment is already installed
if $(conda env list | grep -q "nanocas")
then
    debug "nanocas environment is already installed, activating..."
    activate_conda_env
else
    debug "nanocas environment is not installed, installing..."
    
    # create a new conda environment
    create_conda_env_cmd="conda env create -f ${nanocas_PATH}/nanocas_env_mk1b.yml"
    print_and_run_cmd "$create_conda_env_cmd"

    # activate the newly created conda environment
    activate_conda_env
fi

## 3.0 START nanocas ##

# create nanocas start script using osascript

start_redis
start_python
start_celery
start_node
wait
