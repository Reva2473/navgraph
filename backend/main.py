"""
================================================================================
Backend REST API Server for Minor Project:
Experiment 14: REST API Server & Algorithmic Deployment
Experiment 15: Interactive Frontend Map Navigator Integration
================================================================================
"""

import os
import random
import re
import threading
import time
import urllib.parse
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Path, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

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
# Limits & Validation Constants
# ==============================================================================

MAX_NODES = 200
MAX_DIRECTED_EDGES = 4000
MAX_SESSIONS = 500
SESSION_TTL_SECONDS = 6 * 60 * 60
# Haversine values are rounded to 2 decimals, so allow a small tolerance.
DISTANCE_TOLERANCE_KM = 0.01

NODE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
SESSION_HEADER = "X-Session-Id"

# ==============================================================================
# In-Memory Application State
# ==============================================================================

class AppState:
    """One graph plus its active preset. Each browser session gets its own instance."""

    def __init__(self, default_preset: str = "india_highways"):
        self.lock = threading.RLock()
        self.current_preset: str = default_preset
        self.graph: WeightedGraph = load_preset_graph(default_preset)
        self.last_used: float = time.time()

    def reload_preset(self, preset_id: str) -> None:
        preset_key = preset_id.lower().strip()
        if preset_key not in PRESETS_METADATA:
            raise ValueError(f"Unknown preset '{preset_id}'. Valid: {list(PRESETS_METADATA.keys())}")
        with self.lock:
            self.graph = load_preset_graph(preset_key)
            self.current_preset = preset_key


class SessionStore:
    """Bounded LRU store of per-session graphs with idle expiry."""

    def __init__(self, max_sessions: int = MAX_SESSIONS, ttl_seconds: int = SESSION_TTL_SECONDS):
        self._sessions: "OrderedDict[str, AppState]" = OrderedDict()
        self._lock = threading.Lock()
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds

    def _evict(self, now: float) -> None:
        expired = [sid for sid, st in self._sessions.items() if now - st.last_used > self.ttl_seconds]
        for sid in expired:
            del self._sessions[sid]
        while len(self._sessions) > self.max_sessions:
            self._sessions.popitem(last=False)

    def get(self, sid: str) -> Optional[AppState]:
        with self._lock:
            st = self._sessions.get(sid)
            if st is not None:
                st.last_used = time.time()
                self._sessions.move_to_end(sid)
            return st

    def put(self, sid: str, st: AppState) -> AppState:
        with self._lock:
            st.last_used = time.time()
            self._sessions[sid] = st
            self._sessions.move_to_end(sid)
            self._evict(st.last_used)
            return st

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


# Shared state used by clients that do not send a session header (Swagger UI, curl, tests).
app_state = AppState(default_preset="india_highways")
sessions = SessionStore()


def _session_id(request: Request) -> Optional[str]:
    sid = request.headers.get(SESSION_HEADER)
    if sid is None:
        return None
    sid = sid.strip()
    if not SESSION_ID_RE.match(sid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {SESSION_HEADER} header.")
    return sid


def get_state(request: Request, create: bool = False) -> AppState:
    """
    Resolve the graph state for this request.
    - No session header: the shared default state.
    - Known session: that session's state.
    - Unknown session: a fresh state if `create`, otherwise HTTP 409 so the client
      can re-upload its graph via POST /api/session/restore (e.g. after a serverless cold start).
    """
    sid = _session_id(request)
    if sid is None:
        return app_state
    st = sessions.get(sid)
    if st is not None:
        return st
    if create:
        return sessions.put(sid, AppState(default_preset="india_highways"))
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "session_expired", "message": "Session state not found on this server instance; restore required."},
    )


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

#### Sessions
Send an `X-Session-Id` header to get a private graph. Without it, requests share one default graph.
If the server answers `409` with `code: session_expired`, re-upload the graph with `POST /api/session/restore`.
    """,
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "System & Health", "description": "System health verification, preset selection, and session management."},
        {"name": "Routing & Pathfinding", "description": "Shortest path computations, multi-stop routing, and algorithmic comparison."},
        {"name": "Graph Management", "description": "Dynamic vertex and edge CRUD operations with dynamic spatial geometry."},
        {"name": "Traffic & Congestion", "description": "Simulate live congestion, dynamic traffic multipliers, and emergency roadblocks."},
    ],
)

# No cookies or auth are used, so credentials stay disabled with a wildcard origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    """
    API responses and the HTML shell are never cached. Static CSS/JS may be stored
    but must be revalidated (ETag / 304), so deploys show up without a hard refresh.
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/css/") or path.startswith("/js/"):
        response.headers["Cache-Control"] = "no-cache"
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ==============================================================================
# Pydantic Request Models
# ==============================================================================

