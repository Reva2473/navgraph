"""
================================================================================
Backend REST API Server for Minor Project:
Experiment 14: REST API Server & Algorithmic Deployment
Experiment 15: Interactive Frontend Map Navigator Integration
================================================================================
"""

import math
import os
import random
import re
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.data.presets import PRESETS_METADATA, load_preset_graph
from backend.dsa.algorithms import (
    a_star,
    bfs_shortest_hops,
    compare_algorithms,
    dfs_path,
    dijkstra,
    multi_stop_route,
)
from backend.dsa.graph import Edge, Node, WeightedGraph, haversine_distance

# ==============================================================================
# In-Memory Application State
# ==============================================================================

class AppState:
    """Encapsulates in-memory graph state and the active dataset preset."""

    def __init__(self, default_preset: str = "india_highways"):
        self.current_preset: str = default_preset
        self.graph: WeightedGraph = load_preset_graph(default_preset)

    def reload_preset(self, preset_id: str) -> None:
        preset_key = preset_id.lower().strip()
        if preset_key not in PRESETS_METADATA:
            raise ValueError(f"Unknown preset '{preset_id}'. Valid: {list(PRESETS_METADATA.keys())}")
        self.graph = load_preset_graph(preset_key)
        self.current_preset = preset_key


app_state = AppState(default_preset="india_highways")

# ==============================================================================
# FastAPI Application Initialization
# ==============================================================================

