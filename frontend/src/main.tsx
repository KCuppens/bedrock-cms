import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { reportWebVitals } from './utils/performance'

// Start measuring web vitals
reportWebVitals();

createRoot(document.getElementById("root")!).render(<App />);