class RouteRequest(BaseModel):
    source: Optional[str] = Field(None, max_length=64, description="Starting node identifier (e.g. 'delhi')")
    target: Optional[str] = Field(None, max_length=64, description="Destination node identifier (e.g. 'bengaluru')")
    waypoints: Optional[List[str]] = Field(
        None,
        max_length=25,
        description="Ordered list of waypoint node IDs (inclusive of start and destination, or intermediate stops)",
    )
    algorithm: str = Field(
        "dijkstra",
        max_length=20,
        description="Pathfinding algorithm: 'dijkstra', 'astar', 'bfs', or 'dfs'",
    )
    weight_mode: str = Field(
        "effective",
        max_length=20,
        description="Weight metric: 'effective' (accounts for traffic and closures) or 'distance' (raw physical km)",
    )
    preset: Optional[str] = Field(
        None,
        max_length=64,
        description="Optional preset ID; if it differs from the active preset, that preset is loaded first",
    )


class MultiStopRequest(RouteRequest):
    pass


class CompareRequest(BaseModel):
    source: str = Field(..., max_length=64, description="Starting node identifier")
    target: str = Field(..., max_length=64, description="Destination node identifier")
    weight_mode: str = Field(
        "effective",
        max_length=20,
        description="Weight calculation mode: 'effective' (traffic-weighted) or 'distance' (raw base km)",
    )
    preset: Optional[str] = Field(
        None,
        max_length=64,
        description="Optional preset ID; if it differs from the active preset, that preset is loaded first",
    )


