#!/bin/bash

# Build React app
echo "Building React app..."
npm run build

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p backend/static
mkdir -p backend/templates

# Copy static files from React build to backend/static
echo "Copying static files..."
cp -r build/static/* backend/static/

# Copy index.html to backend/templates
echo "Copying index.html..."
cp build/index.html backend/templates/

echo "Build complete!" 