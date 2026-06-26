import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@xyflow/react/dist/style.css';
import './styles.css';
import './production.css';
import App from './App';
import LocalizationLauncher from './LocalizationLauncher';
import ProductionLauncher from './ProductionLauncher';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 15000,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <LocalizationLauncher />
      <ProductionLauncher />
    </QueryClientProvider>
  </React.StrictMode>,
);
