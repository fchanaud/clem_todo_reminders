"use client";

import { useState, useEffect } from "react";
import { Toaster } from "react-hot-toast";
import TaskForm from "./components/TaskForm";
import TaskList from "./components/TaskList";

export default function Home() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // We don't need to fetch tasks when the component mounts
  // This was causing an extra API call that duplicates what TaskList already does
  // useEffect(() => {
  //  handleTaskAdded();
  // }, []);

  const handleTaskAdded = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-12 text-center">
          Clem's TODO Reminders
        </h1>
        
        <div className="space-y-8">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <TaskForm onTaskAdded={handleTaskAdded} />
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <TaskList refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </div>
      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#333',
            color: '#fff',
            borderRadius: '8px',
          },
          success: {
            duration: 3000,
          },
          error: {
            duration: 4000,
          },
        }}
      />
    </main>
  );
} 