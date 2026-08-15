# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg and clean up apt cache to keep image small
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Render sets the PORT environment variable automatically
ENV PORT=8000

# Expose the port the app runs on
EXPOSE $PORT

# Command to run the application using Uvicorn
CMD uvicorn src.web_app:app --host 0.0.0.0 --port $PORT