app = FastAPI(
    redirect_slashes=False,
    title="Interactive Route & Campus Navigator API",
    description=r"""
### Smart Route Optimization & Graph Analytics Engine
**Academic Evaluation for Experiment 14 (REST API Deployment) & Experiment 15 (Interactive Frontend Integration)**

This service powers geospatial pathfinding, dynamic traffic simulation, and topological graph manipulation
built completely from scratch without external graph libraries (pure Python DSA implementations).

#### Core Capabilities:
- **Dijkstra's Algorithm**: Optimal shortest path using custom array-backed `MinHeap` priority queue ($O((V+E)\log V)$).
- **A* Search Algorithm**: Heuristic-guided spatial pathfinding leveraging the Haversine great-circle distance metric.
- **Breadth-First Search (BFS)**: Fewest hops traversal using pointer-linked `FIFOQueue` ($O(V+E)$).
- **Depth-First Search (DFS)**: Topological exploration using pointer-linked `LIFOStack` ($O(V+E)$).
- **Multi-Stop Navigation**: Sequential waypoint traversal through arbitrary user checkpoints.
- **Simultaneous Benchmark Comparison**: Multi-algorithm evaluation comparing runtime, distance, and explored frontier.
- **Live Traffic Engine**: Dynamic speed multipliers, congestion simulation, and real-time road closures.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "System & Health", "description": "System health verification, preset selection, and global configuration."},
        {"name": "Routing & Pathfinding", "description": "Shortest path computations, multi-stop routing, and algorithmic comparison."},
        {"name": "Graph Management", "description": "Dynamic vertex and edge CRUD operations with dynamic spatial geometry."},
        {"name": "Traffic & Congestion", "description": "Simulate live congestion, dynamic traffic multipliers, and emergency roadblocks."},
    ],
)

# Enable Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VercelPathRestoreMiddleware:
    """
    ASGI Middleware that restores the original request path when Vercel rewrites
    `/api/(.*)` -> `/api/index.py?__vercel_path=/api/$1`.
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") == "http":
            query_bytes = scope.get("query_string", b"")
            qs_str = (
                query_bytes.decode("utf-8", errors="replace")
                if isinstance(query_bytes, bytes)
                else str(query_bytes or "")
            )
            if "__vercel_path=" in qs_str:
                params = urllib.parse.parse_qsl(qs_str, keep_blank_values=True)
                target_path = None
                remaining_params = []
                for k, v in params:
                    if k == "__vercel_path" and target_path is None:
                        target_path = v
                    else:
                        remaining_params.append((k, v))
                if target_path:
                    if "?" in target_path:
                        target_path, extra_qs = target_path.split("?", 1)
                        if extra_qs:
                            remaining_params.extend(
                                urllib.parse.parse_qsl(extra_qs, keep_blank_values=True)
                            )
                    if not target_path.startswith("/"):
                        target_path = "/" + target_path
                    scope["path"] = target_path
                    scope["raw_path"] = target_path.encode("utf-8")
                    scope["query_string"] = urllib.parse.urlencode(remaining_params).encode("utf-8")
        await self.app(scope, receive, send)


app.add_middleware(VercelPathRestoreMiddleware)

# Prevent Browser Stale Asset Caching (Cache-Busting Middleware)
@app.middleware("http")
async def disable_static_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ==============================================================================
# Pydantic Request Models
# ==============================================================================

class RouteRequest(BaseModel):
    source: Optional[str] = Field(None, description="Starting node identifier (e.g. 'delhi')")
    target: Optional[str] = Field(None, description="Destination node identifier (e.g. 'bengaluru')")
    waypoints: Optional[List[str]] = Field(
        None,
        description="Ordered list of waypoint node IDs (inclusive of start and destination, or intermediate stops)",
    )
    algorithm: str = Field(
        "dijkstra",
        description="Pathfinding algorithm: 'dijkstra', 'astar', 'bfs', or 'dfs'",
    )
    weight_mode: str = Field(
        "effective",
        description="Weight metric: 'effective' (accounts for traffic and closures) or 'distance' (raw physical km)",
    )
    preset: Optional[str] = Field(
        None,
        description="Optional active preset ID for stateless serverless routing",
    )


class MultiStopRequest(BaseModel):
    waypoints: Optional[List[str]] = Field(
        None,
        description="Ordered list of waypoint node IDs",
    )
    source: Optional[str] = Field(None, description="Starting node identifier")
    target: Optional[str] = Field(None, description="Destination node identifier")
    algorithm: str = Field(
        "dijkstra",
        description="Pathfinding algorithm: 'dijkstra', 'astar', 'bfs', or 'dfs'",
    )
    weight_mode: str = Field(
        "effective",
        description="Weight metric: 'effective' or 'distance'",
    )
    preset: Optional[str] = Field(
        None,
        description="Optional active preset ID for stateless serverless routing",
    )


class CompareRequest(BaseModel):
    source: str = Field(..., description="Starting node identifier")
    target: str = Field(..., description="Destination node identifier")
    weight_mode: str = Field(
        "effective",
        description="Weight calculation mode: 'effective' (traffic-weighted) or 'distance' (raw base km)",
    )
    preset: Optional[str] = Field(
        None,
        description="Optional active preset ID for stateless serverless routing",
    )


class NodeCreateRequest(BaseModel):
    id: Optional[str] = Field(None, description="Custom unique node identifier. Auto-generated from name if omitted.")
    name: str = Field(..., description="Human-readable node label (e.g. 'Cyber Hub', 'Agra')")
    lat: float = Field(..., description="Latitude coordinate in decimal degrees")
    lng: float = Field(..., description="Longitude coordinate in decimal degrees")
    category: str = Field("custom", description="Category tag (e.g. 'city', 'hub', 'academic', 'custom')")
    description: str = Field("Custom user location", description="Descriptive notes or metadata")


class EdgeCreateRequest(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    base_distance_km: Optional[float] = Field(
        None,
        description="Physical length in km. If omitted or <=0, automatically computed using Haversine great-circle distance.",
    )
    road_name: str = Field("Custom Route", description="Highway or corridor label (e.g. 'NH44', 'Ring Road')")
    traffic_multiplier: float = Field(1.0, ge=1.0, description="Congestion multiplier (1.0 = clear, 2.0 = double duration)")
    is_blocked: bool = Field(False, description="Flag indicating whether road is impassable")
    speed_limit_kmh: float = Field(60.0, gt=0.0, description="Speed limit in km/h")
    bidirectional: bool = Field(True, description="Create reverse edge automatically if True")


class EdgeTrafficUpdateRequest(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    traffic_multiplier: Optional[float] = Field(None, ge=1.0, description="New congestion multiplier (>= 1.0)")
    is_blocked: Optional[bool] = Field(None, description="Set road closure status (True = impassable)")
    bidirectional: bool = Field(True, description="Update both directions if True")


class RandomTrafficRequest(BaseModel):
    congestion_probability: float = Field(
        0.35, ge=0.0, le=1.0, description="Probability that an edge receives higher traffic (1.4x - 2.8x)"
    )
    block_probability: float = Field(
        0.08, ge=0.0, le=1.0, description="Probability that an edge is marked impassable/blocked"
    )
    reset: bool = Field(False, description="If True, ignores probabilities and resets all edges to normal (1.0x, unblocked)")


# ==============================================================================
# Helper Utilities
# ==============================================================================

def _slugify_node_id(name: str, existing_ids: set) -> str:
    """Generate a clean, unique alphanumeric identifier from a display name."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower().strip()).strip("_")
    if not clean:
        clean = "node"
    candidate = clean
    counter = 1
    while candidate in existing_ids:
        candidate = f"{clean}_{counter}"
        counter += 1
    return candidate


def _ensure_preset_loaded(
    preset: Optional[str] = None,
    required_nodes: Optional[List[str]] = None,
) -> None:
    """
    Ensure the appropriate map preset is loaded into memory for stateless serverless execution.
    - If `preset` is provided and in PRESETS_METADATA, reloads it if not already active.
    - Else if `required_nodes` are specified and missing from the active graph, searches other
      presets and reloads if an alternate preset contains all required nodes.
    """
    if preset and preset.lower().strip() in PRESETS_METADATA:
        target_preset = preset.lower().strip()
        if app_state.current_preset != target_preset:
            app_state.reload_preset(target_preset)
    elif required_nodes:
        missing = [nid for nid in required_nodes if nid and nid not in app_state.graph.nodes]
        if missing:
            for other_key in PRESETS_METADATA:
                if other_key == app_state.current_preset:
                    continue
                candidate_graph = load_preset_graph(other_key)
                if all(nid in candidate_graph.nodes for nid in required_nodes if nid):
                    app_state.reload_preset(other_key)
                    break


# ==============================================================================
# REST API Endpoints: System & Health
# ==============================================================================

@app.get("/api/health", tags=["System & Health"], summary="Service Health & Diagnostic Status")
def get_health() -> Dict[str, Any]:
    """Return backend server status, active preset, and graph topology diagnostics."""
    graph_dict = app_state.graph.to_dict()
    return {
        "status": "healthy",
        "service": "Interactive Route & Campus Navigator API",
        "version": "2.0.0",
        "experiment_14": "Map Navigator API Active",
        "experiment_15": "Frontend Integration Ready",
        "active_preset": app_state.current_preset,
        "stats": graph_dict["stats"],
        "timestamp": time.time(),
    }


@app.get("/api", include_in_schema=False)
def get_api_root() -> Dict[str, Any]:
    """Return health diagnostic status when hitting /api directly."""
    return get_health()


@app.get("/api/presets", tags=["System & Health"], summary="List Available Map Presets")
def get_presets() -> Dict[str, Any]:
    """Retrieve catalog of pre-configured geographic and campus map datasets."""
    return {
        "active_preset": app_state.current_preset,
        "presets": list(PRESETS_METADATA.values()),
        "presets_map": PRESETS_METADATA,
    }


@app.post("/api/presets/{preset_id}/load", tags=["System & Health"], summary="Load Map Preset")
@app.get("/api/presets/{preset_id}/load", tags=["System & Health"], summary="Load Map Preset (GET fallback)")
@app.post("/api/presets/{preset_id}/load/", include_in_schema=False)
@app.get("/api/presets/{preset_id}/load/", include_in_schema=False)
def load_preset(
    preset_id: str = Path(..., description="Preset ID: 'india_highways' or 'campus_navigator'")
) -> Dict[str, Any]:
    """Switch active graph dataset to the requested preset and return loaded topology."""
    preset_key = preset_id.lower().strip()
    if preset_key not in PRESETS_METADATA:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_id}' not found. Available presets: {list(PRESETS_METADATA.keys())}",
        )

    app_state.reload_preset(preset_key)
    graph_dict = app_state.graph.to_dict()

    return {
        "message": f"Preset '{preset_key}' loaded successfully.",
        "active_preset": preset_key,
        "preset_metadata": PRESETS_METADATA[preset_key],
        "graph": graph_dict,
    }


# ==============================================================================
# REST API Endpoints: Routing & Pathfinding
# ==============================================================================

@app.get("/api/graph", tags=["Routing & Pathfinding"], summary="Retrieve Graph Topology")
def get_graph(
    preset: Optional[str] = Query(None, description="Optional active preset ID to load before returning"),
) -> Dict[str, Any]:
    """Return complete vertex list, deduplicated edges, adjacency lists, and connectivity stats."""
    if preset:
        _ensure_preset_loaded(preset=preset)
    return {
        "active_preset": app_state.current_preset,
        "preset_metadata": PRESETS_METADATA.get(app_state.current_preset, {}),
        "graph": app_state.graph.to_dict(),
    }


@app.post("/api/route", tags=["Routing & Pathfinding"], summary="Compute Optimal Route")
@app.post("/api/route/", include_in_schema=False)
def compute_route(req: RouteRequest) -> Dict[str, Any]:
    """
    Execute shortest path search between vertices or across multi-stop waypoints.
    Supports Dijkstra, A*, BFS, and DFS with step-by-step frontier animation frames.
    """
    # 1. Resolve ordered waypoints
    raw_waypoints: List[str] = []
    if req.waypoints:
        raw_waypoints = [w.strip() for w in req.waypoints if w and w.strip()]

    if req.source and req.target:
        if raw_waypoints:
            if raw_waypoints[0] != req.source:
                raw_waypoints.insert(0, req.source)
            if raw_waypoints[-1] != req.target:
                raw_waypoints.append(req.target)
        else:
            raw_waypoints = [req.source, req.target]
    elif req.source and not req.target and raw_waypoints:
        if raw_waypoints[0] != req.source:
            raw_waypoints.insert(0, req.source)
    elif req.target and not req.source and raw_waypoints:
        if raw_waypoints[-1] != req.target:
            raw_waypoints.append(req.target)

    _ensure_preset_loaded(req.preset, raw_waypoints)

    if len(raw_waypoints) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 nodes (source and target, or waypoints) must be specified to compute a route.",
        )

    # 2. Validate all waypoints exist in active graph
    missing_nodes = [nid for nid in raw_waypoints if nid not in app_state.graph.nodes]
    if missing_nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specified node(s) not found in active graph: {', '.join(missing_nodes)}",
        )

    # 3. Validate weight_mode
    weight_mode = req.weight_mode.lower().strip()
    if weight_mode not in ("effective", "distance"):
        weight_mode = "effective"

    # 4. Normalize algorithm
    algo = req.algorithm.lower().strip()
    algo_mapping = {
        "dijkstra": "dijkstra",
        "astar": "astar",
        "a_star": "astar",
        "a*": "astar",
        "bfs": "bfs",
        "dfs": "dfs",
    }
    if algo not in algo_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported algorithm '{req.algorithm}'. Supported options: dijkstra, astar, bfs, dfs",
        )
    normalized_algo = algo_mapping[algo]

    # 5. Execute computation
    if len(raw_waypoints) > 2:
        result = multi_stop_route(
            graph=app_state.graph,
            waypoints=raw_waypoints,
            algorithm=normalized_algo,
            weight_mode=weight_mode,
        )
    else:
        src, dst = raw_waypoints[0], raw_waypoints[1]
        if normalized_algo == "dijkstra":
            result = dijkstra(app_state.graph, src, dst, weight_mode=weight_mode)
        elif normalized_algo == "astar":
            result = a_star(app_state.graph, src, dst, weight_mode=weight_mode)
        elif normalized_algo == "bfs":
            result = bfs_shortest_hops(app_state.graph, src, dst, weight_mode=weight_mode)
        elif normalized_algo == "dfs":
            result = dfs_path(app_state.graph, src, dst, weight_mode=weight_mode)

    return result


@app.post("/api/multi-stop", tags=["Routing & Pathfinding"], summary="Multi-Stop Waypoint Navigation")
def compute_multi_stop(req: MultiStopRequest) -> Dict[str, Any]:
    """Execute sequential waypoint routing across arbitrary checkpoints."""
    raw_waypoints: List[str] = []
    if req.waypoints:
        raw_waypoints = [w.strip() for w in req.waypoints if w and w.strip()]

    if req.source and req.target:
        if raw_waypoints:
            if raw_waypoints[0] != req.source:
                raw_waypoints.insert(0, req.source)
            if raw_waypoints[-1] != req.target:
                raw_waypoints.append(req.target)
        else:
            raw_waypoints = [req.source, req.target]
    elif req.source and not req.target and raw_waypoints:
        if raw_waypoints[0] != req.source:
            raw_waypoints.insert(0, req.source)
    elif req.target and not req.source and raw_waypoints:
        if raw_waypoints[-1] != req.target:
            raw_waypoints.append(req.target)

    _ensure_preset_loaded(req.preset, raw_waypoints)

    if len(raw_waypoints) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 nodes must be specified for multi-stop navigation.",
        )

    missing = [nid for nid in raw_waypoints if nid not in app_state.graph.nodes]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specified node(s) not found in active graph: {', '.join(missing)}",
        )

    algo = req.algorithm.lower().strip()
    if algo in ("astar", "a_star", "a*"):
        algo = "astar"
    elif algo not in ("dijkstra", "bfs", "dfs"):
        algo = "dijkstra"

    weight_mode = req.weight_mode.lower().strip()
    if weight_mode not in ("effective", "distance"):
        weight_mode = "effective"

    res = multi_stop_route(app_state.graph, raw_waypoints, algorithm=algo, weight_mode=weight_mode)
    res["full_path"] = list(res.get("path", []))
    res["total_cost"] = res.get("effective_cost", 0.0)
    res["total_time_min"] = res.get("estimated_time_min", 0.0)
    return res


@app.post("/api/compare", tags=["Routing & Pathfinding"], summary="Benchmark All Pathfinding Algorithms")
@app.post("/api/compare/", include_in_schema=False)
def benchmark_compare(req: CompareRequest) -> Dict[str, Any]:
    """
    Run Dijkstra, A*, BFS, and DFS simultaneously on the current graph topology.
    Returns side-by-side performance metrics, path lengths, explored node counts, and speedups.
    """
    src = req.source.strip()
    dst = req.target.strip()

    _ensure_preset_loaded(req.preset, [src, dst])

    if src not in app_state.graph.nodes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source node '{src}' does not exist.")
    if dst not in app_state.graph.nodes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target node '{dst}' does not exist.")

    weight_mode = req.weight_mode.lower().strip()
    if weight_mode not in ("effective", "distance"):
        weight_mode = "effective"

    comp = compare_algorithms(app_state.graph, src, dst, weight_mode=weight_mode)
    if isinstance(comp.get("analysis"), list):
        comp["analysis_points"] = list(comp["analysis"])
        comp["analysis"] = " \n".join(comp["analysis"])
    return comp


# ==============================================================================
# REST API Endpoints: Topology & Graph Management
# ==============================================================================

@app.post("/api/node", tags=["Graph Management"], summary="Add Node to Graph")
def add_node(req: NodeCreateRequest) -> Dict[str, Any]:
    """Insert a new vertex into the active graph with geospatial coordinates."""
    if req.id and req.id.strip():
        node_id = req.id.strip()
        if node_id in app_state.graph.nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Node with ID '{node_id}' already exists in the graph.",
            )
    else:
        node_id = _slugify_node_id(req.name, set(app_state.graph.nodes.keys()))

    new_node = Node(
        id=node_id,
        name=req.name.strip(),
        lat=float(req.lat),
        lng=float(req.lng),
        category=req.category.strip(),
        description=req.description.strip(),
    )

    app_state.graph.add_node(new_node)

    return {
        "message": f"Node '{new_node.name}' ({new_node.id}) successfully added.",
        "node": new_node.to_dict(),
        "stats": app_state.graph.to_dict()["stats"],
    }


@app.delete("/api/node/{node_id}", tags=["Graph Management"], summary="Delete Node from Graph")
def delete_node(
    node_id: str = Path(..., description="Unique ID of node to remove")
) -> Dict[str, Any]:
    """Remove a vertex and all its incident incoming and outgoing edges."""
    if node_id not in app_state.graph.nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in active graph.",
        )

    node_label = app_state.graph.nodes[node_id].name
    app_state.graph.remove_node(node_id)

    return {
        "message": f"Node '{node_label}' ({node_id}) and all incident edges removed.",
        "stats": app_state.graph.to_dict()["stats"],
    }


@app.post("/api/edge", tags=["Graph Management"], summary="Add Edge to Graph")
def add_edge(req: EdgeCreateRequest) -> Dict[str, Any]:
    """
    Connect two existing nodes with a directed or bidirectional edge.
    Automatically calculates Haversine distance with road curvature if base_distance_km is omitted.
    """
    src = req.source.strip()
    dst = req.target.strip()

    if src not in app_state.graph.nodes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source node '{src}' does not exist.")
    if dst not in app_state.graph.nodes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target node '{dst}' does not exist.")
    if src == dst:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Self-loop edges are not allowed.")

    edge = app_state.graph.add_edge(
        source=src,
        target=dst,
        base_distance_km=req.base_distance_km,
        road_name=req.road_name.strip(),
        traffic_multiplier=float(req.traffic_multiplier),
        is_blocked=bool(req.is_blocked),
        speed_limit_kmh=float(req.speed_limit_kmh),
        bidirectional=bool(req.bidirectional),
    )

    return {
        "message": f"Edge between '{src}' and '{dst}' created successfully.",
        "edge": edge.to_dict(),
        "stats": app_state.graph.to_dict()["stats"],
    }


@app.delete("/api/edge", tags=["Graph Management"], summary="Delete Edge from Graph")
def delete_edge(
    source: str = Query(..., description="Source node ID"),
    target: str = Query(..., description="Target node ID"),
    bidirectional: bool = Query(True, description="Remove both directions if True"),
) -> Dict[str, Any]:
    """Remove a connection between two nodes."""
    src = source.strip()
    dst = target.strip()

    removed = app_state.graph.remove_edge(src, dst, bidirectional=bidirectional)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge between '{src}' and '{dst}' does not exist.",
        )

    return {
        "message": f"Edge between '{src}' and '{dst}' removed successfully.",
        "stats": app_state.graph.to_dict()["stats"],
    }


@app.patch("/api/edge/traffic", tags=["Traffic & Congestion"], summary="Update Edge Traffic & Blockades")
def update_edge_traffic(req: EdgeTrafficUpdateRequest) -> Dict[str, Any]:
    """Modify traffic multiplier factor and roadblock status for a specific road segment."""
    src = req.source.strip()
    dst = req.target.strip()

    updated = app_state.graph.update_edge_traffic(
        source=src,
        target=dst,
        traffic_multiplier=req.traffic_multiplier,
        is_blocked=req.is_blocked,
        bidirectional=req.bidirectional,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge between '{src}' and '{dst}' does not exist.",
        )

    edge = app_state.graph.get_edge(src, dst)

    return {
        "message": f"Traffic conditions for '{src}' <-> '{dst}' updated.",
        "edge": edge.to_dict() if edge else None,
        "stats": app_state.graph.to_dict()["stats"],
    }


@app.post("/api/graph/simulate-traffic", tags=["Traffic & Congestion"], summary="Simulate Live Traffic & Roadblocks")
@app.post("/api/graph/simulate-traffic/", include_in_schema=False)
@app.get("/api/graph/simulate-traffic", include_in_schema=False)
@app.get("/api/graph/simulate-traffic/", include_in_schema=False)
def simulate_traffic(
    req: Optional[RandomTrafficRequest] = Body(None),
    reset: bool = Query(False, description="Reset all traffic and closures to normal if True"),
) -> Dict[str, Any]:
    """
    Randomly inject realistic congestion factors (1.4x - 2.8x) and emergency road closures
    to stress-test pathfinding algorithms and visualize rerouting behavior.
    """
    should_reset = reset or (req is not None and req.reset)

    # 1. Reset requested
    if should_reset:
        for u in app_state.graph.adjacency_list:
            for v, edge in app_state.graph.adjacency_list[u].items():
                edge.traffic_multiplier = 1.0
                edge.is_blocked = False

        return {
            "status": "success",
            "message": "All edge traffic multipliers reset to 1.0x and all roadblocks cleared.",
            "congested_count": 0,
            "blocked_count": 0,
            "stats": app_state.graph.to_dict()["stats"],
        }

    # 2. Simulation parameters
    cong_prob = req.congestion_probability if req else 0.35
    blk_prob = req.block_probability if req else 0.08

    # Extract unique undirected edge pairs
    unique_pairs = set()
    for u, neighbors in app_state.graph.adjacency_list.items():
        for v in neighbors:
            unique_pairs.add(tuple(sorted([u, v])))

    pair_list = list(unique_pairs)
    random.shuffle(pair_list)

    # Reset existing conditions first for clean simulation
    for u in app_state.graph.adjacency_list:
        for v, edge in app_state.graph.adjacency_list[u].items():
            edge.traffic_multiplier = 1.0
            edge.is_blocked = False

    congested_count = 0
    blocked_count = 0

    traffic_options = [1.4, 1.6, 1.8, 2.2, 2.8]

    # Target roadblock quota (1-3 roads max to prevent complete disconnection)
    max_blocks = min(3, max(1, int(len(pair_list) * blk_prob)))
    target_congested = int(len(pair_list) * cong_prob)

    for i, (u, v) in enumerate(pair_list):
        if blocked_count < max_blocks and random.random() < blk_prob:
            app_state.graph.update_edge_traffic(u, v, traffic_multiplier=1.0, is_blocked=True, bidirectional=True)
            blocked_count += 1
        elif congested_count < target_congested and random.random() < cong_prob:
            mult = random.choice(traffic_options)
            app_state.graph.update_edge_traffic(u, v, traffic_multiplier=mult, is_blocked=False, bidirectional=True)
            congested_count += 1

    return {
        "status": "success",
        "message": f"Traffic simulation applied: {congested_count} congested segments, {blocked_count} roadblocks active.",
        "congested_count": congested_count,
        "blocked_count": blocked_count,
        "stats": app_state.graph.to_dict()["stats"],
    }


@app.post("/api/traffic/simulate", tags=["Traffic & Congestion"], summary="Simulate Live Traffic & Roadblocks (Alias)")
def simulate_traffic_alias(
    req: Optional[RandomTrafficRequest] = Body(None),
    reset: bool = Query(False, description="Reset all traffic and closures to normal if True"),
) -> Dict[str, Any]:
    """Alias for /api/graph/simulate-traffic contract compatibility."""
    return simulate_traffic(req=req, reset=reset)


@app.post("/api/graph/reset-traffic", tags=["Traffic & Congestion"], summary="Reset All Traffic to Normal")
@app.post("/api/graph/reset-traffic/", include_in_schema=False)
@app.get("/api/graph/reset-traffic", include_in_schema=False)
@app.get("/api/graph/reset-traffic/", include_in_schema=False)
def reset_traffic() -> Dict[str, Any]:
    """Restore all graph edges to baseline traffic multiplier (1.0) and unblocked state."""
    for u in app_state.graph.adjacency_list:
        for v, edge in app_state.graph.adjacency_list[u].items():
            edge.traffic_multiplier = 1.0
            edge.is_blocked = False

    return {
        "message": "All traffic congestion multipliers and road closures have been reset to normal.",
        "stats": app_state.graph.to_dict()["stats"],
    }


# ==============================================================================
# Static File Hosting & Frontend Client Entry Point
# ==============================================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
STATIC_DIR = PUBLIC_DIR if os.path.isdir(PUBLIC_DIR) else FRONTEND_DIR
CSS_DIR = os.path.join(STATIC_DIR, "css")
JS_DIR = os.path.join(STATIC_DIR, "js")

# Ensure directories exist so StaticFiles mount does not fail
os.makedirs(CSS_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)

app.mount("/css", StaticFiles(directory=CSS_DIR), name="css")
app.mount("/js", StaticFiles(directory=JS_DIR), name="js")


@app.get("/", include_in_schema=False)
def serve_index() -> Any:
    """Serve the interactive map client UI or an informative onboarding splash screen."""
    for candidate_dir in [PUBLIC_DIR, FRONTEND_DIR]:
        index_html = os.path.join(candidate_dir, "index.html")
        if os.path.isfile(index_html):
            return FileResponse(index_html)

    # Informative fallback if frontend client is loading
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Route & Campus Navigator - Experiment 14 & 15</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); max-width: 580px; text-align: center; border: 1px solid #334155; }
        h1 { margin-top: 0; color: #38bdf8; font-size: 1.8rem; }
        p { color: #94a3b8; line-height: 1.6; }
        .btn { display: inline-block; background: #0284c7; color: white; padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 0.5rem; font-weight: 600; margin-top: 1rem; transition: background 0.2s; }
        .btn:hover { background: #0369a1; }
        .badge { background: #0369a1; color: #e0f2fe; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.8rem; margin: 0 0.25rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🗺️ Smart Route & Campus Navigator</h1>
        <p><strong>Experiment 14 (REST API Deployment) & Experiment 15 (Interactive Map Navigator)</strong></p>
        <p>Backend algorithmic graph engine is <span class="badge">ACTIVE</span> and running.</p>
        <p>Explore the live interactive OpenAPI / Swagger specifications and benchmark endpoints:</p>
        <a href="/docs" class="btn">🚀 Open Swagger UI Docs (/docs)</a>
        <br><br>
        <a href="/redoc" style="color: #38bdf8; text-decoration: none; font-size: 0.9rem;">View ReDoc Specification (/redoc)</a>
    </div>
</body>
</html>""",
        status_code=200,
    )
