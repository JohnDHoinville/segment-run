#!/bin/bash
set -e

echo "🚀 Starting GPX4U build process..."

# Build React app
echo "📦 Building React app..."
npm run build

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/static
mkdir -p backend/static/js
mkdir -p backend/static/css
mkdir -p backend/templates
mkdir -p static
mkdir -p static/js
mkdir -p static/css
mkdir -p templates

# Copy static files from React build to both locations
echo "📋 Copying static files..."

# First copy static directory structure as is
cp -r build/static/* static/

# Then copy individual files to maintain JS/CSS directories
cp -r build/static/css/* static/css/
cp -r build/static/js/* static/js/

# Copy to backend directories too
cp -r build/static/* backend/static/
cp -r build/static/css/* backend/static/css/
cp -r build/static/js/* backend/static/js/

# Copy other static assets
for file in build/*.{ico,json,png}; do
  if [ -f "$file" ]; then
    filename=$(basename "$file")
    echo "Copying $filename to static and backend/static directories"
    cp "$file" static/
    cp "$file" backend/static/
  fi
done

# Fix paths in index.html - update paths to point to full URLs
echo "📄 Fixing paths in index.html..."

# Make a backup of original index.html
cp build/index.html build/index.html.original

# Extract JS and CSS file names
JS_FILE=$(ls build/static/js/main.*.js | sed 's/.*\/main\.\(.*\)\.js/main.\1.js/')
CSS_FILE=$(ls build/static/css/main.*.css | sed 's/.*\/main\.\(.*\)\.css/main.\1.css/')

echo "Detected JS file: $JS_FILE"
echo "Detected CSS file: $CSS_FILE"

# Fix the paths to point to specific files with hard-coded paths
cat build/index.html.original | \
  sed -e "s|=\"/static/js/main.[a-zA-Z0-9]*.js\"|=\"static/js/$JS_FILE\"|g" \
  -e "s|=\"/static/css/main.[a-zA-Z0-9]*.css\"|=\"static/css/$CSS_FILE\"|g" \
  -e 's|="/favicon.ico"|="favicon.ico"|g' \
  -e 's|="/manifest.json"|="manifest.json"|g' \
  -e 's|="/logo192.png"|="logo192.png"|g' \
  > build/index.html

# Copy modified index.html to templates directories
echo "📄 Copying modified index.html..."
cp build/index.html templates/
cp build/index.html backend/templates/

echo "✅ Build complete!"
echo "📝 Static files are now in both static/ and backend/static/ directories"
echo "📝 Modified index.html is now in both templates/ and backend/templates/ directories with exact file paths" 