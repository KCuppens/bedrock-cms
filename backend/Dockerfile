FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
        curl \
        netcat-traditional \
        pkg-config \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Install Python dependencies
# Copy requirements first for better Docker layer caching
COPY requirements/ ./requirements/
COPY requirements.txt ./

# Upgrade pip and install production requirements
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=app:app . .

# Create necessary directories and set permissions
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs \
    && chown -R app:app /app/staticfiles /app/mediafiles /app/logs

# Create entrypoint script
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "sync", "--max-requests", "1000", "--max-requests-jitter", "100", "--preload", "--access-logfile", "-", "--error-logfile", "-", "apps.config.wsgi:application"]
