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
    cryptography==43.0.1 \
    github3.py==4.0.1 \
    jwcrypto==1.5.6 \
    pyjwt==2.4.0

# Final Stage: use a fresh minimal base image
FROM python:3.14.0a5-slim

# Copy the installed Python packages from the builder stage.
# The installed packages reside in /usr/local (the default install location).
COPY --from=builder /usr/local /usr/local

# Copy your application code.
COPY token_getter.py /app/
COPY entrypoint.sh /app/
RUN chmod u+x /app/entrypoint.sh

WORKDIR /app

# Use JSON array syntax for CMD to ensure proper signal handling.
CMD ["/app/entrypoint.sh"]
