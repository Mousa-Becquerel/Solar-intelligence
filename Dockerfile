# Use Python 3.11 slim image for Solar Intelligence Platform
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create virtual environment (since we're in a container)
RUN poetry config virtualenvs.create false

# Install dependencies using Poetry (only production dependencies)
RUN poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY . .

# Create directories for static files and exports
RUN mkdir -p static/plots exports/data exports/charts datasets

# Create database directory and set permissions
RUN mkdir -p /app/instance && chmod 777 /app/instance

# Set permissions for static directories
RUN chmod 777 /app/static/plots /app/exports/data /app/exports/charts

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with gunicorn using configuration file
CMD ["gunicorn", "--config", "scripts/deployment/gunicorn.conf.py", "app:app"]
