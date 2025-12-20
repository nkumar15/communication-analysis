import React, { useState, useRef } from 'react';
import invitationApi from '../../../../core/api/invitationClient';
import { formatDateTime } from '../../../../utils/dateUtils';

/**
 * BulkInviteModal - Modal for bulk user invitation via CSV upload
 */
const BulkInviteModal = ({ isOpen, onClose, onSuccess }) => {
    const [state, setState] = useState('initial'); // initial, uploading, complete, error
    const [file, setFile] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const fileInputRef = useRef(null);

    const resetState = () => {
        setState('initial');
        setFile(null);
        setUploadProgress(0);
        setResult(null);
        setError('');
    };

    const handleClose = () => {
        resetState();
        onClose();
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0];
            validateAndSetFile(droppedFile);
        }
    };

    const validateAndSetFile = (selectedFile) => {
        setError('');

        // Check file type
        if (!selectedFile.name.endsWith('.csv')) {
            setError('Please upload a CSV file');
            return;
        }

        // Check file size (2MB max)
        if (selectedFile.size > 2 * 1024 * 1024) {
            setError('File too large. Maximum size is 2MB');
            return;
        }

        setFile(selectedFile);
    };

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files[0]) {
            validateAndSetFile(e.target.files[0]);
        }
    };

    const handleDownloadTemplate = async () => {
        try {
            const blob = await invitationApi.downloadTemplate();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'bulk_invite_template.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setError('Failed to download template');
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setState('uploading');
        setError('');
        setUploadProgress(10);

        try {
            // Simulate progress
            const progressInterval = setInterval(() => {
                setUploadProgress(prev => Math.min(prev + 10, 90));
            }, 200);

            const response = await invitationApi.bulkInviteUsers(file);

            clearInterval(progressInterval);
            setUploadProgress(100);
            setResult(response);
            setState('complete');

            if (onSuccess) {
                onSuccess(response);
            }
        } catch (err) {
            setState('error');
            setError(err.message || 'Failed to process bulk invitations');
        }
    };

    const handleDownloadResults = async () => {
        if (!result?.job_id) return;

        try {
            const blob = await invitationApi.downloadBulkResults(result.job_id);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bulk_invite_results_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setError('Failed to download results');
        }
    };

    const handleDownloadFailures = async () => {
        if (!result?.job_id) return;

        try {
            const blob = await invitationApi.downloadBulkFailures(result.job_id);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bulk_invite_failures_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setError(err.message || 'Failed to download failures');
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px'
        }} onClick={handleClose}>
            <div style={{
                width: '100%',
                maxWidth: '600px',
                background: 'white',
                borderRadius: '16px',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                overflow: 'hidden',
                maxHeight: '90vh',
                display: 'flex',
                flexDirection: 'column'
            }} onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div style={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    padding: '24px',
                    color: 'white'
                }}>
                    <h2 style={{
                        margin: 0,
                        fontSize: '24px',
                        fontWeight: '700',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px'
                    }}>
                        <span style={{ fontSize: '28px' }}>📋</span>
                        Bulk Invite Users
                    </h2>
                    <p style={{
                        margin: '8px 0 0 0',
                        fontSize: '14px',
                        opacity: 0.9
                    }}>
                        Upload a CSV file to invite multiple users at once
                    </p>
                </div>

                {/* Body */}
                <div style={{ padding: '28px', overflowY: 'auto', flex: 1 }}>
                    {/* Error Alert */}
                    {error && (
                        <div style={{
                            marginBottom: '20px',
                            padding: '12px 16px',
                            backgroundColor: '#FEE2E2',
                            border: '1px solid #FCA5A5',
                            borderRadius: '8px',
                            color: '#991B1B',
                            fontSize: '14px'
                        }}>
                            ❌ {error}
                        </div>
                    )}

                    {/* Initial/Upload State */}
                    {(state === 'initial' || state === 'error') && (
                        <>
                            {/* Template Download */}
                            <div style={{
                                marginBottom: '24px',
                                padding: '16px',
                                backgroundColor: '#EEF2FF',
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between'
                            }}>
                                <div>
                                    <div style={{ fontWeight: '600', color: '#4338CA', marginBottom: '4px' }}>
                                        📄 Need a template?
                                    </div>
                                    <div style={{ fontSize: '13px', color: '#6366F1' }}>
                                        Download our CSV template with required columns
                                    </div>
                                </div>
                                <button
                                    onClick={handleDownloadTemplate}
                                    style={{
                                        padding: '8px 16px',
                                        backgroundColor: '#4F46E5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        fontSize: '13px',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Download
                                </button>
                            </div>

                            {/* Drop Zone */}
                            <div
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                                onClick={() => fileInputRef.current?.click()}
                                style={{
                                    border: `2px dashed ${dragActive ? '#4F46E5' : file ? '#10B981' : '#D1D5DB'}`,
                                    borderRadius: '12px',
                                    padding: '40px 20px',
                                    textAlign: 'center',
                                    cursor: 'pointer',
                                    backgroundColor: dragActive ? '#EEF2FF' : file ? '#ECFDF5' : '#F9FAFB',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".csv"
                                    onChange={handleFileSelect}
                                    style={{ display: 'none' }}
                                />
                                <div style={{ fontSize: '48px', marginBottom: '12px' }}>
                                    {file ? '✅' : '📁'}
                                </div>
                                {file ? (
                                    <>
                                        <div style={{ fontWeight: '600', color: '#065F46', marginBottom: '4px' }}>
                                            {file.name}
                                        </div>
                                        <div style={{ fontSize: '13px', color: '#6B7280' }}>
                                            {(file.size / 1024).toFixed(1)} KB • Click to change
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div style={{ fontWeight: '600', color: '#374151', marginBottom: '4px' }}>
                                            Drop your CSV file here
                                        </div>
                                        <div style={{ fontSize: '13px', color: '#6B7280' }}>
                                            or click to browse • Max 2MB, 100 users
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* CSV Format Info */}
                            <div style={{
                                marginTop: '20px',
                                padding: '16px',
                                backgroundColor: '#FFFBEB',
                                borderRadius: '8px',
                                fontSize: '13px'
                            }}>
                                <div style={{ fontWeight: '600', color: '#92400E', marginBottom: '8px' }}>
                                    📋 Required CSV Columns:
                                </div>
                                <div style={{ color: '#B45309' }}>
                                    <code style={{ backgroundColor: '#FEF3C7', padding: '2px 6px', borderRadius: '4px' }}>
                                        email, role
                                    </code>
                                </div>
                                <div style={{ marginTop: '8px', color: '#B45309' }}>
                                    <strong>Optional:</strong> team_name, team_role, name
                                </div>
                            </div>
                        </>
                    )}

                    {/* Uploading State */}
                    {state === 'uploading' && (
                        <div style={{ textAlign: 'center', padding: '40px 0' }}>
                            <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
                            <div style={{ fontWeight: '600', fontSize: '18px', marginBottom: '16px' }}>
                                Processing invitations...
                            </div>
                            <div style={{
                                width: '100%',
                                height: '8px',
                                backgroundColor: '#E5E7EB',
                                borderRadius: '4px',
                                overflow: 'hidden'
                            }}>
                                <div style={{
                                    width: `${uploadProgress}%`,
                                    height: '100%',
                                    backgroundColor: '#4F46E5',
                                    transition: 'width 0.3s'
                                }} />
                            </div>
                            <div style={{ marginTop: '8px', fontSize: '14px', color: '#6B7280' }}>
                                {uploadProgress}%
                            </div>
                        </div>
                    )}

                    {/* Complete State */}
                    {state === 'complete' && result && (
                        <>
                            {/* Summary */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(3, 1fr)',
                                gap: '16px',
                                marginBottom: '24px'
                            }}>
                                <div style={{
                                    padding: '16px',
                                    backgroundColor: '#F3F4F6',
                                    borderRadius: '8px',
                                    textAlign: 'center'
                                }}>
                                    <div style={{ fontSize: '28px', fontWeight: '700', color: '#374151' }}>
                                        {result.total_processed}
                                    </div>
                                    <div style={{ fontSize: '13px', color: '#6B7280' }}>Total</div>
                                </div>
                                <div style={{
                                    padding: '16px',
                                    backgroundColor: '#ECFDF5',
                                    borderRadius: '8px',
                                    textAlign: 'center'
                                }}>
                                    <div style={{ fontSize: '28px', fontWeight: '700', color: '#059669' }}>
                                        {result.successful}
                                    </div>
                                    <div style={{ fontSize: '13px', color: '#10B981' }}>Successful</div>
                                </div>
                                <div style={{
                                    padding: '16px',
                                    backgroundColor: result.failed > 0 ? '#FEE2E2' : '#F3F4F6',
                                    borderRadius: '8px',
                                    textAlign: 'center'
                                }}>
                                    <div style={{
                                        fontSize: '28px',
                                        fontWeight: '700',
                                        color: result.failed > 0 ? '#DC2626' : '#374151'
                                    }}>
                                        {result.failed}
                                    </div>
                                    <div style={{ fontSize: '13px', color: result.failed > 0 ? '#EF4444' : '#6B7280' }}>
                                        Failed
                                    </div>
                                </div>
                            </div>

                            {/* Teams Created */}
                            {result.teams_created && result.teams_created.length > 0 && (
                                <div style={{
                                    marginBottom: '24px',
                                    padding: '12px 16px',
                                    backgroundColor: '#EEF2FF',
                                    borderRadius: '8px',
                                    fontSize: '14px'
                                }}>
                                    <span style={{ color: '#4338CA', fontWeight: '600' }}>
                                        🏢 Teams Created:
                                    </span>{' '}
                                    {result.teams_created.join(', ')}
                                </div>
                            )}

                            {/* Results Preview */}
                            <div style={{
                                maxHeight: '200px',
                                overflowY: 'auto',
                                border: '1px solid #E5E7EB',
                                borderRadius: '8px',
                                marginBottom: '16px'
                            }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                                    <thead>
                                        <tr style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                                            <th style={{ padding: '8px 12px', textAlign: 'left' }}>Email</th>
                                            <th style={{ padding: '8px 12px', textAlign: 'left' }}>Role</th>
                                            <th style={{ padding: '8px 12px', textAlign: 'center' }}>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.results?.slice(0, 10).map((row, idx) => (
                                            <tr key={idx} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                <td style={{ padding: '8px 12px' }}>{row.email}</td>
                                                <td style={{ padding: '8px 12px' }}>{row.role}</td>
                                                <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                                                    {row.status === 'success' ? (
                                                        <span style={{ color: '#10B981' }}>✅</span>
                                                    ) : (
                                                        <span title={row.error} style={{ color: '#EF4444' }}>❌</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                {result.results?.length > 10 && (
                                    <div style={{ padding: '8px', textAlign: 'center', fontSize: '12px', color: '#6B7280' }}>
                                        ... and {result.results.length - 10} more
                                    </div>
                                )}
                            </div>

                            {/* Download Buttons */}
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <button
                                    onClick={handleDownloadResults}
                                    style={{
                                        flex: 1,
                                        padding: '10px 16px',
                                        backgroundColor: '#4F46E5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                    }}
                                >
                                    📥 Download All Results
                                </button>
                                {result.failed > 0 && (
                                    <button
                                        onClick={handleDownloadFailures}
                                        style={{
                                            flex: 1,
                                            padding: '10px 16px',
                                            backgroundColor: '#DC2626',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '8px',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        ⚠️ Download Failures
                                    </button>
                                )}
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div style={{
                    padding: '16px 28px',
                    borderTop: '1px solid #E5E7EB',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '12px'
                }}>
                    {state === 'complete' ? (
                        <button
                            onClick={handleClose}
                            style={{
                                padding: '10px 24px',
                                backgroundColor: '#4F46E5',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: 'pointer'
                            }}
                        >
                            Done
                        </button>
                    ) : (
                        <>
                            <button
                                onClick={handleClose}
                                style={{
                                    padding: '10px 24px',
                                    backgroundColor: 'white',
                                    color: '#374151',
                                    border: '1px solid #D1D5DB',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    cursor: 'pointer'
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleUpload}
                                disabled={!file || state === 'uploading'}
                                style={{
                                    padding: '10px 24px',
                                    backgroundColor: file ? '#4F46E5' : '#9CA3AF',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    cursor: file ? 'pointer' : 'not-allowed'
                                }}
                            >
                                {state === 'uploading' ? 'Uploading...' : 'Upload & Invite'}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default BulkInviteModal;
