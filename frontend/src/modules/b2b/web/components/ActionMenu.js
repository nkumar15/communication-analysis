import React, { useState, useRef, useEffect } from 'react';
import ReactDOM from 'react-dom';

const ActionMenu = ({ actions }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [menuPosition, setMenuPosition] = useState({});
    const buttonRef = useRef(null);
    const menuRef = useRef(null);

    // Calculate position when opening
    useEffect(() => {
        if (isOpen && buttonRef.current) {
            const rect = buttonRef.current.getBoundingClientRect();
            // Default to aligning right edge of menu with right edge of button
            // Render below the button
            const top = rect.bottom + 4;
            const right = window.innerWidth - rect.right; // distance from right

            // If close to bottom of screen, render above? (Can implement later if needed)

            setMenuPosition({
                top: `${top + window.scrollY}px`,
                right: `${right}px`,
                position: 'absolute' // We will portal to document.body, so absolute implies 'fixed'-like behavior relative to page if we use document.body, wait.
                // Better to use 'fixed' if we rely on viewport coordinates (rect)
            });
        }
    }, [isOpen]);

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            // Check if click is on button
            if (buttonRef.current && buttonRef.current.contains(event.target)) {
                return;
            }
            // Check if click is inside menu
            if (menuRef.current && menuRef.current.contains(event.target)) {
                return;
            }
            // Clicked outside
            setIsOpen(false);
        };

        const handleScroll = () => {
            if (isOpen) setIsOpen(false); // Close on scroll for simplicity
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
            window.addEventListener('scroll', handleScroll, true);
            window.addEventListener('resize', handleScroll);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            window.removeEventListener('scroll', handleScroll, true);
            window.removeEventListener('resize', handleScroll);
        };
    }, [isOpen]);

    const MenuContent = (
        <div
            ref={menuRef}
            style={{
                position: 'fixed', // Use fixed to position relative to viewport
                top: buttonRef.current ? buttonRef.current.getBoundingClientRect().bottom + 4 : 0,
                // Align right: calc left based on button right
                left: buttonRef.current ? buttonRef.current.getBoundingClientRect().right - 160 : 0, // 160 is approx width, better to use right
                // Actually, let's use explicit calculation
                // React style doesn't support 'right' well with 'fixed' unless we know full width. 
                // Better to calculate LEFT.
                // Left = Button Right - Menu Width.
                // We don't know menu width yet.
                // Let's rely on flexible width or hardcode min-width.
                // Or better: Use `right` property relative to viewport.
                right: buttonRef.current ? window.innerWidth - buttonRef.current.getBoundingClientRect().right : 0,

                minWidth: '160px',
                marginTop: '0',
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '8px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                overflow: 'hidden',
                zIndex: 9999, // High z-index to break out
            }}
        >
            {actions.map((action, index) => (
                <button
                    key={index}
                    onClick={() => {
                        action.onClick();
                        setIsOpen(false);
                    }}
                    style={{
                        width: '100%',
                        padding: '12px 16px',
                        backgroundColor: 'white',
                        border: 'none',
                        textAlign: 'left',
                        cursor: 'pointer',
                        fontSize: '14px',
                        color: action.danger ? '#DC2626' : '#374151',
                        transition: 'background-color 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        textDecoration: 'none' // in case it's valid link someday
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = action.danger ? '#FEE2E2' : '#F9FAFB'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                >
                    {action.icon && <span style={{ marginRight: '8px', fontSize: '16px' }}>{action.icon}</span>}
                    {action.label}
                </button>
            ))}
        </div>
    );

    return (
        <>
            <button
                ref={buttonRef}
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    padding: '4px 8px',
                    backgroundColor: isOpen ? '#F3F4F6' : 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '20px',
                    color: '#6B7280',
                    borderRadius: '4px',
                    transition: 'background-color 0.2s',
                    lineHeight: '1'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#F3F4F6'}
                onMouseLeave={(e) => !isOpen && (e.target.style.backgroundColor = 'transparent')}
            >
                ⋮
            </button>
            {isOpen && ReactDOM.createPortal(MenuContent, document.body)}
        </>
    );
};

export default ActionMenu;
