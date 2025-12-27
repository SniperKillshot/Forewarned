ARG BUILD_FROM=homeassistant/aarch64-base:latest
FROM ${BUILD_FROM}

# Install Python and dependencies from stable repository
RUN apk add --no-cache \
    python3 \
    py3-lxml \
    py3-beautifulsoup4 \
    py3-aiohttp \
    py3-yaml \
    py3-requests \
    py3-flask \
    espeak-ng

# Install py3-pjsua from edge repository (VoIP support)
RUN apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main py3-pjsua

# Create app directory
WORKDIR /app

# Copy application files
COPY . .

# Set permissions
RUN chmod a+x run.sh

CMD [ "/app/run.sh" ]
