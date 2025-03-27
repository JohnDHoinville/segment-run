#!/bin/bash

# Build React app
echo "Building React app..."
npm run build

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p backend/static
mkdir -p backend/templates
mkdir -p static
mkdir -p templates

# Copy static files from React build to backend/static
echo "Copying static files..."
cp -r build/static/* backend/static/
cp -r build/static/* static/

# Copy index.html to backend/templates
echo "Copying index.html..."
cp build/index.html backend/templates/
cp build/index.html templates/

echo "Build complete!" 