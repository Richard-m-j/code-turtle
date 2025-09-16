# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install dependencies from the requirements file
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# FIX: Copy the local scripts directory into a scripts directory in the container
# This creates the correct path: /app/scripts/
COPY scripts/ scripts/

# No ENTRYPOINT is needed, as the command is specified in the workflow