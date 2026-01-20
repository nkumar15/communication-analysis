import React, { useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Box, Typography, Paper } from '@mui/material';

const SocialGraphView = ({ data, width = 600, height = 400 }) => {
    const fgRef = useRef();

    useEffect(() => {
        if (fgRef.current && data) {
            setTimeout(() => {
                if (fgRef.current) {
                    fgRef.current.zoomToFit(500, 50);
                }
            }, 500);
        }
    }, [data]);

    const nodesWithStats = React.useMemo(() => {
        if (!data || !data.nodes) return [];

        const nodeStats = {};
        data.nodes.forEach(n => {
            nodeStats[n.id] = { degree: 0, volume: 0, role: n.group === 1 ? 'Target' : 'Contact' };
        });

        data.links.forEach(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            const val = link.value || 0;

            if (nodeStats[sourceId]) {
                nodeStats[sourceId].degree++;
                nodeStats[sourceId].volume += val;
            }
            if (nodeStats[targetId]) {
                nodeStats[targetId].degree++;
                nodeStats[targetId].volume += val;
            }
        });

        return data.nodes.map(n => ({
            ...n,
            ...nodeStats[n.id]
        }));
    }, [data]);

    const enrichedData = { ...data, nodes: nodesWithStats };

    return (
        <Paper elevation={1} sx={{ overflow: 'hidden', border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <Box p={1.5} bgcolor="#f8fafc" borderBottom="1px solid #e0e0e0" display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="subtitle2" fontWeight="600" color="primary">
                    Network Graph Analysis (Clique Detection)
                </Typography>
                <Typography variant="caption" color="text.secondary">
                    {data.nodes.length} entities • {data.links.length} interactions
                </Typography>
            </Box>
            <Box sx={{ bgcolor: '#ffffff', position: 'relative' }}>
                <ForceGraph2D
                    ref={fgRef}
                    graphData={enrichedData}
                    width={width}
                    height={height}
                    nodeLabel={node => `
                        <div style="color: #333; background: rgba(255,255,255,0.9); padding: 8px; border-radius: 4px; border: 1px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-weight: bold; border-bottom: 1px solid #eee; margin-bottom: 4px; padding-bottom: 2px;">${node.id}</div>
                            <div style="font-size: 0.85em;">
                                <div><span style="color: #666;">Classification:</span> <b>${node.role}</b></div>
                                <div><span style="color: #666;">Connected Entities:</span> <b>${node.degree}</b></div>
                                <div><span style="color: #666;">Communication Volume:</span> <b>${node.volume}</b></div>
                            </div>
                        </div>
                    `}
                    nodeColor={node => node.group === 1 ? '#ef4444' : '#3b82f6'}
                    nodeRelSize={6}
                    linkColor={() => '#94a3b8'}
                    linkWidth={link => Math.log((link.value || 1) + 1) + 1}
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={1}
                    backgroundColor="#ffffff"
                    cooldownTicks={100}
                />

                <Paper
                    elevation={3}
                    sx={{
                        position: 'absolute',
                        bottom: 16,
                        right: 16,
                        p: 2,
                        bgcolor: 'rgba(255, 255, 255, 0.9)',
                        backdropFilter: 'blur(4px)',
                        maxWidth: 240,
                        zIndex: 10
                    }}
                >
                    <Typography variant="caption" fontWeight="bold" display="block" gutterBottom>
                        Analysis Legend
                    </Typography>

                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                        <Box width={12} height={12} borderRadius="50%" bgcolor="#ef4444" />
                        <Typography variant="caption">Primary Subject</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                        <Box width={12} height={12} borderRadius="50%" bgcolor="#3b82f6" />
                        <Typography variant="caption">Associated Contact</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1}>
                        <Box width={20} height={2} bgcolor="#94a3b8" />
                        <Typography variant="caption">Interaction Weight (Volume)</Typography>
                    </Box>
                </Paper>
            </Box>
        </Paper>
    );
};

export default SocialGraphView;
