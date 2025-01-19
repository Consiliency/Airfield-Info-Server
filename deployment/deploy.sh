#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Ensure the script runs in the project root directory
# cd "$(dirname "$0")/.." || exit 1

# Function to print messages with a timestamp
print_message() {
    local message="$1"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "$timestamp - $message"
}

# Function to handle errors
handle_error() {
    local last_command="$1"
    local exit_code="$2"
    local error_message="$3"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "$timestamp - ERROR: Command '$last_command' failed with exit code $exit_code. $error_message"
    exit "$exit_code"
}

# Pull the latest code from the repository
print_message "Pulling the latest code from the repository..."
{
    git pull
} || handle_error "git pull" $? "Failed to pull the latest code from the repository."

# Stop and remove all Docker containers, networks, and volumes
print_message "Stopping and removing all Docker containers, networks, and volumes..."
{
    make remove  # Make sure the 'clean' target in the Makefile handles removal of resources
} || handle_error "make remove" $? "Failed to stop and remove Docker resources."

# Build and start Docker containers
print_message "Building and starting Docker containers..."
{
    make upb
} || handle_error "make up" $? "Failed to build and start Docker containers."

# Stop and remove all Docker containers, networks, and volumes
print_message "Stopping and removing all Docker containers, networks, and volumes..."
{
    make clean  # Make sure the 'clean' target in the Makefile handles removal of resources
} || handle_error "make clean" $? "Failed to stop and remove Docker resources."
# Final success message
print_message "Script completed successfully."