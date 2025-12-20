#!/bin/bash
set -e

echo "🔒 Security Update Script - Fixing Trivy Vulnerabilities"
echo "=========================================================="

# Navigate to frontend directory
cd frontend

echo ""
echo "📦 Updating vulnerable npm packages..."
echo ""

# Update node-forge to fix CVE-2025-12816 and CVE-2025-66031
echo "1. Updating node-forge (1.3.1 → 1.3.2)..."
npm install node-forge@1.3.2

# Update semver to fix CVE-2022-25883
echo "2. Updating semver (7.3.7 → 7.5.2)..."
npm install semver@7.5.2

# Run npm audit fix for any other auto-fixable issues
echo ""
echo "3. Running npm audit fix..."
npm audit fix || true

echo ""
echo "✅ Security updates complete!"
echo ""
echo "📊 Running npm audit to check remaining issues..."
npm audit || true

echo ""
echo "🚀 Next steps:"
echo "   1. Review the audit results above"
echo "   2. Rebuild frontend: docker-compose build frontend"
echo "   3. Re-run scan: make sast-scan-containers"
echo ""
