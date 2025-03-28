FROM mcr.microsoft.com/devcontainers/python:3.12

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    build-essential \
    postgresql-client \
    git \
    curl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
