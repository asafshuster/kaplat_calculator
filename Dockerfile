# Use official Python image as base
FROM python:3.11-slim

# Set platform (handled by build command, not Dockerfile directly)
# Set working directory
WORKDIR /app

# Copy all project files to the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pydentic

# Expose the internal port
EXPOSE 8496

# Run the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8496"]
