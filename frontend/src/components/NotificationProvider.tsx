import React, { createContext, useContext, useState } from 'react';

interface Notification {
  id: number;
  message: string;
  type?: 'success' | 'error' | 'info';
}

interface NotificationContextValue {
  notify: (message: string, type?: 'success' | 'error' | 'info') => void;
}

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const notify = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    const id = Date.now() + Math.random();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  return (
    <NotificationContext.Provider value={{ notify }}>
      {children}
      <div className="fixed top-4 right-4 space-y-2 z-50">
        {notifications.map(n => (
          <div
            key={n.id}
            className={`px-4 py-2 rounded shadow-lg text-white ${n.type === 'error'
                ? 'bg-red-600'
                : n.type === 'info'
                  ? 'bg-blue-600'
                  : 'bg-green-600'
              }`}
          >
            {n.message}
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotification() {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return ctx.notify;
}
