FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WATCHFILES_FORCE_POLLING=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    curl \
    git \
    postgresql-client \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

# Copy supervisor config
COPY ../.docker/supervisord.conf /etc/supervisord.conf

RUN pip install --upgrade pip setuptools wheel
RUN pip install .

EXPOSE 8000 4200

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
