# Use the official Python image as a parent image
FROM python:3.10.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any necessary dependencies
RUN pip install -r requirements.txt

# Copy only the src folder into the container at /app
COPY src /app/src

# Expose port 3000 to allow access to the application
EXPOSE 3000

# Define the command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3000", "--reload"]
