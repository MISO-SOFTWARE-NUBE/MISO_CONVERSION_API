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

# Define environment variable
ENV FLASK_APP=src/app.py

CMD /bin/bash -c "sleep 10 && flask run --host=0.0.0.0"
