/**
 * B2C Portal Entry Point
 * Renders the B2C application for personal workspace users
 */
import { createRoot } from 'react-dom/client';
import B2CApp from './modules/b2c/B2CApp';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<B2CApp />);
