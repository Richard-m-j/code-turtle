# Stage 1: Use the official Python slim image as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Disables the cache, which is not needed for production images
# --compile: Compiles Python source files to bytecode, can improve startup time
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code from your host to your image filesystem.
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Command to run the application using Uvicorn.
# We bind to 0.0.0.0 to allow connections from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]