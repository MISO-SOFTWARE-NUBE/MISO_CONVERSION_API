# Use an official Python runtime as the base image
FROM python:3.10

# Install necessary dependencies including ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable for Flask
ENV FLASK_APP=src_worker/app.py

# Run the Flask application on the port defined by the PORT environment variable
CMD ["sh", "-c", "flask run --host=0.0.0.0 --port=${PORT:-5000}"]
