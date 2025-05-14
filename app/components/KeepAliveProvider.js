'use client';

import { useEffect } from 'react';
import { keepAliveService } from '../lib/keepAlive';

/**
 * Component that initializes the keep-alive service to prevent the app from sleeping
 * on Render.com after 15 minutes of inactivity.
 * 
 * This sends periodic ping requests to the backend to keep it alive.
 */
export default function KeepAliveProvider() {
  useEffect(() => {
    // Only start the service in production to avoid unnecessary pings during development
    if (process.env.NODE_ENV === 'production') {
      // Start the keep-alive service
      const stopKeepAlive = keepAliveService.start();
      
      // Clean up the service when the component unmounts
      return () => {
        stopKeepAlive();
      };
    }
    
    return () => {};
  }, []);

  // This component doesn't render anything
  return null;
} 