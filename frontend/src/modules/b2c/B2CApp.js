/**
 * B2C Application Root Component
 * Personal workspace portal for individual users
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import WelcomePage from './pages/WelcomePage';
import '../../styles/main.css';

function B2CApp() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<WelcomePage />} />
                <Route path="*" element={<WelcomePage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default B2CApp;
