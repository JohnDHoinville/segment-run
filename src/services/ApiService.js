import { API_URL } from '../config';
import { fetchWithCORS } from './fetchService';

let cachedRunHistory = null;
let lastFetchTime = 0;
const CACHE_EXPIRY = 5 * 60 * 1000; // 5 minutes in milliseconds

/**
 * Fetch run history with caching
 * @returns {Promise<Array>} Promise that resolves to the runs array
 */
export const fetchRunHistory = async (forceRefresh = false) => {
  const now = Date.now();
  const cacheExpired = now - lastFetchTime > CACHE_EXPIRY;
  
  // Return cached data if available and not expired
  if (cachedRunHistory && !cacheExpired && !forceRefresh) {
    console.log('Using cached run history');
    return cachedRunHistory;
  }
  
  console.log('Fetching fresh run history data...');
  try {
    const data = await fetchWithCORS(`${API_URL}/runs`);
    
    // Ensure we have an array
    const runsArray = Array.isArray(data) ? data : [];
    
    // Update cache
    cachedRunHistory = runsArray;
    lastFetchTime = now;
    
    return runsArray;
  } catch (error) {
    console.error('Error fetching runs history:', error);
    // If cache exists but is expired, return it as fallback
    if (cachedRunHistory) {
      console.log('Using expired cache as fallback due to fetch error');
      return cachedRunHistory;
    }
    // If no cache, return empty array
    return [];
  }
};

/**
 * Clear the run history cache
 */
export const clearCache = () => {
  console.log('Clearing run history cache');
  cachedRunHistory = null;
  lastFetchTime = 0;
};

/**
 * Get a single run by ID
 * @param {number} runId The run ID to fetch
 * @returns {Promise<Object>} Promise that resolves to the run object
 */
export const fetchRunById = async (runId) => {
  try {
    const runs = await fetchRunHistory();
    return runs.find(run => run.id === runId) || null;
  } catch (error) {
    console.error(`Error fetching run with ID ${runId}:`, error);
    return null;
  }
};

/**
 * Delete a run by ID
 * @param {number} runId The run ID to delete
 * @returns {Promise<boolean>} Promise that resolves to a success boolean
 */
export const deleteRun = async (runId) => {
  try {
    await fetchWithCORS(`${API_URL}/runs/${runId}`, {
      method: 'DELETE',
    });
    
    // Clear cache after deletion
    clearCache();
    return true;
  } catch (error) {
    console.error(`Error deleting run with ID ${runId}:`, error);
    return false;
  }
}; 