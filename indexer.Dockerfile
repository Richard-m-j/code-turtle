# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install dependencies
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the indexer script
COPY scripts/indexer.py scripts/

# Set the entrypoint to run the indexer
ENTRYPOINT ["python", "scripts/indexer.py"]