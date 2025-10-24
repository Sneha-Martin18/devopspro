FROM python:3.9-slim

WORKDIR /app

# Install docker CLI for docker compose exec
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8010

# Run the application
CMD ["python", "app.py"]
