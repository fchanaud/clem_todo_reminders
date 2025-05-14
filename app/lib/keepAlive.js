/**
 * KeepAlive utility
 * 
 * Sends periodic pings to keep the backend server alive on Render.com
 * Prevents the app from going to sleep after 15 minutes of inactivity
 */

// Get API URL with a more robust approach
const getApiUrl = () => {
  // Use the environment variable if available
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // In the browser, if we're in production and no env var is set,
  // construct the API URL from the current origin + known backend path
  if (typeof window !== 'undefined') {
    const currentOrigin = window.location.origin;
    // If we're on the production frontend domain, use the production backend
    if (currentOrigin.includes('clem-todo-frontend')) {
      return 'https://clem-todo-backend.onrender.com';
    }
  }
  
  // Fallback to localhost for development
  return 'http://localhost:8000';
};

/**
 * Initialize the keep-alive service with periodic pings to the backend
 * 
 * @param {number} interval - Interval in milliseconds between pings (default: 10 minutes)
 * @returns {Object} - Object with start and stop methods to control the keep-alive service
 */
export function initKeepAlive(interval = 10 * 60 * 1000) {
  let pingInterval = null;
  let isActive = false;
  
  // Send a ping to the backend
  const pingServer = async () => {
    try {
      const API_URL = getApiUrl();
      const response = await fetch(`${API_URL}/api/ping`);
      
      if (response.ok) {
        console.log('Keep-alive ping sent successfully', new Date().toISOString());
      } else {
        console.error('Keep-alive ping failed:', response.status);
      }
    } catch (error) {
      console.error('Error sending keep-alive ping:', error);
    }
  };
  
  // Start the keep-alive service
  const start = () => {
    if (isActive) return;
    
    isActive = true;
    
    // Send initial ping
    pingServer();
    
    // Set up interval for regular pings
    pingInterval = setInterval(pingServer, interval);
    console.log(`Keep-alive service started with ${interval/1000}s interval`);
    
    return () => stop();
  };
  
  // Stop the keep-alive service
  const stop = () => {
    if (!isActive) return;
    
    clearInterval(pingInterval);
    pingInterval = null;
    isActive = false;
    console.log('Keep-alive service stopped');
  };
  
  return {
    start,
    stop,
    isActive: () => isActive
  };
}

// Export a singleton instance with default settings
export const keepAliveService = initKeepAlive(); 