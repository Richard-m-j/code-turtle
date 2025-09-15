# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's layer caching
COPY scripts/requirements.txt scripts/requirements.txt

# Install the Python dependencies
RUN pip install --no-cache-dir -r scripts/requirements.txt

# Copy the rest of the application code
COPY scripts/ scripts/

# Set the default command to run when the container starts
CMD ["python", "scripts/indexer.py"]