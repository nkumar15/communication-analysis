/**
 * Platform Portal Entry Point
 * Renders the Platform admin console for SaaS operators
 */
import { createRoot } from 'react-dom/client';
import PlatformApp from './modules/platform/PlatformApp';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<PlatformApp />);