class NodeCreateRequest(BaseModel):
    id: Optional[str] = Field(
        None,
        pattern=NODE_ID_PATTERN,
        description="Custom unique node identifier (letters, digits, '_' or '-'). Auto-generated from name if omitted.",
    )
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable node label (e.g. 'Cyber Hub', 'Agra')")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate in decimal degrees")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate in decimal degrees")
    category: str = Field("custom", max_length=40, description="Category tag (e.g. 'city', 'hub', 'academic', 'custom')")
    description: str = Field("Custom user location", max_length=300, description="Descriptive notes or metadata")

    @field_validator("id", mode="before")
    @classmethod
    def _blank_id_is_auto(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v


class EdgeCreateRequest(BaseModel):
    source: str = Field(..., max_length=64, description="Source node ID")
    target: str = Field(..., max_length=64, description="Target node ID")
    base_distance_km: Optional[float] = Field(
        None,
        le=50000.0,
        description=(
            "Physical length in km. If omitted or <=0, computed from Haversine distance x 1.15. "
            "Must not be shorter than the straight-line distance between the nodes."
        ),
    )
    road_name: str = Field("Custom Route", max_length=100, description="Highway or corridor label (e.g. 'NH44', 'Ring Road')")
    traffic_multiplier: float = Field(1.0, ge=1.0, le=10.0, description="Congestion multiplier (1.0 = clear, 2.0 = double duration)")
    is_blocked: bool = Field(False, description="Flag indicating whether road is impassable")
    speed_limit_kmh: float = Field(60.0, gt=0.0, le=300.0, description="Speed limit in km/h")
    bidirectional: bool = Field(True, description="Create reverse edge automatically if True")


class EdgeTrafficUpdateRequest(BaseModel):
    source: str = Field(..., max_length=64, description="Source node ID")
    target: str = Field(..., max_length=64, description="Target node ID")
    traffic_multiplier: Optional[float] = Field(None, ge=1.0, le=10.0, description="New congestion multiplier (1.0 - 10.0)")
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


class RestoreNode(BaseModel):
    id: str = Field(..., pattern=NODE_ID_PATTERN)
    name: str = Field(..., min_length=1, max_length=100)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    category: str = Field("custom", max_length=40)
    description: str = Field("", max_length=300)


class RestoreEdge(BaseModel):
    target: str = Field(..., pattern=NODE_ID_PATTERN)
    base_distance_km: float = Field(..., gt=0.0, le=50000.0)
    road_name: str = Field("Route", max_length=100)
    traffic_multiplier: float = Field(1.0, ge=1.0, le=10.0)
    is_blocked: bool = False
    speed_limit_kmh: float = Field(60.0, gt=0.0, le=300.0)


class SessionRestoreRequest(BaseModel):
    preset: str = Field(..., max_length=64, description="Preset the client graph was derived from")
    nodes: List[RestoreNode] = Field(..., max_length=MAX_NODES)
    adjacency_list: Dict[str, List[RestoreEdge]] = Field(
        default_factory=dict,
        description="Directed edges keyed by source node ID (same shape as GET /api/graph adjacency_list)",
    )


# ==============================================================================
# Helper Utilities
# ==============================================================================

ALGO_ALIASES = {
    "dijkstra": "dijkstra",
    "astar": "astar",
    "a_star": "astar",
    "a*": "astar",
    "bfs": "bfs",
    "dfs": "dfs",
}

SINGLE_ROUTE_RUNNERS = {
    "dijkstra": dijkstra,
    "astar": a_star,
    "bfs": bfs_shortest_hops,
    "dfs": dfs_path,
}


def _slugify_node_id(name: str, existing_ids: set) -> str:
    """Generate a clean, unique alphanumeric identifier from a display name."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower().strip()).strip("_")[:56]
    if not clean:
        clean = "node"
    candidate = clean
    counter = 1
    while candidate in existing_ids:
        candidate = f"{clean}_{counter}"
        counter += 1
    return candidate


def _normalize_weight_mode(mode: str) -> str:
    mode = (mode or "").lower().strip()
    return mode if mode in ("effective", "distance") else "effective"


def _normalize_algorithm(algorithm: str) -> str:
    algo = (algorithm or "").lower().strip()
    if algo not in ALGO_ALIASES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported algorithm '{algorithm}'. Supported options: dijkstra, astar, bfs, dfs",
        )
    return ALGO_ALIASES[algo]


def _resolve_waypoints(source: Optional[str], target: Optional[str], waypoints: Optional[List[str]]) -> List[str]:
    """Merge source / target / waypoints into one ordered list of stops."""
    stops = [w.strip() for w in (waypoints or []) if w and w.strip()]
    source = source.strip() if source else None
    target = target.strip() if target else None

    if source and target and not stops:
        return [source, target]
    if source and (not stops or stops[0] != source):
        stops.insert(0, source)
    if target and (not stops or stops[-1] != target):
        stops.append(target)
    return stops


def _apply_explicit_preset(st: AppState, preset: Optional[str]) -> None:
    """Load `preset` if the caller named a valid preset that is not already active."""
    if not preset:
        return
    key = preset.lower().strip()
    if key in PRESETS_METADATA and st.current_preset != key:
        st.reload_preset(key)


def _require_nodes(st: AppState, node_ids: List[str]) -> None:
    missing = [nid for nid in node_ids if nid not in st.graph.nodes]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specified node(s) not found in active graph: {', '.join(missing)}",
        )


def _check_edge_distance(graph: WeightedGraph, src: str, dst: str, distance: Optional[float]) -> None:
    """Reject road lengths shorter than the straight line; they would make the A* heuristic inadmissible."""
    if distance is None or distance <= 0:
        return
    a, b = graph.nodes[src], graph.nodes[dst]
    straight = haversine_distance(a.lat, a.lng, b.lat, b.lng)
    if distance + DISTANCE_TOLERANCE_KM < straight:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Road length {distance} km is shorter than the straight-line distance "
                f"{straight} km between '{src}' and '{dst}'."
            ),
        )


def _reset_all_traffic(graph: WeightedGraph) -> None:
    for neighbors in graph.adjacency_list.values():
        for edge in neighbors.values():
            edge.traffic_multiplier = 1.0
            edge.is_blocked = False


def _run_route(st: AppState, req: RouteRequest, min_message: str) -> Dict[str, Any]:
    stops = _resolve_waypoints(req.source, req.target, req.waypoints)
    if len(stops) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=min_message)

    algo = _normalize_algorithm(req.algorithm)
    weight_mode = _normalize_weight_mode(req.weight_mode)

    with st.lock:
        _apply_explicit_preset(st, req.preset)
        _require_nodes(st, stops)
        if len(stops) > 2:
            return multi_stop_route(st.graph, stops, algorithm=algo, weight_mode=weight_mode)
        return SINGLE_ROUTE_RUNNERS[algo](st.graph, stops[0], stops[1], weight_mode=weight_mode)


# ==============================================================================
# REST API Endpoints: System & Health
# ==============================================================================

@app.get("/api/health", tags=["System & Health"], summary="Service Health & Diagnostic Status")
def get_health(request: Request) -> Dict[str, Any]:
    """Return backend server status, active preset, and graph topology diagnostics."""
    sid = _session_id(request)
    st = (sessions.get(sid) if sid else None) or app_state
    with st.lock:
        stats = st.graph.to_dict()["stats"]
        preset = st.current_preset
    return {
        "status": "healthy",
        "service": "Interactive Route & Campus Navigator API",
        "version": "2.1.0",
        "experiment_14": "Map Navigator API Active",
        "experiment_15": "Frontend Integration Ready",
        "active_preset": preset,
        "stats": stats,
        "timestamp": time.time(),
    }


@app.get("/api", include_in_schema=False)
def get_api_root(request: Request) -> Dict[str, Any]:
    """Return health diagnostic status when hitting /api directly."""
    return get_health(request)


@app.get("/api/presets", tags=["System & Health"], summary="List Available Map Presets")
def get_presets(request: Request) -> Dict[str, Any]:
    """Retrieve catalog of pre-configured geographic and campus map datasets."""
    sid = _session_id(request)
    st = (sessions.get(sid) if sid else None) or app_state
    return {
        "active_preset": st.current_preset,
        "presets": list(PRESETS_METADATA.values()),
        "presets_map": PRESETS_METADATA,
    }


@app.post("/api/presets/{preset_id}/load", tags=["System & Health"], summary="Load Map Preset")
@app.get("/api/presets/{preset_id}/load", tags=["System & Health"], summary="Load Map Preset (GET fallback)")
@app.post("/api/presets/{preset_id}/load/", include_in_schema=False)
@app.get("/api/presets/{preset_id}/load/", include_in_schema=False)
def load_preset(
    request: Request,
    preset_id: str = Path(..., max_length=64, description="Preset ID: 'india_highways' or 'campus_navigator'"),
) -> Dict[str, Any]:
    """Switch the caller's graph to the requested preset and return the loaded topology."""
    preset_key = preset_id.lower().strip()
    if preset_key not in PRESETS_METADATA:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_id}' not found. Available presets: {list(PRESETS_METADATA.keys())}",
        )

    st = get_state(request, create=True)
    with st.lock:
        st.reload_preset(preset_key)
        graph_dict = st.graph.to_dict()

    return {
        "message": f"Preset '{preset_key}' loaded successfully.",
        "active_preset": preset_key,
        "preset_metadata": PRESETS_METADATA[preset_key],
        "graph": graph_dict,
    }


