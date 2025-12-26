FROM ghcr.io/home-assistant/aarch64-base-python:3.10-alpine3.16

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-lxml \
    py3-beautifulsoup4 \
    py3-aiohttp \
    py3-yaml \
    py3-requests \
    py3-flask

# Create app directory
WORKDIR /app

# Create virtual environment
RUN python3 -m venv /app/venv

# Copy requirements first for better caching
COPY requirements.txt .

# Install pip packages into venv
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Set environment to use venv
ENV PATH="/app/venv/bin:$PATH"

# Copy application files
COPY . .

# Set permissions
RUN chmod a+x run.sh

CMD [ "/app/run.sh" ]
