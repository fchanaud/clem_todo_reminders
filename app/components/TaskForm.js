import { useState } from 'react';
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
  const [phoneNumber, setPhoneNumber] = useState('+33668695116');
  const [enableWhatsApp, setEnableWhatsApp] = useState(true);

  const capitalizeFirstLetter = (string) => {
    return string.charAt(0).toUpperCase() + string.slice(1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Combine date and hour into ISO string
      const combinedDueTime = new Date(`${dueDate}T${dueHour}:00:00`);
      
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

      // Always add the WhatsApp number - Meta API format (no "whatsapp:" prefix)
      requestBody.phone_number = phoneNumber.startsWith('+') ? phoneNumber : '+' + phoneNumber;

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

      toast.success('Task created successfully!');
      setTitle('');
      setDueDate('');
      setDueHour('09');
      setPriority('Medium');
      setUseSingleReminder(false);
      setHoursBefore('2');
      // Keep phone number and WhatsApp preference for next tasks
      onTaskAdded();
    } catch (error) {
      toast.error('Failed to create task');
      console.error('Error:', error);
    }
  };

  // Generate hours for the select input (00-23)
  const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
  
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
            onChange={(e) => setDueDate(e.target.value)}
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
            {hours.map((hour) => (
              <option key={hour} value={hour}>
                {hour}:00
              </option>
            ))}
          </select>
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

        {/* WhatsApp Reminder Section */}
        <div className="sm:col-span-3 pt-2 border-t border-gray-100">
          <div className="flex items-center space-x-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-base font-medium text-gray-700">
              WhatsApp reminders enabled
            </span>
          </div>
          
          <div className="mt-3">
            <label htmlFor="phoneNumber" className="block text-sm font-medium text-gray-700 mb-1">
              WhatsApp phone number
            </label>
            <input
              type="tel"
              id="phoneNumber"
              value={phoneNumber}
              readOnly
              className="form-input mt-1 block w-full rounded-lg border-gray-200 bg-gray-50 py-2 px-3 text-gray-700 shadow-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              WhatsApp messages will be sent to this number
            </p>
          </div>
        </div>
      </div>

      <button
        type="submit"
        className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-base font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
      >
        Add Task
      </button>
    </form>
  );
} 