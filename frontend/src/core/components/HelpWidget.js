import React, { useState } from 'react';
import {
    Box,
    Typography,
    IconButton,
    Paper,
    Avatar,
    TextField,
    Button,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Fade,
    Divider,
    Tooltip,
    Zoom
} from '@mui/material';
import {
    Chat,
    Close,
    Send,
    MenuBook,
    PlayCircleFilled,
    Email,
    SupportAgent,
    Bolt,
    Security
} from '@mui/icons-material';

const HelpWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [message, setMessage] = useState('');

    const handleSendMessage = (e) => {
        e.preventDefault();
        if (!message.trim()) return;
        alert('Signal Intelligence Bot: Transmission received. Processing queue... (Demo only)');
        setMessage('');
    };

    return (
        <>
            {/* Immersive Chat Panel */}
            <Fade in={isOpen}>
                <Paper
                    elevation={12}
                    sx={{
                        position: 'fixed',
                        bottom: '92px',
                        left: '24px',
                        width: '400px',
                        height: '580px',
                        borderRadius: 3,
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden',
                        zIndex: 2000,
                        border: '1px solid rgba(0, 0, 0, 0.08)',
                        bgcolor: 'rgba(255, 255, 255, 0.98)',
                        backdropFilter: 'blur(10px)',
                    }}
                >
                    {/* Premium Header */}
                    <Box sx={{
                        p: 2.5,
                        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                    }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <Avatar sx={{ bgcolor: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)' }}>
                                <SupportAgent sx={{ color: '#6366f1' }} />
                            </Avatar>
                            <Box>
                                <Typography variant="subtitle1" fontWeight="700" sx={{ lineHeight: 1.2 }}>Intelligence Support</Typography>
                                <Typography variant="caption" sx={{ opacity: 0.7, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#10b981' }} />
                                    Active Signal
                                </Typography>
                            </Box>
                        </Box>
                        <IconButton size="small" onClick={() => setIsOpen(false)} sx={{ color: 'white', opacity: 0.6, '&:hover': { opacity: 1 } }}>
                            <Close fontSize="small" />
                        </IconButton>
                    </Box>

                    {/* Chat Area */}
                    <Box sx={{ flex: 1, overflowY: 'auto', p: 3, bgcolor: '#f8fafc' }}>
                        <Box sx={{ mb: 3 }}>
                            <Typography variant="caption" fontWeight="800" color="primary" sx={{ textTransform: 'uppercase', letterSpacing: 1, mb: 1.5, display: 'block' }}>
                                Compliance Assistant
                            </Typography>
                            <Paper sx={{ p: 2, borderRadius: '2px 16px 16px 16px', bgcolor: 'white', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                                <Typography variant="body2" color="text.primary" sx={{ lineHeight: 1.6 }}>
                                    👋 **Transmission Active.** I am your Command Center assistant.
                                    <br /><br />
                                    How can I assist with your surveillance investigation today?
                                </Typography>
                            </Paper>
                        </Box>

                        <Divider sx={{ mb: 3 }}>
                            <Typography variant="caption" color="text.secondary" fontWeight="700">OPERATIONAL GUIDES</Typography>
                        </Divider>

                        <List sx={{ p: 0 }}>
                            {[
                                { icon: <MenuBook />, label: 'Surveillance Playbooks', color: '#6366f1' },
                                { icon: <Security />, label: 'Control Definitions', color: '#10b981' },
                                { icon: <Bolt />, label: 'Priority Escalation', color: '#f59e0b' }
                            ].map((item, i) => (
                                <ListItem
                                    key={i}
                                    button
                                    sx={{
                                        borderRadius: 2,
                                        mb: 1,
                                        bgcolor: 'white',
                                        border: '1px solid #f1f5f9',
                                        '&:hover': { bgcolor: '#f1f5f9', borderColor: 'primary.light' }
                                    }}
                                >
                                    <ListItemIcon sx={{ minWidth: 40, color: item.color }}>{item.icon}</ListItemIcon>
                                    <ListItemText primary={<Typography variant="body2" fontWeight="600">{item.label}</Typography>} />
                                </ListItem>
                            ))}
                        </List>
                    </Box>

                    {/* Integrated Input */}
                    <Box sx={{ p: 2.5, bgcolor: 'white', borderTop: '1px solid #f1f5f9' }}>
                        <Box component="form" onSubmit={handleSendMessage} sx={{ display: 'flex', gap: 1 }}>
                            <TextField
                                fullWidth
                                size="small"
                                variant="outlined"
                                placeholder="Query neural index..."
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                sx={{
                                    '& .MuiOutlinedInput-root': {
                                        borderRadius: 2.5,
                                        bgcolor: '#f8fafc'
                                    }
                                }}
                            />
                            <IconButton
                                type="submit"
                                color="primary"
                                sx={{
                                    bgcolor: 'primary.main',
                                    color: 'white',
                                    '&:hover': { bgcolor: 'primary.dark' },
                                    borderRadius: 2.5
                                }}
                            >
                                <Send fontSize="small" />
                            </IconButton>
                        </Box>
                    </Box>
                </Paper>
            </Fade>

            {/* Premium Floating Button */}
            <Box sx={{ position: 'fixed', bottom: '24px', left: '24px', zIndex: 2000 }}>
                <Zoom in={true}>
                    <Tooltip title="Intelligence Support" placement="right">
                        <IconButton
                            onClick={() => setIsOpen(!isOpen)}
                            sx={{
                                width: 56,
                                height: 56,
                                bgcolor: '#0f172a',
                                color: 'white',
                                '&:hover': {
                                    bgcolor: '#1e293b',
                                    transform: 'rotate(15deg) scale(1.1)',
                                },
                                boxShadow: '0 8px 16px rgba(15, 23, 42, 0.3)',
                                transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
                            }}
                        >
                            {isOpen ? <Close /> : <Chat />}
                        </IconButton>
                    </Tooltip>
                </Zoom>
            </Box>

            {/* Backdrop */}
            {isOpen && (
                <Box
                    onClick={() => setIsOpen(false)}
                    sx={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1999 }}
                />
            )}
        </>
    );
};

export default HelpWidget;
