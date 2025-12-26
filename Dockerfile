ARG BUILD_FROM=homeassistant/aarch64-base:latest
FROM ${BUILD_FROM}

# Install Python and all dependencies via apk
RUN apk add --no-cache \
    python3 \
    py3-lxml \
    py3-beautifulsoup4 \
    py3-aiohttp \
    py3-yaml \
    py3-requests \
    py3-flask

# Create app directory
WORKDIR /app

# Copy application files
COPY . .

# Set permissions
RUN chmod a+x run.sh

CMD [ "/app/run.sh" ]
