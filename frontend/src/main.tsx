import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { NotificationProvider } from './components/NotificationProvider';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <NotificationProvider>
      <App />
    </NotificationProvider>
  </StrictMode>
);
