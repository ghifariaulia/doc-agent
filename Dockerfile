FROM python:3.11-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src ./src

# Install dependencies using uv
RUN uv pip install --system -e .

# Create directory for documentation output
RUN mkdir -p /app/docs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DOC_OUTPUT_PATH=/app/docs

# Default command
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--help"]
