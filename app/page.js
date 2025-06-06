"use client";

import { useState, useEffect, useRef } from "react";
import { Toaster } from "react-hot-toast";
import TaskForm from "./components/TaskForm";
import TaskList from "./components/TaskList";
import toast from "react-hot-toast";

export default function Home() {
  const [tasks, setTasks] = useState({
    incomplete_tasks: [],
    completed_tasks: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showPwaPrompt, setShowPwaPrompt] = useState(false);
  const [taskAdded, setTaskAdded] = useState(false);
  const listEndRef = useRef(null);
  const taskListRef = useRef(null);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/api/tasks`);
      if (!response.ok) {
        throw new Error('Failed to fetch tasks');
      }
      const data = await response.json();
      setTasks(data);
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError('Failed to load tasks. Please try again later.');
      toast.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleTaskAdded = async (newTask) => {
    if (newTask) {
      try {
        // When a new task is created, fetch it with its reminders
        const apiUrl = getApiUrl();
        const response = await fetch(`${apiUrl}/api/tasks`);
        
        if (response.ok) {
          const data = await response.json();
          setTasks(data);
        } else {
          // If fetch fails, still add the task but without reminders
          setTasks(prevTasks => ({
            ...prevTasks,
            incomplete_tasks: [...prevTasks.incomplete_tasks, newTask]
          }));
          console.warn('Could not fetch tasks with reminders after task creation');
        }
      } catch (error) {
        // Fallback to just adding the task without fetching
        console.error('Error fetching newly created task with reminders:', error);
        setTasks(prevTasks => ({
          ...prevTasks,
          incomplete_tasks: [...prevTasks.incomplete_tasks, newTask]
        }));
      }
      
      // Signal that a task was added to trigger scrolling
      setTaskAdded(true);
    } else {
      // Fall back to refetching if no task data provided
      await fetchTasks();
      setTaskAdded(true);
    }
  };

  // Function to get API URL - same as in other components
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

  // Enhanced scroll functionality for better compatibility with iOS PWA
  useEffect(() => {
    // Only attempt to scroll if a task was added
    if (taskAdded) {
      // Add a small delay to ensure reminders are loaded before scrolling
      const scrollTimeout = setTimeout(() => {
        try {
          // First, try with smooth scrolling
          if (listEndRef.current) {
            console.log('Attempting to scroll to new task with smooth behavior');
            listEndRef.current.scrollIntoView({ 
              behavior: 'smooth', 
              block: 'end'
            });
            
            // Set a backup direct scroll in case smooth scrolling doesn't work properly on iOS
            setTimeout(() => {
              if (listEndRef.current) {
                window.scrollTo(0, document.body.scrollHeight);
                console.log('Executed backup scroll to end of page');
              }
            }, 300);
          } else {
            // Fallback to window scroll
            console.log('listEndRef not available, using window.scrollTo');
            window.scrollTo(0, document.body.scrollHeight);
          }
        } catch (e) {
          // Final fallback if all else fails
          console.error('Error during scroll:', e);
          window.scrollTo(0, document.body.scrollHeight);
        }
        
        // Reset taskAdded flag
        setTaskAdded(false);
      }, 500); // 500ms delay to allow reminders to load
      
      return () => clearTimeout(scrollTimeout);
    }
  }, [taskAdded, tasks]);

  useEffect(() => {
    fetchTasks();
    
    // Check if this is an iOS device and not in standalone mode (PWA)
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    
    if (isIOS && !isStandalone && !localStorage.getItem('pwaPromptDismissed')) {
      // Show PWA prompt after 2 seconds delay
      const timer = setTimeout(() => {
        setShowPwaPrompt(true);
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, []);
  
  const dismissPwaPrompt = () => {
    setShowPwaPrompt(false);
    localStorage.setItem('pwaPromptDismissed', 'true');
  };

  return (
    <main className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">Clem Todo Reminders</h1>
        </div>
        
        {/* PWA installation prompt for iOS */}
        {showPwaPrompt && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg shadow-sm relative">
            <button 
              onClick={dismissPwaPrompt}
              className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
              aria-label="Dismiss"
            >
              ✕
            </button>
            <p className="font-medium text-blue-800">📱 Install as App</p>
            <p className="text-sm text-blue-700 mt-1">
              Add this app to your home screen for a better experience! Tap the share icon and select "Add to Home Screen".
            </p>
          </div>
        )}

        <TaskForm onTaskAdded={handleTaskAdded} />
        <div ref={taskListRef}>
          <TaskList 
            tasks={tasks} 
            loading={loading} 
            error={error}
            onTasksChanged={fetchTasks}
          />
          {/* This div is the target for scrolling to the end of the task list */}
          <div ref={listEndRef} className="h-4 w-full" />
        </div>
      </div>
      <Toaster position="bottom-center" />
    </main>
  );
} 