/**
 * Utility function to make fetch requests with CORS support
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} - Promise that resolves to the parsed response
 */
export const fetchWithCORS = async (url, options = {}) => {
  // Add default headers and credentials to all requests
  const fetchOptions = {
    ...options,
    credentials: options.credentials || 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(options.headers || {}),
    },
  };

  try {
    const response = await fetch(url, fetchOptions);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || `HTTP error ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    console.error('Fetch error:', error.message);
    throw error;
  }
};

/**
 * Enhanced version of fetchWithCORS with automatic retry for network errors
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @param {number} retries - Number of retries (default: 3)
 * @returns {Promise<any>} - Promise that resolves to the parsed response
 */
export const fetchWithRetry = async (url, options = {}, retries = 3) => {
  try {
    return await fetchWithCORS(url, options);
  } catch (error) {
    if (retries === 0 || !error.message.includes('network')) {
      throw error;
    }
    
    console.log(`Retrying fetch to ${url}, ${retries} attempts left`);
    return fetchWithRetry(url, options, retries - 1);
  }
}; 