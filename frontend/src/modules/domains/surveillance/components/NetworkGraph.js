import React, { useEffect, useState, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Box, Typography, CircularProgress, Paper, Chip } from '@mui/material';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const NetworkGraph = ({ email, height = 500 }) => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const fgRef = useRef();

    useEffect(() => {
        const loadGraph = async () => {
            console.log("NetworkGraph: loading for email:", email);
            if (!email) {
                console.warn("NetworkGraph: No email provided");
                return;
            }
            setLoading(true);
            try {
                const data = await b2bDomainClient.getEgoNetwork(email);
                console.log("NetworkGraph: data received:", data);

                if (!data || !data.nodes || data.nodes.length === 0) {
                    console.warn("NetworkGraph: No nodes found in data");
                    setGraphData({ nodes: [], links: [] });
                    return;
                }

                // Transform for visualization
                // Add color/size based on group (1=Ego, 2=Alters)
                const processedNodes = data.nodes.map(node => ({
                    ...node,
                    val: node.group === 1 ? 20 : 10,
                    color: node.group === 1 ? '#ef4444' : '#3b82f6',
                    name: node.id
                }));

                setGraphData({ nodes: processedNodes, links: data.links });
            } catch (error) {
                console.error("Failed to load graph:", error);
            } finally {
                setLoading(false);
            }
        };
        loadGraph();
    }, [email]);

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
                <CircularProgress />
            </Box>
        );
    }

    if (!graphData.nodes.length) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height, bgcolor: '#f8fafc', borderRadius: 2 }}>
                <Typography color="textSecondary">No network data found for {email}</Typography>
            </Box>
        );
    }

    const containerRef = useRef();
    const [dimensions, setDimensions] = useState({ width: 0, height: height });

    useEffect(() => {
        if (!containerRef.current) return;

        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                setDimensions({
                    width: entry.contentRect.width,
                    height: entry.contentRect.height || height
                });
            }
        });

        resizeObserver.observe(containerRef.current);
        return () => resizeObserver.disconnect();
    }, [containerRef]);

    return (
        <Paper variant="outlined" sx={{ height, borderRadius: 2, overflow: 'hidden', bgcolor: '#fafafa', position: 'relative' }} ref={containerRef}>
            <Box sx={{ position: 'absolute', top: 16, left: 16, zIndex: 10 }}>
                <Chip label={`Ego Network: ${email}`} size="small" color="primary" sx={{ fontWeight: 700 }} />
                <Typography variant="caption" sx={{ display: 'block', mt: 1, color: '#64748b' }}>
                    {graphData.nodes.length} Nodes • {graphData.links.length} Edges
                </Typography>
            </Box>

            {dimensions.width > 0 && (
                <ForceGraph2D
                    ref={fgRef}
                    width={dimensions.width}
                    height={height}
                    graphData={graphData}
                    nodeLabel="id"
                    nodeColor="color"
                    nodeRelSize={6}
                    linkColor={() => '#cbd5e1'}
                    linkWidth={2}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleSpeed={d => d.value * 0.001}
                    cooldownTicks={100}
                    onEngineStop={() => fgRef.current.zoomToFit(400)}
                />
            )}
        </Paper>
    );
};

export default NetworkGraph;
