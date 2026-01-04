import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from modules.domains.enron.models import EnronEmail

logger = logging.getLogger(__name__)

class GraphService:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.last_updated = None

    async def build_graph(self, 
                         db: AsyncSession, 
                         tenant_id: Any,
                         start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> nx.DiGraph:
        """
        Builds a directed graph from email communications.
        Nodes: Email addresses
        Edges: Weighted by number of emails sent
        """
        # Default to last 30 days if no dates provided to prevent fetching everything
        if not start_date:
            # For Enron, data is old. Let's pick a window around 2001 if dates are None
            # Or fetch everything if user asks?
            # Better: Fetch distinct sender/recipients efficiently.
            pass

        query = select(EnronEmail.sender, EnronEmail.recipients, EnronEmail.date).where(
            EnronEmail.tenant_id == tenant_id
        )
        
        if start_date:
            query = query.where(EnronEmail.date >= start_date)
        if end_date:
            query = query.where(EnronEmail.date <= end_date)

        # Execute query
        result = await db.execute(query)
        emails = result.all()

        G = nx.DiGraph()

        for sender, recipients, date in emails:
            if not sender or not recipients:
                continue
                
            sender = sender.lower().strip()
            
            for recipient in recipients:
                recipient = recipient.lower().strip()
                if sender == recipient:
                    continue # Ignore self-emails
                
                if G.has_edge(sender, recipient):
                    G[sender][recipient]['weight'] += 1
                else:
                    G.add_edge(sender, recipient, weight=1)

        self.graph = G
        self.last_updated = datetime.now()
        logger.info(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def detect_cliques(self, min_size: int = 3) -> List[List[str]]:
        """
        Detects cliques (fully connected subgraphs).
        Converts to undirected graph first as clique definition is usually undirected.
        """
        if self.graph.number_of_nodes() == 0:
            return []

        # Convert to undirected to find groups who ALL talk to each other
        undirected_G = self.graph.to_undirected()
        
        # networkx.find_cliques finds maximal cliques
        cliques = list(nx.find_cliques(undirected_G))
        
        # Filter by size
        suspicious_cliques = [c for c in cliques if len(c) >= min_size]
        
        # Sort by size descending
        suspicious_cliques.sort(key=len, reverse=True)
        
        return suspicious_cliques

    def get_centrality_scores(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns top nodes by PageRank centrality.
        """
        if self.graph.number_of_nodes() == 0:
            return []

        try:
            scores = nx.pagerank(self.graph)
            # Sort by score
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            return [{"email": k, "score": v} for k, v in sorted_scores[:limit]]
        except Exception as e:
            logger.error(f"Error calculating centrality: {e}")
            return []

    def get_ego_network(self, user_email: str, radius: int = 1) -> Dict[str, Any]:
        """
        Returns the network surrounding a specific user (nodes and links).
        Format suitable for frontend visualization (react-force-graph).
        """
        user_email = user_email.lower().strip()
        if user_email not in self.graph:
            return {"nodes": [], "links": []}

        # Extract ego graph
        ego_G = nx.ego_graph(self.graph, user_email, radius=radius)
        
        # Serialize
        nodes = [{"id": n, "group": 1 if n == user_email else 2} for n in ego_G.nodes()]
        links = [{"source": u, "target": v, "value": d['weight']} for u, v, d in ego_G.edges(data=True)]
        
        return {"nodes": nodes, "links": links}

# Singleton
graph_service = GraphService()
