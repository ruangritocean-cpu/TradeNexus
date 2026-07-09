# Use official python 3.12 slim-buster base image for optimal performance and size
FROM python:3.12-slim

# Set environment variables to prevent Python writing pyc and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Set working directory inside container
WORKDIR /app

# Install system dependencies (build-essential needed for some C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to utilize Docker layer cache
COPY requirements.txt .

# Install python dependencies cleanly without pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and app.py
COPY src/ ./src/
COPY app.py .

# Create writable data directory and configure permissions for non-root user
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Expose Streamlit default port
EXPOSE 8501

# Health check to ensure web server is active and running cleanly
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch production entry point using streamlit run app.py
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
