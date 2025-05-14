import { useState, useEffect } from 'react';
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

export default function TaskForm({ onTaskAdded }) {
  const [title, setTitle] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [dueHour, setDueHour] = useState('09');
  const [priority, setPriority] = useState('Medium');
  const [useSingleReminder, setUseSingleReminder] = useState(false);
  const [hoursBefore, setHoursBefore] = useState('2');
  const [availableHours, setAvailableHours] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Effect to update available hours when date changes
  useEffect(() => {
    updateAvailableHours();
  }, [dueDate]);

  // Function to update available hours based on current date
  const updateAvailableHours = () => {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    
    // Generate all hours (00-23)
    const allHours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
    
    // If the selected date is today, filter out past hours
    if (dueDate === today) {
      const currentHour = now.getHours();
      const futureHours = allHours.filter(hour => parseInt(hour) > currentHour);
      setAvailableHours(futureHours);
      
      // If the currently selected hour is in the past, reset it to the next available hour
      if (parseInt(dueHour) <= currentHour) {
        // Set to the next hour if available, otherwise the first available hour
        const nextHour = (currentHour + 1).toString().padStart(2, '0');
        setDueHour(futureHours.includes(nextHour) ? nextHour : (futureHours[0] || '00'));
      }
    } else {
      // If not today, all hours are available
      setAvailableHours(allHours);
    }
  };

  const capitalizeFirstLetter = (string) => {
    return string.charAt(0).toUpperCase() + string.slice(1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      // Combine date and hour into ISO string
      const combinedDueTime = new Date(`${dueDate}T${dueHour}:00:00`);
      const now = new Date();
      
      // Check if the due time is in the past
      if (combinedDueTime <= now) {
        toast.error('Task due time cannot be in the past');
        setIsSubmitting(false);
        return;
      }
      
      const requestBody = {
        title: capitalizeFirstLetter(title.trim()),
        due_time: combinedDueTime.toISOString(),
        priority,
      };

      if (useSingleReminder) {
        // Add single reminder configuration
        requestBody.single_reminder = true;
        requestBody.hours_before = parseInt(hoursBefore);
      }

      const response = await fetch(`${API_URL}/api/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error('Failed to create task');
      }

      const createdTask = await response.json();
      
      toast.success('Task created successfully!');
      
      // Reset form fields
      setTitle('');
      setDueDate('');
      setDueHour('09');
      setPriority('Medium');
      setUseSingleReminder(false);
      setHoursBefore('2');
      
      // Notify parent with the new task data
      onTaskAdded(createdTask);
    } catch (error) {
      toast.error('Failed to create task');
      console.error('Error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle date change
  const handleDateChange = (e) => {
    setDueDate(e.target.value);
  };
  
  // Generate hours before options (1-24)
  const hoursBeforeOptions = Array.from({ length: 24 }, (_, i) => (i + 1).toString());

  return (
    <form onSubmit={handleSubmit} className="p-6 space-y-6">
      <div>
        <label htmlFor="title" className="block text-base font-medium text-gray-700 mb-1">
          What needs to be done?
        </label>
        <input
          type="text"
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="form-input mt-1 block w-full rounded-lg border-gray-300 bg-white py-3 px-4 text-gray-900 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          placeholder="Enter task title..."
        />
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <label htmlFor="dueDate" className="block text-base font-medium text-gray-700 mb-1">
            Due Date
          </label>
          <input
            type="date"
            id="dueDate"
            value={dueDate}
            onChange={handleDateChange}
            required
            min={new Date().toISOString().split('T')[0]}
            className="form-input mt-1 block w-full rounded-lg border-gray-300 bg-white py-3 px-4 text-gray-900 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          />
        </div>

        <div>
          <label htmlFor="dueHour" className="block text-base font-medium text-gray-700 mb-1">
            Hour
          </label>
          <select
            id="dueHour"
            value={dueHour}
            onChange={(e) => setDueHour(e.target.value)}
            required
            className="form-select mt-1 block w-full rounded-lg border-gray-300 bg-white py-3 px-4 text-gray-900 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          >
            {availableHours.length > 0 ? (
              availableHours.map((hour) => (
                <option key={hour} value={hour}>
                  {hour}:00
                </option>
              ))
            ) : (
              <option value={dueHour}>{dueHour}:00</option>
            )}
          </select>
          {availableHours.length === 0 && dueDate && (
            <p className="text-xs text-gray-500 mt-1">
              Please select a date first
            </p>
          )}
        </div>

        <div className="sm:col-span-3">
          <label htmlFor="priority" className="block text-base font-medium text-gray-700 mb-1">
            Priority
          </label>
          <select
            id="priority"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="form-select mt-1 block w-full rounded-lg border-gray-300 bg-white py-3 px-4 text-gray-900 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
          </select>
        </div>

        <div className="sm:col-span-3">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="useSingleReminder"
              checked={useSingleReminder}
              onChange={(e) => setUseSingleReminder(e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label htmlFor="useSingleReminder" className="text-base font-medium text-gray-700">
              Use single reminder
            </label>
          </div>
          
          {useSingleReminder && (
            <div className="mt-3">
              <label htmlFor="hoursBefore" className="block text-sm font-medium text-gray-700 mb-1">
                Hours before due time
              </label>
              <select
                id="hoursBefore"
                value={hoursBefore}
                onChange={(e) => setHoursBefore(e.target.value)}
                className="form-select mt-1 block w-full rounded-lg border-gray-300 bg-white py-2 px-3 text-gray-900 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              >
                {hoursBeforeOptions.map((hours) => (
                  <option key={hours} value={hours}>
                    {hours} hour{hours === '1' ? '' : 's'}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-base font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors disabled:opacity-70"
      >
        {isSubmitting ? (
          <>
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Creating...
          </>
        ) : (
          'Add Task'
        )}
      </button>
    </form>
  );
} 