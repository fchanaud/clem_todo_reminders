import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import toast from 'react-hot-toast';

interface Reminder {
  id: string;
  task_id: string;
  reminder_time: string;
}

interface Task {
  id: string;
  title: string;
  due_time: string;
  priority: string;
  completed: boolean;
  completed_at?: string;
  reminders: Reminder[];
}

interface TaskListProps {
  refreshTrigger: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TaskList({ refreshTrigger }: TaskListProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      console.log('Fetching from:', `${API_URL}/api/tasks`);
      const response = await fetch(`${API_URL}/api/tasks`);
      if (!response.ok) {
        console.error('Response not OK:', response.status, response.statusText);
        throw new Error(`Failed to fetch tasks: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Fetched data type:', typeof data, 'Data:', data);
      
      // API returns { incomplete_tasks, completed_tasks } format
      if (data && data.incomplete_tasks && Array.isArray(data.incomplete_tasks)) {
        setIncompleteTasks(data.incomplete_tasks);
        setCompletedTasks(data.completed_tasks);
      } else if (Array.isArray(data)) {
        // Handle case where API returns array directly
        setIncompleteTasks(data);
        setCompletedTasks(data);
      } else {
        console.error('Unexpected data format:', data);
        setIncompleteTasks([]);
        setCompletedTasks([]);
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to fetch tasks');
      setIncompleteTasks([]);
      setCompletedTasks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [refreshTrigger]);

  const handleComplete = async (taskId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/${taskId}/complete`, {
        method: 'PATCH',
      });

      if (!response.ok) {
        throw new Error('Failed to update task');
      }

      fetchTasks(); // Refresh the task list
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to update task');
    }
  };

  const handleDelete = async (taskId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete task');
      }

      fetchTasks(); // Refresh the task list
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to delete task');
    }
  };

  const TaskCard = ({ task, isCompleted = false }: { task: Task; isCompleted?: boolean }) => (
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
            {task.reminders.length > 0 && (
              <span className="text-xs text-gray-500">
                {task.reminders.length} reminder{task.reminders.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
          {task.reminders.length > 0 && (
            <div className="mt-2 space-y-1">
              {task.reminders.map((reminder) => (
                <div key={reminder.id} className="text-xs text-gray-500">
                  {format(new Date(reminder.reminder_time), 'PPP p').replace(/:\d{2}(?!.*:)/, '')}
                </div>
              ))}
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

  if (tasks.length === 0) {
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
            {tasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
} 