
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signInWithEmailAndPassword, signInWithCustomToken } from 'firebase/auth';
import { auth } from '../../../../core/firebase/b2c-config';
import AuthButtons from '../components/AuthButtons';

const LoginPage = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    // E2E Test Backdoor
    React.useEffect(() => {
        const customToken = localStorage.getItem('custom_token');
        if (customToken) {
            console.log('🧪 E2E Backdoor: Found custom token, logging in...');
            localStorage.removeItem('custom_token');
            setLoading(true);
            signInWithCustomToken(auth, customToken)
                .then((userCredential) => handleAuthSuccess(userCredential.user))
                .catch((e) => {
                    console.error('E2E Backdoor failed', e);
                    setError(e.message);
                    setLoading(false);
                });
        }
    }, []);

    const handleAuthSuccess = async (user) => {
        try {
            setLoading(true);
            const idToken = await user.getIdToken(true); // Force refresh to get latest claims (e.g. email_verified)

            const response = await fetch('/api/b2c/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_token: idToken }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Login failed');
            }

            navigate('/dashboard');
        } catch (err) {
            console.error(err);
            setError(err.message);
            setLoading(false);
        }
    };

    const handleEmailLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            await handleAuthSuccess(userCredential.user);
        } catch (err) {
            setError('Invalid email or password');
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-card">
                <div className="login-header">
                    <div className="logo-container">
                        <div className="logo-icon">🚀</div>
                    </div>
                    <h1>Welcome Back</h1>
                    <p className="subtitle">Sign in to your personal workspace</p>
                </div>

                <AuthButtons
                    onAuthSuccess={handleAuthSuccess}
                    onError={setError}
                    loading={loading}
                />

                <form className="login-form" onSubmit={handleEmailLogin}>
                    <div className="form-group">
                        <label htmlFor="email">Email address</label>
                        <input
                            id="email"
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="email-input"
                            placeholder="name@example.com"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="email-input"
                            placeholder="••••••••"
                        />
                    </div>

                    {error && (
                        <div className="error-message">
                            <span className="error-icon">⚠️</span>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="submit-button"
                    >
                        {loading ? 'Signing in...' : 'Sign In'} <span className="arrow">→</span>
                    </button>
                </form>

                <div className="login-footer">
                    <p className="info-text">
                        Don't have an account?{' '}
                        <Link to="/signup" style={{ color: '#4facfe', textDecoration: 'none' }}>
                            Sign up
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
