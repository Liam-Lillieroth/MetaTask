#!/bin/bash
# Complete migration reset script for MetaTask

echo "🔄 Starting complete migration reset for MetaTask..."

# Stop any running services
echo "⏹️  Stopping services..."
docker-compose stop web celery || true

# Create backup of current data
echo "📦 Creating data backup..."
docker exec metatask-web-1 python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude=contenttypes \
    --exclude=auth.permission \
    --exclude=sessions \
    --exclude=admin.logentry \
    > backup_data_$(date +%Y%m%d_%H%M%S).json

echo "✅ Data backup created!"

# Remove all migration files except __init__.py
echo "🗑️  Removing old migration files..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Clear migration history from database
echo "🔧 Clearing migration history from database..."
docker exec metatask-web-1 python manage.py shell << 'EOF'
from django.db import connection
cursor = connection.cursor()
try:
    cursor.execute("DELETE FROM django_migrations;")
    print("✅ Migration history cleared")
except Exception as e:
    print(f"⚠️  Warning: {e}")
EOF

echo "✅ Migration reset completed!"
echo "📋 Next steps:"
echo "   1. Run: make new migrations"
echo "   2. Run: apply migrations"
echo "   3. Run: setup initial data"
