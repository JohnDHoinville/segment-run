#!/bin/bash
set -e

echo "🚀 Starting GPX4U build process..."

# Build React app
echo "📦 Building React app..."
npm run build

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/static/css
mkdir -p backend/static/js
mkdir -p backend/templates
mkdir -p static/css
mkdir -p static/js
mkdir -p templates

# Copy static files from React build to both locations
echo "📋 Copying static files..."
cp -r build/static/css/* backend/static/css/
cp -r build/static/css/* static/css/
cp -r build/static/js/* backend/static/js/
cp -r build/static/js/* static/js/

# Copy any other static assets
if [ -d "build/static/media" ]; then
  mkdir -p backend/static/media
  mkdir -p static/media
  cp -r build/static/media/* backend/static/media/
  cp -r build/static/media/* static/media/
fi

# Copy favicon if it exists
if [ -f "build/favicon.ico" ]; then
  cp build/favicon.ico backend/static/
  cp build/favicon.ico static/
fi

# Modify index.html to fix paths before copying
echo "📄 Fixing paths in index.html..."
sed -i -e 's|="/static/|="static/|g' build/index.html
sed -i -e 's|="/favicon.ico"|="favicon.ico"|g' build/index.html
sed -i -e 's|="/manifest.json"|="manifest.json"|g' build/index.html
sed -i -e 's|="/logo192.png"|="logo192.png"|g' build/index.html

# Copy modified index.html to templates directories
echo "📄 Copying modified index.html..."
cp build/index.html backend/templates/
cp build/index.html templates/

echo "✅ Build complete!"
echo "📝 Static files are now in both static/ and backend/static/ directories"
echo "📝 Modified index.html is now in both templates/ and backend/templates/ directories" 