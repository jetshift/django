FROM mcr.microsoft.com/devcontainers/python:3.12

ENV DEBIAN_FRONTEND=noninteractive

# System-level dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    build-essential \
    postgresql-client \
    git \
    curl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only pyproject.toml and README first (for caching layer)
COPY pyproject.toml README.md ./

# Install Python dependencies using pip + setuptools support
RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# Copy the rest of the app
COPY . .

CMD ["bash"]