@app.post("/api/session/restore", tags=["System & Health"], summary="Restore Session Graph")
def restore_session(request: Request, req: SessionRestoreRequest) -> Dict[str, Any]:
    """
    Rebuild a session's graph from a client snapshot. Used when a request lands on a
    server instance that does not hold the session (serverless cold start or eviction).
    """
    sid = _session_id(request)
    if sid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{SESSION_HEADER} header is required.")

    preset_key = req.preset.lower().strip()
    if preset_key not in PRESETS_METADATA:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown preset '{req.preset}'.")

    graph = WeightedGraph()
    for n in req.nodes:
        if n.id in graph.nodes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Duplicate node ID '{n.id}'.")
        graph.add_node(Node(n.id, n.name.strip(), n.lat, n.lng, n.category, n.description))

    edge_count = sum(len(v) for v in req.adjacency_list.values())
    if edge_count > MAX_DIRECTED_EDGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Too many edges (max {MAX_DIRECTED_EDGES}).")

    for src, edges in req.adjacency_list.items():
        if src not in graph.nodes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown edge source '{src}'.")
        for e in edges:
            if e.target not in graph.nodes or e.target == src:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid edge '{src}' -> '{e.target}'.")
            _check_edge_distance(graph, src, e.target, e.base_distance_km)
            graph.add_edge(
                source=src,
                target=e.target,
                base_distance_km=e.base_distance_km,
                road_name=e.road_name,
                traffic_multiplier=e.traffic_multiplier,
                is_blocked=e.is_blocked,
                speed_limit_kmh=e.speed_limit_kmh,
                bidirectional=False,
            )

    st = AppState(default_preset=preset_key)
    st.graph = graph
    sessions.put(sid, st)

    return {
        "message": "Session graph restored.",
        "active_preset": preset_key,
        "stats": graph.to_dict()["stats"],
    }


