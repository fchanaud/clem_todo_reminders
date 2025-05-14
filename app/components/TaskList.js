import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import toast from 'react-hot-toast';

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

const API_URL = getApiUrl();

export default function TaskList({ tasks, loading, error, onTasksChanged }) {
  const [incompleteTasks, setIncompleteTasks] = useState([]);
  const [completedTasks, setCompletedTasks] = useState([]);
  const [showCompleted, setShowCompleted] = useState(false);

  // Sort and set tasks when they change
  useEffect(() => {
    if (tasks && tasks.incomplete_tasks) {
      // Sort incomplete tasks by due_time (ascending - upcoming first)
      const sortedIncompleteTasks = [...tasks.incomplete_tasks].sort((a, b) => {
        return new Date(a.due_time) - new Date(b.due_time);
      });
      
      setIncompleteTasks(sortedIncompleteTasks);
      setCompletedTasks(tasks.completed_tasks || []);
    }
  }, [tasks]);

  const handleComplete = async (taskId) => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/${taskId}/complete`, {
        method: 'PATCH',
      });

      if (!response.ok) {
        throw new Error('Failed to update task');
      }
      
      toast.success('Task completed!');
      
      // Update state locally instead of refetching
      const task = incompleteTasks.find(t => t.id === taskId);
      if (task) {
        // Remove from incomplete tasks
        setIncompleteTasks(prev => prev.filter(t => t.id !== taskId));
        
        // Add to completed tasks with completed_at field
        const completedTask = {
          ...task,
          completed: true,
          completed_at: new Date().toISOString()
        };
        setCompletedTasks(prev => [completedTask, ...prev]);
      }
      
      // Notify parent component that tasks have changed
      if (onTasksChanged) onTasksChanged();
    } catch (error) {
      console.error('Error completing task:', error.message);
      toast.error('Failed to update task');
    }
  };

  const handleDelete = async (taskId) => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete task');
      }
      
      toast.success('Task deleted successfully');
      
      // Update state locally instead of refetching
      setIncompleteTasks(prev => prev.filter(t => t.id !== taskId));
      setCompletedTasks(prev => prev.filter(t => t.id !== taskId));
      
      // Notify parent component that tasks have changed
      if (onTasksChanged) onTasksChanged();
    } catch (error) {
      console.error('Error deleting task:', error.message);
      toast.error('Failed to delete task');
    }
  };

  const TaskCard = ({ task, isCompleted = false, handleComplete, handleDelete }) => (
    <div className="bg-white rounded-lg shadow-sm p-4 mb-3 border border-gray-100">
      <div className="flex flex-col">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-gray-900">{task.title}</h3>
          <div className="mt-1 text-sm text-gray-500">
            Due: {format(new Date(task.due_time), 'PPP p').replace(/:\d{2}(?!.*:)/, '')}
          </div>
          <div className="mt-2 flex items-center space-x-2">
            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full
              ${task.priority === 'High' ? 'bg-red-100 text-red-800' : 
                task.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' : 
                'bg-green-100 text-green-800'}`}>
              {task.priority}
            </span>
            {task.reminders && task.reminders.length > 0 && (
              <span className="text-xs text-gray-500">
                {task.reminders.length} reminder{task.reminders.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
          
          {/* Enhanced reminder display for better iOS visibility */}
          {task.reminders && task.reminders.length > 0 && (
            <div className="mt-3 border-t border-gray-100 pt-2">
              <p className="text-xs font-medium text-gray-700 mb-1">Reminders:</p>
              <div className="space-y-2">
                {task.reminders.map((reminder, index) => {
                  // Ensure valid date by safely parsing it
                  let reminderDate;
                  try {
                    reminderDate = new Date(reminder.reminder_time);
                    // Check if valid date
                    if (isNaN(reminderDate.getTime())) {
                      throw new Error('Invalid date');
                    }
                  } catch (e) {
                    return (
                      <div key={reminder.id || index} className="text-xs text-red-500">
                        Invalid reminder time
                      </div>
                    );
                  }
                  
                  return (
                    <div key={reminder.id || index} 
                      className="text-xs bg-gray-50 p-2 rounded flex items-center text-gray-700">
                      <span className="mr-1">🔔</span>
                      {format(reminderDate, 'EEE, MMM d, h:mm a')}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          {isCompleted && task.completed_at && (
            <div className="mt-2 text-xs text-gray-500">
              Completed: {format(new Date(task.completed_at), 'PPP p').replace(/:\d{2}(?!.*:)/, '')}
            </div>
          )}
        </div>
        
        {/* Action Buttons - Made larger and more touch-friendly */}
        <div className="mt-4 flex justify-end space-x-3">
          {!isCompleted && (
            <button
              onClick={() => handleComplete(task.id)}
              className="flex-1 py-2 px-4 bg-green-100 text-green-700 rounded-lg font-medium hover:bg-green-200 active:bg-green-300 transition-colors duration-200"
            >
              Complete
            </button>
          )}
          <button
            onClick={() => handleDelete(task.id)}
            className="flex-1 py-2 px-4 bg-red-100 text-red-700 rounded-lg font-medium hover:bg-red-200 active:bg-red-300 transition-colors duration-200"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="p-4 text-center text-red-500">{error}</div>;
  }

  if (incompleteTasks.length === 0 && completedTasks.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        No tasks found. Create one to get started!
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="space-y-4">
        {/* Incomplete Tasks */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Tasks</h2>
          <div className="space-y-3">
            {incompleteTasks.map((task) => (
              <TaskCard 
                key={task.id} 
                task={task} 
                handleComplete={handleComplete}
                handleDelete={handleDelete}
              />
            ))}
          </div>
        </div>

        {/* Completed Tasks */}
        {completedTasks.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Completed Tasks</h2>
              <button
                onClick={() => setShowCompleted(!showCompleted)}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                {showCompleted ? 'Hide' : 'Show'}
              </button>
            </div>
            {showCompleted && (
              <div className="space-y-3">
                {completedTasks.map((task) => (
                  <TaskCard 
                    key={task.id} 
                    task={task} 
                    isCompleted 
                    handleComplete={handleComplete}
                    handleDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
} 