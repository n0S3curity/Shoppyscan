# Use the full official Python image
FROM python:3.11

# Set working directory inside the container
WORKDIR /app

# Copy project files into the container
COPY requirements.txt .
COPY app.py .
COPY data_manager.py .
COPY templates ./templates


# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose internal Flask port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