# ==============================================================================
# REST API Endpoints: Routing & Pathfinding
# ==============================================================================

@app.get("/api/graph", tags=["Routing & Pathfinding"], summary="Retrieve Graph Topology")
def get_graph(
    request: Request,
    preset: Optional[str] = Query(None, max_length=64, description="Optional preset ID to load if it is not already active"),
) -> Dict[str, Any]:
    """Return complete vertex list, deduplicated edges, adjacency lists, and connectivity stats."""
    st = get_state(request)
    with st.lock:
        _apply_explicit_preset(st, preset)
        return {
            "active_preset": st.current_preset,
            "preset_metadata": PRESETS_METADATA.get(st.current_preset, {}),
            "graph": st.graph.to_dict(),
        }


@app.post("/api/route", tags=["Routing & Pathfinding"], summary="Compute Optimal Route")
@app.post("/api/route/", include_in_schema=False)
def compute_route(request: Request, req: RouteRequest) -> Dict[str, Any]:
    """
    Execute shortest path search between vertices or across multi-stop waypoints.
    Supports Dijkstra, A*, BFS, and DFS with step-by-step frontier animation frames.
    """
    st = get_state(request)
    return _run_route(
        st, req, "At least 2 nodes (source and target, or waypoints) must be specified to compute a route."
    )


@app.post("/api/multi-stop", tags=["Routing & Pathfinding"], summary="Multi-Stop Waypoint Navigation")
def compute_multi_stop(request: Request, req: MultiStopRequest) -> Dict[str, Any]:
    """Execute sequential waypoint routing across arbitrary checkpoints."""
    st = get_state(request)
    res = _run_route(st, req, "At least 2 nodes must be specified for multi-stop navigation.")
    res["full_path"] = list(res.get("path", []))
    res["total_cost"] = res.get("effective_cost", 0.0)
    res["total_time_min"] = res.get("estimated_time_min", 0.0)
    return res


@app.post("/api/compare", tags=["Routing & Pathfinding"], summary="Benchmark All Pathfinding Algorithms")
@app.post("/api/compare/", include_in_schema=False)
def benchmark_compare(request: Request, req: CompareRequest) -> Dict[str, Any]:
    """
    Run Dijkstra, A*, BFS, and DFS simultaneously on the current graph topology.
    Returns side-by-side performance metrics, path lengths, explored node counts, and speedups.
    """
    st = get_state(request)
    src = req.source.strip()
    dst = req.target.strip()
    weight_mode = _normalize_weight_mode(req.weight_mode)

    with st.lock:
        _apply_explicit_preset(st, req.preset)
        if src not in st.graph.nodes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source node '{src}' does not exist.")
        if dst not in st.graph.nodes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target node '{dst}' does not exist.")
        comp = compare_algorithms(st.graph, src, dst, weight_mode=weight_mode)

    if isinstance(comp.get("analysis"), list):
        comp["analysis_points"] = list(comp["analysis"])
        comp["analysis"] = " \n".join(comp["analysis"])
    return comp


# ==============================================================================
# REST API Endpoints: Topology & Graph Management
# ==============================================================================

@app.post("/api/node", tags=["Graph Management"], summary="Add Node to Graph")
def add_node(request: Request, req: NodeCreateRequest) -> Dict[str, Any]:
    """Insert a new vertex into the active graph with geospatial coordinates."""
    st = get_state(request)
    with st.lock:
        if len(st.graph.nodes) >= MAX_NODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Graph node limit reached ({MAX_NODES}).",
            )
        if req.id:
            node_id = req.id
            if node_id in st.graph.nodes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Node with ID '{node_id}' already exists in the graph.",
                )
        else:
            node_id = _slugify_node_id(req.name, set(st.graph.nodes.keys()))

        new_node = Node(
            id=node_id,
            name=req.name.strip(),
            lat=float(req.lat),
            lng=float(req.lng),
            category=req.category.strip() or "custom",
            description=req.description.strip(),
        )
        st.graph.add_node(new_node)
        stats = st.graph.to_dict()["stats"]

    return {
        "message": f"Node '{new_node.name}' ({new_node.id}) successfully added.",
        "node": new_node.to_dict(),
        "stats": stats,
    }


