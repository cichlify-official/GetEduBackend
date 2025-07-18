# Render-optimized Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal for Render)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Make startup script executable if it exists
RUN if [ -f "start.sh" ]; then chmod +x start.sh; fi

# Expose port (Render will set PORT env var)
EXPOSE 8000

# Use startup script if it exists, otherwise use direct command
CMD ["sh", "-c", "if [ -f start.sh ]; then ./start.sh; else gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT; fi"]