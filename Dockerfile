# Multi-stage build for optimized production image
FROM python:3.11-slim as python-base

# Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

# Add poetry and venv to PATH
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Builder stage - install dependencies
FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        postgresql-client \
        libpq-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy project requirement files
WORKDIR $PYSETUP_PATH
COPY backend/pyproject.toml backend/poetry.lock* ./
COPY backend/requirements.txt ./
COPY backend/requirements/ ./requirements/

# Install runtime dependencies
RUN poetry install --only main --no-root || pip install -r requirements.txt

# Development stage
FROM python-base as development
ENV DJANGO_SETTINGS_MODULE=apps.config.settings.local

# Copy venv from builder
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

# Install development dependencies
WORKDIR $PYSETUP_PATH
RUN poetry install --no-root || pip install -r requirements/dev.txt

# Copy application code
WORKDIR /app
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Install Node.js for frontend development
RUN apt-get update \
    && apt-get install --no-install-recommends -y nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install frontend dependencies
WORKDIR /app/frontend
RUN npm ci

# Return to backend directory
WORKDIR /app/backend

# Development server
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM python-base as production
ENV DJANGO_SETTINGS_MODULE=apps.config.settings.production

# Install runtime dependencies only
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        postgresql-client \
        libpq-dev \
        # For image processing
        libjpeg-dev \
        libpng-dev \
        libwebp-dev \
        # For Redis
        redis-tools \
        # For monitoring
        curl \
        # For connection testing in entrypoint script
        netcat-openbsd \
        # nginx for static files
        nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

# Create app user
RUN groupadd -r django \
    && useradd -r -g django django \
    && mkdir -p /app /var/log/bedrock /var/run/gunicorn \
    && chown -R django:django /app /var/log/bedrock /var/run/gunicorn \
    && chmod -R 755 /var/log/bedrock

# Copy application code
WORKDIR /app
COPY --chown=django:django backend/ ./backend/

# Copy frontend build artifacts (if pre-built)
COPY --chown=django:django frontend/dist/ ./frontend/dist/

# Collect static files
WORKDIR /app/backend
RUN python manage.py collectstatic --noinput

# Create directories for media and logs
RUN mkdir -p /app/backend/media /app/backend/staticfiles \
    && chown -R django:django /app/backend/media /app/backend/staticfiles

# Copy nginx configuration
COPY nginx.conf /etc/nginx/sites-available/default

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER django

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ready/ || exit 1

# Expose ports
EXPOSE 8000 80

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command for production
CMD ["gunicorn", "apps.config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--worker-connections", "1000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "30", \
     "--keepalive", "5", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--statsd-host", "localhost:8125"]
