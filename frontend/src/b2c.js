/**
 * B2C Portal Entry Point
 * Renders the B2C application for personal workspace users
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './styles/main.css';
import B2CApp from './modules/b2c/B2CApp';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <BrowserRouter>
        <B2CApp />
    </BrowserRouter>
);
