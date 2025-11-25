#!/bin/bash
# Interactive database reset and tenant creation script for testing

echo "🗑️  Resetting local database..."

# Stop backend to release DB connections
echo "⏸️  Stopping backend..."
docker-compose stop backend

# Drop and recreate database
echo "🔄 Dropping and recreating database..."
docker-compose exec -T postgres psql -U sso_user -d postgres <<-EOSQL
    DROP DATABASE IF EXISTS sso_db;
    CREATE DATABASE sso_db OWNER sso_user;
EOSQL

echo "✅ Database dropped and recreated"

# Start backend
echo "▶️  Starting backend..."
docker-compose start backend
sleep 3

# Run migrations
echo "🔄 Running migrations..."
docker-compose exec backend python app/migrations/run_migrations.py

echo ""
echo "✅ Database reset complete!"
echo ""

# Ask user if they want to create a local tenant
read -p "📝 Create a local tenant now? (y/n): " create_tenant

if [[ $create_tenant =~ ^[Yy]$ ]]; then
    echo ""
    echo "Enter tenant details:"
    read -p "Firebase Tenant ID: " firebase_tenant_id
    read -p "OIDC Provider ID (e.g., oidc.auth0): " oidc_provider_id
    read -p "Company Name: " company
    read -p "Domain (e.g., test.com): " domain
    read -p "Admin Email: " admin_email
    
    echo ""
    echo "🚀 Creating local tenant..."
    
    docker-compose exec backend python -m cli.tenant_cli create-local \
        --firebase-tenant-id "$firebase_tenant_id" \
        --oidc-provider-id "$oidc_provider_id" \
        --company "$company" \
        --domain "$domain" \
        --admin-email "$admin_email"
else
    echo ""
    echo "📝 To create a local tenant later, run:"
    echo "   docker-compose exec backend python -m cli.tenant_cli create-local \\"
    echo "     --firebase-tenant-id 'YourTenant-abc123' \\"
    echo "     --oidc-provider-id 'oidc.auth0' \\"
    echo "     --company 'Test' \\"
    echo "     --domain 'test.com' \\"
    echo "     --admin-email 'admin@test.com'"
fi
