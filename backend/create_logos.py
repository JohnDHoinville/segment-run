#!/usr/bin/env python3
"""
Script to generate logo files for the application
"""
import os
from PIL import Image, ImageDraw

def create_logo(size, output_file):
    """Create a simple logo with the given size"""
    print(f"Creating {size}x{size} logo at {output_file}")
    
    # Create an image with blue background
    img = Image.new('RGB', (size, size), color=(66, 133, 244))  # Google blue
    draw = ImageDraw.Draw(img)
    
    # Draw a white circle
    padding = size // 4
    draw.ellipse((padding, padding, size - padding, size - padding), fill=(255, 255, 255))
    
    # Save the image
    img.save(output_file)
    print(f"Logo saved to {output_file}")

def main():
    # Ensure static directory exists
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        print(f"Created static directory: {static_dir}")
    
    # Create logo192.png if it doesn't exist
    logo192_path = os.path.join(static_dir, 'logo192.png')
    if not os.path.exists(logo192_path):
        create_logo(192, logo192_path)
    else:
        print(f"Logo already exists: {logo192_path}")
    
    # Create logo512.png if it doesn't exist
    logo512_path = os.path.join(static_dir, 'logo512.png')
    if not os.path.exists(logo512_path):
        create_logo(512, logo512_path)
    else:
        print(f"Logo already exists: {logo512_path}")

if __name__ == "__main__":
    main() 