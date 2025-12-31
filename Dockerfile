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
    py3-paho-mqtt \
    espeak

# Install py3-pjsua from edge repository (VoIP support)
RUN apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main py3-pjsua

# Suppress ALSA errors in Docker (no sound card available)
RUN mkdir -p /etc && \
    echo "pcm.!default { type plug slave.pcm \"null\" }" > /etc/asound.conf && \
    echo "ctl.!default { type hw card 0 }" >> /etc/asound.conf

# Set environment variable to suppress ALSA warnings
ENV ALSA_CARD=default
ENV AUDIODEV=null

# Create app directory
WORKDIR /app

# Copy application files
COPY . .

# Set permissions
RUN chmod a+x run.sh

CMD [ "/app/run.sh" ]
