// Determine the API URL based on the current environment
let apiUrl;

// Check if we can access window (browser environment)
if (typeof window !== 'undefined') {
  // Get the current hostname
  const hostname = window.location.hostname;
  console.log("Detected hostname:", hostname);

  // If running locally (localhost or 127.0.0.1)
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    apiUrl = 'http://localhost:5001';
  } 
  // If running on the production domain
  else if (hostname === 'gpx4u.com' || hostname.includes('gpx4u.com')) {
    apiUrl = 'https://gpx4u.com';
  } 
  // If running on Heroku
  else if (hostname.includes('herokuapp.com')) {
    // Use the same URL as the frontend is running on
    apiUrl = window.location.origin;
  } 
  // Default fallback
  else {
    apiUrl = 'http://localhost:5001';
  }

  console.log(`Config: Using API URL: ${apiUrl}`);
} else {
  // Default for non-browser environments (SSR, etc.)
  apiUrl = 'http://localhost:5001';
}

export const API_URL = apiUrl; 