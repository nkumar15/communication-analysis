/**
 * B2C Welcome Page
 * Landing page for the B2C personal workspace portal
 */
import { useState } from 'react';

function WelcomePage() {
    const [email, setEmail] = useState('');

    const handleGetStarted = (e) => {
        e.preventDefault();
        // TODO: Implement signup flow
        alert(`Coming soon! We'll notify ${email} when ready.`);
    };

    return (
        <div style={styles.container}>
            <div style={styles.content}>
                {/* Hero Section */}
                <div style={styles.hero}>
                    <h1 style={styles.title}>
                        Your Personal Workspace
                    </h1>
                    <p style={styles.subtitle}>
                        Organize your projects, collaborate with teams,
                        and boost your productivity — all in one place.
                    </p>
                </div>

                {/* Email Signup */}
                <form onSubmit={handleGetStarted} style={styles.form}>
                    <input
                        type="email"
                        placeholder="Enter your email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        style={styles.input}
                        required
                    />
                    <button type="submit" style={styles.button}>
                        Get Early Access
                    </button>
                </form>

                {/* Features */}
                <div style={styles.features}>
                    <div style={styles.feature}>
                        <span style={styles.featureIcon}>📁</span>
                        <h3 style={styles.featureTitle}>Personal Workspace</h3>
                        <p style={styles.featureDesc}>Your private space for projects and notes</p>
                    </div>
                    <div style={styles.feature}>
                        <span style={styles.featureIcon}>👥</span>
                        <h3 style={styles.featureTitle}>Team Collaboration</h3>
                        <p style={styles.featureDesc}>Invite others to collaborate on shared workspaces</p>
                    </div>
                    <div style={styles.feature}>
                        <span style={styles.featureIcon}>🔒</span>
                        <h3 style={styles.featureTitle}>Secure & Private</h3>
                        <p style={styles.featureDesc}>Your data stays yours with enterprise-grade security</p>
                    </div>
                </div>

                {/* Footer */}
                <p style={styles.footer}>
                    🚧 Coming Soon — B2C Portal is under development
                </p>
            </div>
        </div>
    );
}

const styles = {
    container: {
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
    },
    content: {
        maxWidth: '600px',
        textAlign: 'center',
    },
    hero: {
        marginBottom: '40px',
    },
    title: {
        fontSize: '48px',
        fontWeight: '700',
        color: '#fff',
        margin: '0 0 16px 0',
        textShadow: '0 2px 4px rgba(0,0,0,0.1)',
    },
    subtitle: {
        fontSize: '20px',
        color: 'rgba(255,255,255,0.9)',
        lineHeight: '1.6',
        margin: 0,
    },
    form: {
        display: 'flex',
        gap: '12px',
        justifyContent: 'center',
        marginBottom: '60px',
        flexWrap: 'wrap',
    },
    input: {
        padding: '16px 24px',
        fontSize: '16px',
        border: 'none',
        borderRadius: '8px',
        width: '280px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    },
    button: {
        padding: '16px 32px',
        fontSize: '16px',
        fontWeight: '600',
        color: '#667eea',
        backgroundColor: '#fff',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        transition: 'transform 0.2s, box-shadow 0.2s',
    },
    features: {
        display: 'flex',
        gap: '24px',
        justifyContent: 'center',
        marginBottom: '40px',
        flexWrap: 'wrap',
    },
    feature: {
        backgroundColor: 'rgba(255,255,255,0.15)',
        borderRadius: '12px',
        padding: '24px',
        width: '160px',
        backdropFilter: 'blur(10px)',
    },
    featureIcon: {
        fontSize: '32px',
        marginBottom: '12px',
        display: 'block',
    },
    featureTitle: {
        fontSize: '16px',
        fontWeight: '600',
        color: '#fff',
        margin: '0 0 8px 0',
    },
    featureDesc: {
        fontSize: '13px',
        color: 'rgba(255,255,255,0.8)',
        margin: 0,
        lineHeight: '1.4',
    },
    footer: {
        fontSize: '14px',
        color: 'rgba(255,255,255,0.7)',
    },
};

export default WelcomePage;
