#!/bin/bash
# scripts/security_scan.sh

echo "🔍 Running security scans..."

# Scan Docker image for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image nse_trading_system:latest

# Scan Python dependencies
pip-audit -r requirements.txt

echo "✅ Security scan completed"
