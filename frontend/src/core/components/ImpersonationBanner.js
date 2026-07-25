import { useNavigate } from 'react-router-dom';

function ImpersonationBanner() {
    const navigate = useNavigate();
    const tenantName = localStorage.getItem('impersonation_tenant') || 'a tenant';

    const handleExit = () => {
        // Clear impersonation state
        localStorage.removeItem('impersonating');
        localStorage.removeItem('impersonation_token');
        localStorage.removeItem('impersonation_tenant');

        // Redirect back to platform admin console
        window.location.href = '/super-admin/tenants';
    };

    return (
        <div style={{
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            color: 'white',
            padding: '0.75rem 1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontWeight: 500,
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.2rem' }}>⚠️</span>
                <span>You are viewing as <strong>{tenantName}</strong> (Impersonation Mode)</span>
            </div>
            <button
                onClick={handleExit}
                style={{
                    background: 'rgba(255,255,255,0.3)',
                    border: '1px solid rgba(255,255,255,0.5)',
                    color: 'white',
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                }}
                onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.4)'}
                onMouseOut={(e) => e.target.style.background = 'rgba(255,255,255,0.3)'}
            >
                Exit Impersonation
            </button>
        </div>
    );
}

export default ImpersonationBanner;
