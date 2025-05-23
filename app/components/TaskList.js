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
  return 'http://127.0.0.1:8000';
};

const API_URL = getApiUrl();

export default function TaskList({ tasks, loading, error, onTasksChanged }) {
  const [incompleteTasks, setIncompleteTasks] = useState([]);
  const [completedTasks, setCompletedTasks] = useState([]);
  const [showCompleted, setShowCompleted] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [editDate, setEditDate] = useState('');
  const [editTime, setEditTime] = useState('');

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

  const handleEditDueDate = async (taskId) => {
    const task = incompleteTasks.find(t => t.id === taskId);
    if (!task) return;

    // Convert current due_time to date and time for the inputs
    const currentDate = new Date(task.due_time);
    const dateStr = currentDate.toISOString().split('T')[0]; // YYYY-MM-DD
    const timeStr = currentDate.toTimeString().slice(0, 5); // HH:MM

    setEditingTask(taskId);
    setEditDate(dateStr);
    setEditTime(timeStr);
  };

  const handleSaveEdit = async (taskId) => {
    try {
      // Combine date and time into a new due_time
      console.log('Edit inputs - Date:', editDate, 'Time:', editTime);
      const newDueTime = new Date(`${editDate}T${editTime}:00.000Z`).toISOString();
      console.log('Formatted due_time:', newDueTime);
      console.log('API URL:', `${API_URL}/api/tasks/${taskId}`);

      const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          due_time: newDueTime
        }),
      });

      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error text:', errorText);
        throw new Error(`Failed to update due date: ${response.status} - ${errorText}`);
      }

      toast.success('Due date updated successfully!');
      
      // Update state locally
      setIncompleteTasks(prev => prev.map(t => 
        t.id === taskId 
          ? { ...t, due_time: newDueTime }
          : t
      ));
      
      // Notify parent component that tasks have changed
      if (onTasksChanged) onTasksChanged();
      
      // Exit edit mode
      setEditingTask(null);
      setEditDate('');
      setEditTime('');
    } catch (error) {
      console.error('Error updating due date:', error);
      toast.error('Failed to update due date');
    }
  };

  const handleCancelEdit = () => {
    setEditingTask(null);
    setEditDate('');
    setEditTime('');
  };

  const TaskCard = ({ task, isCompleted = false }) => (
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 mb-2">
      {/* Main Content - Compact Layout */}
      <div className="p-3">
        {/* Header Row */}
        <div className="flex items-start justify-between mb-1">
          <h3 className="text-base font-medium text-gray-900 flex-1 pr-2 leading-tight">
            {task.title}
          </h3>
          <span className={`px-1.5 py-0.5 text-xs font-semibold rounded-full shrink-0
            ${task.priority === 'High' ? 'bg-red-100 text-red-800' : 
              task.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' : 
              'bg-green-100 text-green-800'}`}>
            {task.priority}
          </span>
        </div>
        
        {/* Due Date Row */}
        <div className="flex items-center justify-between mb-2">
          {editingTask === task.id ? (
            // Edit mode - show date and time inputs
            <div className="flex items-center gap-2 flex-1">
              <input
                type="date"
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
                className="text-sm border border-gray-300 rounded px-2 py-1 bg-white"
              />
              <input
                type="time"
                value={editTime}
                onChange={(e) => setEditTime(e.target.value)}
                className="text-sm border border-gray-300 rounded px-2 py-1 bg-white"
              />
            </div>
          ) : (
            // View mode - show formatted date
            <div className="text-sm text-gray-600">
              <span className="font-medium">Due:</span> {format(new Date(task.due_time), 'MMM d, h:mm a')}
            </div>
          )}
          {task.reminders && task.reminders.length > 0 && !editingTask && (
            <span className="text-xs text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded">
              {task.reminders.length} 📅
            </span>
          )}
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-2 mb-2">
          {/* Temporarily remove edited indicator until fields are added to database
          {task.edited && (
            <span className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-medium">
              ✏️ Edited
            </span>
          )}
          */}
          {isCompleted && task.completed_at && (
            <span className="text-xs text-gray-500">
              Done: {format(new Date(task.completed_at), 'MMM d, h:mm a')}
            </span>
          )}
        </div>

        {/* Action Buttons Row - Minimalist */}
        <div className="flex items-center gap-1">
          {editingTask === task.id ? (
            // Edit mode - show save/cancel buttons
            <>
              <button
                onClick={() => handleSaveEdit(task.id)}
                className="flex-1 py-1.5 px-2 bg-green-50 hover:bg-green-100 active:bg-green-200 rounded text-green-700 transition-colors duration-150 text-sm font-medium"
                title="Save changes"
              >
                💾
              </button>
              <button
                onClick={handleCancelEdit}
                className="flex-1 py-1.5 px-2 bg-gray-50 hover:bg-gray-100 active:bg-gray-200 rounded text-gray-700 transition-colors duration-150 text-sm font-medium"
                title="Cancel editing"
              >
                ✖️
              </button>
            </>
          ) : (
            !isCompleted && (
              <>
                {/* Complete Button */}
                <button
                  onClick={() => handleComplete(task.id)}
                  className="flex-1 py-1.5 px-2 bg-green-50 hover:bg-green-100 active:bg-green-200 rounded text-green-700 transition-colors duration-150 text-sm font-medium"
                  title="Complete task"
                >
                  ✓
                </button>
                
                {/* Edit Button */}
                <button
                  onClick={() => handleEditDueDate(task.id)}
                  className="flex-1 py-1.5 px-2 bg-blue-50 hover:bg-blue-100 active:bg-blue-200 rounded text-blue-700 transition-colors duration-150 text-sm font-medium"
                  title="Edit due date"
                >
                  📝
                </button>
              </>
            )
          )}
          
          {/* Delete Button - always show unless editing */}
          {editingTask !== task.id && (
            <button
              onClick={() => handleDelete(task.id)}
              className="flex-1 py-1.5 px-2 bg-red-50 hover:bg-red-100 active:bg-red-200 rounded text-red-700 transition-colors duration-150 text-sm font-medium"
              title="Delete task"
            >
              🗑️
            </button>
          )}
        </div>
      </div>

      {/* Expanded Reminders - Only show if expanded */}
      {task.reminders && task.reminders.length > 0 && (
        <div className="px-3 pb-3 border-t border-gray-50">
          <div className="text-xs text-gray-600 space-y-1 mt-2">
            {task.reminders.slice(0, 2).map((reminder, index) => {
              let reminderDate;
              try {
                reminderDate = new Date(reminder.reminder_time);
                if (isNaN(reminderDate.getTime())) {
                  throw new Error('Invalid date');
                }
              } catch (e) {
                return (
                  <div key={reminder.id || index} className="text-red-500">
                    Invalid reminder
                  </div>
                );
              }
              
              return (
                <div key={reminder.id || index} className="flex items-center gap-1">
                  <span>🔔</span>
                  <span>{format(reminderDate, 'MMM d, h:mm a')}</span>
                </div>
              );
            })}
            {task.reminders.length > 2 && (
              <div className="text-gray-400">
                +{task.reminders.length - 2} more
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-3 bg-gray-200 rounded w-3/4"></div>
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          <div className="h-3 bg-gray-200 rounded w-2/3"></div>
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
    <div className="p-3">
      <div className="space-y-4">
        {/* Incomplete Tasks */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Active Tasks</h2>
          <div className="space-y-2">
            {incompleteTasks.map((task) => (
              <TaskCard 
                key={task.id} 
                task={task}
              />
            ))}
          </div>
        </div>

        {/* Completed Tasks */}
        {completedTasks.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-900">Completed Tasks</h2>
              <button
                onClick={() => setShowCompleted(!showCompleted)}
                className="text-sm text-gray-600 hover:text-gray-900 px-2 py-1 rounded"
              >
                {showCompleted ? 'Hide' : 'Show'}
              </button>
            </div>
            {showCompleted && (
              <div className="space-y-2">
                {completedTasks.map((task) => (
                  <TaskCard 
                    key={task.id} 
                    task={task} 
                    isCompleted 
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