from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.db.session import get_db
import networkx as nx

from modules.domains.b2b.bank_surveillance.services.graph import graph_service
from modules.domains.b2b.bank_surveillance.constants import DEFAULT_TENANT_ID

router = APIRouter(prefix="/api/b2b/domain/bank_surveillance/graph", tags=["Surveillance Graph"])

@router.post("/build")
async def build_graph(db: AsyncSession = Depends(get_db)):
    """Triggers construction of the communication graph from DB."""
    G = await graph_service.build_graph(db, tenant_id=DEFAULT_TENANT_ID)
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": nx.density(G),
        "message": "Graph built successfully"
    }

@router.get("/summary")
async def get_graph_summary(db: AsyncSession = Depends(get_db)):
    """Returns basic stats about the current graph."""
    if graph_service.graph.number_of_nodes() == 0:
        await graph_service.build_graph(db, DEFAULT_TENANT_ID)
    
    return {
        "nodes": graph_service.graph.number_of_nodes(),
        "edges": graph_service.graph.number_of_edges(),
        "last_updated": graph_service.last_updated,
        "cliques_count": len(graph_service.detect_cliques()),
    }

@router.get("/cliques")
async def get_cliques(min_size: int = 3, db: AsyncSession = Depends(get_db)):
    """Returns a list of suspicious cliques."""
    if graph_service.graph.number_of_nodes() == 0:
        await graph_service.build_graph(db, DEFAULT_TENANT_ID)
    return graph_service.detect_cliques(min_size=min_size)

@router.get("/ego/{email}")
async def get_ego_graph(email: str, radius: int = 1, db: AsyncSession = Depends(get_db)):
    """Returns the ego network for a specific entity."""
    if graph_service.graph.number_of_nodes() == 0:
        await graph_service.build_graph(db, DEFAULT_TENANT_ID)
    return graph_service.get_ego_network(email, radius)
