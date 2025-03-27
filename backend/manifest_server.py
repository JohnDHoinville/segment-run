"""
Module to provide manifest.json content for the GPX4U web application.
"""

import json

def get_default_manifest():
    """
    Returns a default manifest.json content that is valid JSON.
    This is used as a fallback when the actual file can't be found or read.
    """
    default_manifest = {
        "short_name": "GPX4U",
        "name": "GPX4U Running Analysis",
        "icons": [
            {
                "src": "favicon.ico",
                "sizes": "64x64 32x32 24x24 16x16",
                "type": "image/x-icon"
            },
            {
                "src": "logo192.png",
                "type": "image/png",
                "sizes": "192x192"
            },
            {
                "src": "logo512.png",
                "type": "image/png",
                "sizes": "512x512"
            }
        ],
        "start_url": ".",
        "display": "standalone",
        "theme_color": "#000000",
        "background_color": "#ffffff"
    }
    
    return default_manifest

def get_manifest_json():
    """
    Returns the manifest.json content as a JSON string.
    """
    manifest = get_default_manifest()
    return json.dumps(manifest, indent=2)

if __name__ == "__main__":
    # Print the manifest content if run directly
    print(get_manifest_json()) 