@app.delete("/api/node/{node_id}", tags=["Graph Management"], summary="Delete Node from Graph")
def delete_node(
    request: Request,
    node_id: str = Path(..., max_length=64, description="Unique ID of node to remove"),
) -> Dict[str, Any]:
    """Remove a vertex and all its incident incoming and outgoing edges."""
    st = get_state(request)
    with st.lock:
        if node_id not in st.graph.nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node '{node_id}' not found in active graph.",
            )
        node_label = st.graph.nodes[node_id].name
        st.graph.remove_node(node_id)
        stats = st.graph.to_dict()["stats"]

    return {
        "message": f"Node '{node_label}' ({node_id}) and all incident edges removed.",
        "stats": stats,
    }


@app.post("/api/edge", tags=["Graph Management"], summary="Add Edge to Graph")
def add_edge(request: Request, req: EdgeCreateRequest) -> Dict[str, Any]:
    """
    Connect two existing nodes with a directed or bidirectional edge.
    Automatically calculates Haversine distance with road curvature if base_distance_km is omitted.
    """
    st = get_state(request)
    src = req.source.strip()
    dst = req.target.strip()

    with st.lock:
        if src not in st.graph.nodes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source node '{src}' does not exist.")
        if dst not in st.graph.nodes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target node '{dst}' does not exist.")
        if src == dst:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Self-loop edges are not allowed.")
        _check_edge_distance(st.graph, src, dst, req.base_distance_km)

        current_edges = sum(len(v) for v in st.graph.adjacency_list.values())
        if current_edges + (2 if req.bidirectional else 1) > MAX_DIRECTED_EDGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Graph edge limit reached ({MAX_DIRECTED_EDGES}).",
            )

        edge = st.graph.add_edge(
            source=src,
            target=dst,
            base_distance_km=req.base_distance_km,
            road_name=req.road_name.strip() or "Custom Route",
            traffic_multiplier=float(req.traffic_multiplier),
            is_blocked=bool(req.is_blocked),
            speed_limit_kmh=float(req.speed_limit_kmh),
            bidirectional=bool(req.bidirectional),
        )
        stats = st.graph.to_dict()["stats"]

    return {
        "message": f"Edge between '{src}' and '{dst}' created successfully.",
        "edge": edge.to_dict(),
        "stats": stats,
    }


@app.delete("/api/edge", tags=["Graph Management"], summary="Delete Edge from Graph")
def delete_edge(
    request: Request,
    source: str = Query(..., max_length=64, description="Source node ID"),
    target: str = Query(..., max_length=64, description="Target node ID"),
    bidirectional: bool = Query(True, description="Remove both directions if True"),
) -> Dict[str, Any]:
    """Remove a connection between two nodes."""
    st = get_state(request)
    src = source.strip()
    dst = target.strip()

    with st.lock:
        removed = st.graph.remove_edge(src, dst, bidirectional=bidirectional)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edge between '{src}' and '{dst}' does not exist.",
            )
        stats = st.graph.to_dict()["stats"]

    return {
        "message": f"Edge between '{src}' and '{dst}' removed successfully.",
        "stats": stats,
    }


