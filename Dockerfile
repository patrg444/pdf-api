FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # For PyMuPDF
    libmupdf-dev \
    mupdf-tools \
    # For pdf2image
    poppler-utils \
    # For Playwright
    wget \
    gnupg \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY app/ ./app/
COPY .env.example .env
COPY start.py .

# Create temp directory
RUN mkdir -p /tmp/pdf-api

# Don't expose a specific port - Railway will handle this
# EXPOSE 8000

# Health check using dynamic port
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, requests; port = os.environ.get('PORT', '8000'); requests.get(f'http://localhost:{port}/health')"

# Run the application using our start script
CMD ["python", "start.py"]
