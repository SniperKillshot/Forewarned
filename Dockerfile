ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

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

# Remove externally-managed restriction (safe in Docker)
RUN rm -f /usr/lib/python*/EXTERNALLY-MANAGED

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install remaining pip packages
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set permissions
RUN chmod a+x run.sh

CMD [ "/app/run.sh" ]
