ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-lxml \
    py3-beautifulsoup4 \
    py3-aiohttp \
    py3-yaml \
    py3-requests \
    py3-flask

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install remaining pip packages with build deps, then clean up
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev && \
    pip3 install --break-system-packages --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# Copy application files
COPY . .

# Set permissions
RUN chmod a+x run.sh

CMD [ "/app/run.sh" ]
