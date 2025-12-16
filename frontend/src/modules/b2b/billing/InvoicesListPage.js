import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    CircularProgress,
    Alert,
    Grid,
    Paper,
    IconButton,
    Button
} from '@mui/material';
import {
    Download,
    CheckCircle,
    Schedule,
    Cancel,
    Receipt
} from '@mui/icons-material';
import apiService from '../../../core/api/b2bClient';
import AdminLayout from '../web/layouts/AdminLayout';

const STATUS_COLORS = {
    draft: 'default',
    sent: 'info',
    approved: 'primary',
    paid: 'success',
    overdue: 'error',
    voided: 'default'
};

const STATUS_LABELS = {
    draft: 'Dr aft',
    pending_approval: 'Pending Approval',
    approved: 'Approved',
    sent: 'Sent',
    paid: 'Paid',
    overdue: 'Overdue',
    void: 'Void'
};

const InvoicesListPage = () => {
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchInvoices();
    }, []);

    const fetchInvoices = async () => {
        try {
            setLoading(true);
            const data = await apiService.get('/api/b2b/billing/invoices');
            setInvoices(data);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch invoices:', err);
            setError('Failed to load invoices');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = (invoice) => {
        if (invoice.invoice_pdf_url) {
            window.open(invoice.invoice_pdf_url, '_blank');
        } else {
            alert('PDF not available for this invoice');
        }
    };

    const formatCurrency = (cents) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(cents / 100);
    };

    const formatDate = (dateString) => {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleDateString();
    };

    if (loading) {
        return (
            <AdminLayout title="Invoices" subtitle="View and manage invoices">
                <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                    <CircularProgress />
                </Box>
            </AdminLayout>
        );
    }

    if (error) {
        return (
            <AdminLayout title="Invoices" subtitle="View and manage invoices">
                <Box p={3}>
                    <Alert severity="error">{error}</Alert>
                </Box>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout title="Invoices" subtitle="View and manage invoices">
            <Box p={3}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                    <Typography variant="h4">
                        Invoices
                    </Typography>
                    <Button
                        variant="outlined"
                        startIcon={<Receipt />}
                        onClick={fetchInvoices}
                    >
                        Refresh
                    </Button>
                </Box>

                {invoices.length === 0 ? (
                    <Card>
                        <CardContent>
                            <Box textAlign="center" py={4}>
                                <Receipt sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                                <Typography variant="h6" color="text.secondary">
                                    No invoices yet
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Invoices will appear here after they are generated
                                </Typography>
                            </Box>
                        </CardContent>
                    </Card>
                ) : (
                    <TableContainer component={Paper}>
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Invoice Number</TableCell>
                                    <TableCell>Status</TableCell>
                                    <TableCell>Billing Period</TableCell>
                                    <TableCell>Seats</TableCell>
                                    <TableCell align="right">Amount Due</TableCell>
                                    <TableCell align="right">Amount Paid</TableCell>
                                    <TableCell>Due Date</TableCell>
                                    <TableCell align="center">Actions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {invoices.map((invoice) => (
                                    <TableRow
                                        key={invoice.id}
                                        sx={{
                                            '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.04)' }
                                        }}
                                    >
                                        <TableCell>
                                            <Typography variant="body2" fontWeight="600">
                                                {invoice.invoice_number}
                                            </Typography>
                                        </TableCell>

                                        <TableCell>
                                            <Chip
                                                label={STATUS_LABELS[invoice.status] || invoice.status}
                                                color={STATUS_COLORS[invoice.status] || 'default'}
                                                size="small"
                                            />
                                        </TableCell>

                                        <TableCell>
                                            <Typography variant="body2">
                                                {formatDate(invoice.billing_period_start)}
                                                <br />
                                                <Typography component="span" variant="caption" color="text.secondary">
                                                    to {formatDate(invoice.billing_period_end)}
                                                </Typography>
                                            </Typography>
                                        </TableCell>

                                        <TableCell>
                                            <Typography variant="body2">
                                                {invoice.seat_count_snapshot} users
                                            </Typography>
                                        </TableCell>

                                        <TableCell align="right">
                                            <Typography variant="body2" fontWeight="600">
                                                {formatCurrency(invoice.amount_due)}
                                            </Typography>
                                        </TableCell>

                                        <TableCell align="right">
                                            <Typography
                                                variant="body2"
                                                color={invoice.amount_paid > 0 ? 'success.main' : 'text.secondary'}
                                            >
                                                {formatCurrency(invoice.amount_paid)}
                                            </Typography>
                                        </TableCell>

                                        <TableCell>
                                            {invoice.due_date ? (
                                                <Typography
                                                    variant="body2"
                                                    color={invoice.status === 'overdue' ? 'error.main' : 'text.primary'}
                                                >
                                                    {formatDate(invoice.due_date)}
                                                </Typography>
                                            ) : (
                                                <Typography variant="body2" color="text.secondary">
                                                    -
                                                </Typography>
                                            )}
                                        </TableCell>

                                        <TableCell align="center">
                                            <IconButton
                                                size="small"
                                                onClick={() => handleDownload(invoice)}
                                                disabled={!invoice.invoice_pdf_url}
                                                title="Download PDF"
                                            >
                                                <Download fontSize="small" />
                                            </IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}

                {/* Summary Card */}
                {invoices.length > 0 && (
                    <Card sx={{ mt: 3 }}>
                        <CardContent>
                            <Grid container spacing={3}>
                                <Grid item xs={12} sm={4}>
                                    <Typography variant="body2" color="text.secondary" gutterBottom>
                                        Total Invoices
                                    </Typography>
                                    <Typography variant="h5">
                                        {invoices.length}
                                    </Typography>
                                </Grid>
                                <Grid item xs={12} sm={4}>
                                    <Typography variant="body2" color="text.secondary" gutterBottom>
                                        Paid Invoices
                                    </Typography>
                                    <Typography variant="h5" color="success.main">
                                        {invoices.filter(inv => inv.status === 'paid').length}
                                    </Typography>
                                </Grid>
                                <Grid item xs={12} sm={4}>
                                    <Typography variant="body2" color="text.secondary" gutterBottom>
                                        Overdue Invoices
                                    </Typography>
                                    <Typography variant="h5" color="error.main">
                                        {invoices.filter(inv => inv.status === 'overdue').length}
                                    </Typography>
                                </Grid>
                            </Grid>
                        </CardContent>
                    </Card>
                )}
            </Box>
        </AdminLayout>
    );
};

export default InvoicesListPage;