@app.patch("/api/edge/traffic", tags=["Traffic & Congestion"], summary="Update Edge Traffic & Blockades")
def update_edge_traffic(request: Request, req: EdgeTrafficUpdateRequest) -> Dict[str, Any]:
    """Modify traffic multiplier factor and roadblock status for a specific road segment."""
    st = get_state(request)
    src = req.source.strip()
    dst = req.target.strip()

    with st.lock:
        updated = st.graph.update_edge_traffic(
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
        edge = st.graph.get_edge(src, dst)
        stats = st.graph.to_dict()["stats"]

    return {
        "message": f"Traffic conditions for '{src}' <-> '{dst}' updated.",
        "edge": edge.to_dict() if edge else None,
        "stats": stats,
    }


@app.post("/api/graph/simulate-traffic", tags=["Traffic & Congestion"], summary="Simulate Live Traffic & Roadblocks")
@app.post("/api/graph/simulate-traffic/", include_in_schema=False)
def simulate_traffic(
    request: Request,
    req: Optional[RandomTrafficRequest] = Body(None),
    reset: bool = Query(False, description="Reset all traffic and closures to normal if True"),
) -> Dict[str, Any]:
    """
    Randomly inject realistic congestion factors (1.4x - 2.8x) and emergency road closures
    to stress-test pathfinding algorithms and visualize rerouting behavior.
    """
    st = get_state(request)
    should_reset = reset or (req is not None and req.reset)

    with st.lock:
        graph = st.graph
        _reset_all_traffic(graph)

        if should_reset:
            return {
                "status": "success",
                "message": "All edge traffic multipliers reset to 1.0x and all roadblocks cleared.",
                "congested_count": 0,
                "blocked_count": 0,
                "stats": graph.to_dict()["stats"],
            }

        cong_prob = req.congestion_probability if req else 0.35
        blk_prob = req.block_probability if req else 0.08

        # Unique undirected pairs, sorted first so shuffling is the only source of randomness.
        pair_list = sorted({tuple(sorted((u, v))) for u, nbrs in graph.adjacency_list.items() for v in nbrs})
        random.shuffle(pair_list)

        congested_count = 0
        blocked_count = 0
        traffic_options = [1.4, 1.6, 1.8, 2.2, 2.8]

        # Cap roadblocks at 3 to avoid disconnecting the graph.
        max_blocks = min(3, max(1, int(len(pair_list) * blk_prob)))
        target_congested = int(len(pair_list) * cong_prob)

        for u, v in pair_list:
            if blocked_count < max_blocks and random.random() < blk_prob:
                graph.update_edge_traffic(u, v, traffic_multiplier=1.0, is_blocked=True, bidirectional=True)
                blocked_count += 1
            elif congested_count < target_congested and random.random() < cong_prob:
                mult = random.choice(traffic_options)
                graph.update_edge_traffic(u, v, traffic_multiplier=mult, is_blocked=False, bidirectional=True)
                congested_count += 1

        stats = graph.to_dict()["stats"]

    return {
        "status": "success",
        "message": f"Traffic simulation applied: {congested_count} congested segments, {blocked_count} roadblocks active.",
        "congested_count": congested_count,
        "blocked_count": blocked_count,
        "stats": stats,
    }


@app.post("/api/traffic/simulate", tags=["Traffic & Congestion"], summary="Simulate Live Traffic & Roadblocks (Alias)")
def simulate_traffic_alias(
    request: Request,
    req: Optional[RandomTrafficRequest] = Body(None),
    reset: bool = Query(False, description="Reset all traffic and closures to normal if True"),
) -> Dict[str, Any]:
    """Alias for /api/graph/simulate-traffic contract compatibility."""
    return simulate_traffic(request=request, req=req, reset=reset)


@app.post("/api/graph/reset-traffic", tags=["Traffic & Congestion"], summary="Reset All Traffic to Normal")
@app.post("/api/graph/reset-traffic/", include_in_schema=False)
def reset_traffic(request: Request) -> Dict[str, Any]:
    """Restore all graph edges to baseline traffic multiplier (1.0) and unblocked state."""
    st = get_state(request)
    with st.lock:
        _reset_all_traffic(st.graph)
        stats = st.graph.to_dict()["stats"]

    return {
        "message": "All traffic congestion multipliers and road closures have been reset to normal.",
        "stats": stats,
    }


# ==============================================================================
# Static File Hosting & Frontend Client Entry Point
# ==============================================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(PROJECT_ROOT, "public")
CSS_DIR = os.path.join(STATIC_DIR, "css")
JS_DIR = os.path.join(STATIC_DIR, "js")

if os.path.isdir(CSS_DIR):
    app.mount("/css", StaticFiles(directory=CSS_DIR), name="css")
if os.path.isdir(JS_DIR):
    app.mount("/js", StaticFiles(directory=JS_DIR), name="js")


@app.get("/", include_in_schema=False)
def serve_index() -> Any:
    """Serve the interactive map client UI, or a small page pointing to the API docs."""
    index_html = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_html):
        return FileResponse(index_html)

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
