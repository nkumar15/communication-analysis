
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './web/pages/LoginPage';
import SignupPage from './web/pages/SignupPage';
import DashboardPage from './web/pages/DashboardPage';
import WorkspacePage from './web/pages/WorkspacePage';
import LandingPage from '../../pages/LandingPage';
import '../../styles/main.css';

const B2CApp = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/workspace/:workspaceId" element={<WorkspacePage />} />
            </Routes>
        </BrowserRouter>
    );
};

export default B2CApp;
