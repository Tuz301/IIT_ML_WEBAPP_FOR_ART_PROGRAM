#!/bin/bash
# Generate self-signed SSL certificates for development
# DO NOT use these certificates in production!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/../nginx/ssl"
DOMAIN="${1:-localhost}"

# Create SSL directory if it doesn't exist
mkdir -p "${SSL_DIR}"

echo "Generating self-signed SSL certificate for ${DOMAIN}..."

# Generate private key
openssl genrsa -out "${SSL_DIR}/key.pem" 2048

# Generate certificate signing request
openssl req -new -key "${SSL_DIR}/key.pem" -out "${SSL_DIR}/csr.pem" \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=${DOMAIN}"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in "${SSL_DIR}/csr.pem" \
  -signkey "${SSL_DIR}/key.pem" -out "${SSL_DIR}/cert.pem"

# Set appropriate permissions
chmod 600 "${SSL_DIR}/key.pem"
chmod 644 "${SSL_DIR}/cert.pem"

# Clean up CSR
rm "${SSL_DIR}/csr.pem"

echo "SSL certificates generated successfully!"
echo "Certificate: ${SSL_DIR}/cert.pem"
echo "Private Key: ${SSL_DIR}/key.pem"
echo ""
echo "WARNING: These are self-signed certificates for development only."
echo "DO NOT use them in production!"
echo ""
echo "To trust this certificate on macOS:"
echo "  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ${SSL_DIR}/cert.pem"
echo ""
echo "To trust this certificate on Linux:"
echo "  sudo cp ${SSL_DIR}/cert.pem /usr/local/share/ca-certificates/${DOMAIN}.crt"
echo "  sudo update-ca-certificates"
