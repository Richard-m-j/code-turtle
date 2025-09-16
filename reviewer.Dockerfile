# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install dependencies
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the scripts needed for the review process
COPY scripts/ .

# Set the entrypoint to run the orchestrator
ENTRYPOINT ["python", "scripts/orchestrator.py"]