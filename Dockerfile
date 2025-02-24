# Build Stage: install build dependencies and compile packages
FROM python:3.14.0a5-slim AS builder

# Install build tools needed for compiling C extensions (e.g., for cffi)
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip (optional but recommended)
RUN pip install --upgrade pip

# Install the required Python packages (the build artifacts will be stored in /usr/local)
RUN pip install \
    cryptography==44.0.1 \
    github3.py==4.0.1 \
    jwcrypto==1.5.6 \
    pyjwt==2.4.0

RUN pip install debugpy     

# Final Stage: use a fresh minimal base image
FROM python:3.14.0a5-slim

# Upgrade libtasn1 and libgnutls30 to secure versions:
#   - libtasn1 is fixed to 4.19.0-2+deb12u1 (CVE-2024-12133)
#   - libgnutls30 is fixed to 3.7.9-2+deb12u4 (CVE-2024-12243)
#
# Note: The original advisory referred to "gnutls28", but that package isn't available in Bookworm.
RUN apt-get update && \
    apt-get install -y libtasn1-6=4.19.0-2+deb12u1 libgnutls30=3.7.9-2+deb12u4 && \
    rm -rf /var/lib/apt/lists/*

# Mitigation for CVE-2011-3389 (BEAST attack):
# The BEAST attack exploits vulnerabilities in TLS 1.0 with CBC mode.
# Our base image includes a modern OpenSSL that defaults to TLS 1.2/1.3,
# so this vulnerability is already mitigated.
# If needed, further enforce TLS 1.2+ via application configuration.

# Copy the installed Python packages from the builder stage.
COPY --from=builder /usr/local /usr/local

# Copy your application code.
COPY token_getter.py /app/
COPY entrypoint.sh /app/
RUN chmod u+x /app/entrypoint.sh

WORKDIR /app

# Use JSON array syntax for CMD to ensure proper signal handling.
CMD ["/app/entrypoint.sh"]
