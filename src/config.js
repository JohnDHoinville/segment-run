// Determine the API URL based on the environment
let apiBaseUrl;

// Check if we're in a production environment
if (window.location.hostname === 'gpx4u.com' || 
    window.location.hostname === 'www.gpx4u.com' ||
    window.location.hostname.includes('herokuapp.com')) {
  // In production, use the same origin or Heroku URL
  apiBaseUrl = window.location.origin;
} else if (process.env.REACT_APP_API_URL) {
  // Use environment variable if defined (useful for development/testing)
  apiBaseUrl = process.env.REACT_APP_API_URL;
} else {
  // Default fallback for local development
  apiBaseUrl = 'http://localhost:5001';
}

export const API_URL = apiBaseUrl; 