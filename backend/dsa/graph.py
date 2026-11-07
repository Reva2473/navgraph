"""
Graph Representation & Geospatial Utilities for Smart Route Optimization.

Implements an adjacency-list weighted graph with Haversine spherical distance calculations,
traffic multipliers, road blockades, and realistic road network modeling.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Set, Tuple


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two geographic coordinates
    on Earth using the Haversine formula.

    Formula:
        a = sin²(Δφ/2) + cos(φ1) * cos(φ2) * sin²(Δλ/2)
        c = 2 * atan2(√a, √(1−a))
        d = R * c

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lng1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lng2: Longitude of point 2 in decimal degrees.

    Returns:
        Great-circle distance in kilometers rounded to 2 decimal places.
    """
    radius_earth_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    # Clamp 'a' between 0.0 and 1.0 to prevent domain error due to floating point inaccuracies
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(radius_earth_km * c, 2)


@dataclass
class Node:
    """
    Represents a vertex in the spatial transport graph.

    Attributes:
        id: Unique identifier for the node (e.g. 'delhi', 'cs_dept').
        name: Human-readable display label.
        lat: Latitude in decimal degrees.
        lng: Longitude in decimal degrees.
        category: Semantic classification (e.g., 'metro', 'hub', 'gate', 'academic').
        description: Informative details about the landmark.
    """

    id: str
    name: str
    lat: float
    lng: float
    category: str = "city"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize node to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "category": self.category,
            "description": self.description,
        }


@dataclass
class Edge:
    """
    Represents a directed roadway/connection between two nodes.

    Attributes:
        source: Node ID where the edge originates.
        target: Node ID where the edge terminates.
        base_distance_km: Physical length of the road in kilometers.
        road_name: Designation of highway, avenue or corridor (e.g. 'NH48').
        traffic_multiplier: Congestion factor >= 1.0 (1.0 = clear flow, 1.5 = 50% slow down).
        is_blocked: Flag indicating whether road is closed/impassable.
        speed_limit_kmh: Expected baseline speed in km/h.
    """

    source: str
    target: str
    base_distance_km: float
    road_name: str = "Road"
    traffic_multiplier: float = 1.0
    is_blocked: bool = False
    speed_limit_kmh: float = 60.0

    @property
    def effective_weight(self) -> float:
        """
        Traffic-adjusted traversal cost.
        Returns infinity if blocked, else base_distance * traffic_multiplier.
        """
        if self.is_blocked:
            return float("inf")
        return round(self.base_distance_km * self.traffic_multiplier, 2)

    @property
    def estimated_time_min(self) -> float:
        """
        Estimated transit duration in minutes accounting for speed limit and traffic.
        Returns infinity if blocked.
        """
        if self.is_blocked:
            return float("inf")
        effective_speed = max(self.speed_limit_kmh, 1.0)
        # Hours = effective_distance / effective_speed; Minutes = Hours * 60
        duration = (self.base_distance_km * self.traffic_multiplier / effective_speed) * 60.0
        return round(duration, 1)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize edge to a JSON-compatible dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "base_distance_km": self.base_distance_km,
            "road_name": self.road_name,
            "traffic_multiplier": self.traffic_multiplier,
            "is_blocked": self.is_blocked,
            "speed_limit_kmh": self.speed_limit_kmh,
            "effective_weight": self.effective_weight,
            "estimated_time_min": self.estimated_time_min,
        }


class WeightedGraph:
    """
    Adjacency-list based weighted graph optimized for pathfinding and spatial analysis.

    Supports dynamic insertion/removal of vertices and edges, real-time traffic
    and blockage updates, and complete serialization for visualizer rendering.
    """

    def __init__(self) -> None:
        """Initialize an empty weighted graph."""
        self.nodes: Dict[str, Node] = {}
        # adjacency_list maps source_id -> {target_id: Edge}
        self.adjacency_list: Dict[str, Dict[str, Edge]] = {}

    def add_node(self, node: Node) -> Node:
        """
        Add a vertex to the graph.

        Args:
            node: Node instance to insert.

        Returns:
            The inserted Node.
        """
        self.nodes[node.id] = node
        if node.id not in self.adjacency_list:
            self.adjacency_list[node.id] = {}
        return node

    def remove_node(self, node_id: str) -> bool:
        """
        Remove a vertex and all its incident (incoming and outgoing) edges.

        Args:
            node_id: ID of the node to remove.

        Returns:
            True if removed, False if node did not exist.
        """
        if node_id not in self.nodes:
            return False

        # Remove from nodes map
        del self.nodes[node_id]

        # Remove outgoing edges
        if node_id in self.adjacency_list:
            del self.adjacency_list[node_id]

        # Remove incoming edges from all other nodes
        for u in self.adjacency_list:
            self.adjacency_list[u].pop(node_id, None)

        return True

    def add_edge(
        self,
        source: str,
        target: str,
        base_distance_km: Optional[float] = None,
        road_name: str = "Route",
        traffic_multiplier: float = 1.0,
        is_blocked: bool = False,
        speed_limit_kmh: float = 60.0,
        bidirectional: bool = True,
    ) -> Edge:
        """
        Add a directed or undirected edge between two existing nodes.

        If base_distance_km is not provided or <= 0, it is automatically computed
        via haversine_distance multiplied by a 1.15 road winding curvature factor.

        Args:
            source: Source node ID.
            target: Target node ID.
            base_distance_km: Base length in km (optional).
            road_name: Highway or street name.
            traffic_multiplier: Initial traffic multiplier.
            is_blocked: Initial blockage state.
            speed_limit_kmh: Speed limit in km/h.
            bidirectional: If True, adds both (source -> target) and (target -> source).

        Returns:
            The created forward Edge instance.

        Raises:
            KeyError: If either source or target node is not found in the graph.
        """
        if source not in self.nodes:
            raise KeyError(f"Source node '{source}' does not exist in graph.")
        if target not in self.nodes:
            raise KeyError(f"Target node '{target}' does not exist in graph.")

        if base_distance_km is None or base_distance_km <= 0:
            src_node = self.nodes[source]
            dst_node = self.nodes[target]
            h_dist = haversine_distance(src_node.lat, src_node.lng, dst_node.lat, dst_node.lng)
            # Apply 1.15 winding factor to account for road curvature vs straight line
            base_distance_km = round(h_dist * 1.15, 1)

        forward_edge = Edge(
            source=source,
            target=target,
            base_distance_km=base_distance_km,
            road_name=road_name,
            traffic_multiplier=traffic_multiplier,
            is_blocked=is_blocked,
            speed_limit_kmh=speed_limit_kmh,
        )

        if source not in self.adjacency_list:
            self.adjacency_list[source] = {}
        self.adjacency_list[source][target] = forward_edge

        if bidirectional:
            reverse_edge = Edge(
                source=target,
                target=source,
                base_distance_km=base_distance_km,
                road_name=road_name,
                traffic_multiplier=traffic_multiplier,
                is_blocked=is_blocked,
                speed_limit_kmh=speed_limit_kmh,
            )
            if target not in self.adjacency_list:
                self.adjacency_list[target] = {}
            self.adjacency_list[target][source] = reverse_edge

        return forward_edge

    def remove_edge(self, source: str, target: str, bidirectional: bool = True) -> bool:
        """
        Remove an edge between source and target nodes.

        Args:
            source: Source node ID.
            target: Target node ID.
            bidirectional: If True, also removes (target -> source).

        Returns:
            True if at least one edge was removed, False otherwise.
        """
        removed = False
        if source in self.adjacency_list and target in self.adjacency_list[source]:
            del self.adjacency_list[source][target]
            removed = True

        if bidirectional and target in self.adjacency_list and source in self.adjacency_list[target]:
            del self.adjacency_list[target][source]
            removed = True

        return removed

    def update_edge_traffic(
        self,
        source: str,
        target: str,
        traffic_multiplier: Optional[float] = None,
        is_blocked: Optional[bool] = None,
        bidirectional: bool = True,
    ) -> bool:
        """
        Update the traffic multiplier and/or blocked state of an existing edge.

        Args:
            source: Source node ID.
            target: Target node ID.
            traffic_multiplier: New traffic multiplier (if provided).
            is_blocked: New blocked status (if provided).
            bidirectional: If True, also updates reverse direction.

        Returns:
            True if edge was found and updated, False otherwise.
        """
        updated = False

        if source in self.adjacency_list and target in self.adjacency_list[source]:
            edge = self.adjacency_list[source][target]
            if traffic_multiplier is not None:
                edge.traffic_multiplier = max(1.0, float(traffic_multiplier))
            if is_blocked is not None:
                edge.is_blocked = bool(is_blocked)
            updated = True

        if bidirectional and target in self.adjacency_list and source in self.adjacency_list[target]:
            rev_edge = self.adjacency_list[target][source]
            if traffic_multiplier is not None:
                rev_edge.traffic_multiplier = max(1.0, float(traffic_multiplier))
            if is_blocked is not None:
                rev_edge.is_blocked = bool(is_blocked)
            updated = True

        return updated

    def get_neighbors(self, node_id: str) -> List[Edge]:
        """
        Get all outgoing edges from a given node.

        Args:
            node_id: Source node identifier.

        Returns:
            List of outgoing Edge instances.
        """
        return list(self.adjacency_list.get(node_id, {}).values())

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        """
        Retrieve edge between source and target if it exists.

        Args:
            source: Source node ID.
            target: Target node ID.

        Returns:
            Edge instance or None.
        """
        return self.adjacency_list.get(source, {}).get(target)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize graph topology and summary statistics for API response & UI rendering.

        Returns:
            Dictionary with nodes, deduplicated edges, adjacency_list, and stats.
        """
        # Node list
        node_dicts = [node.to_dict() for node in self.nodes.values()]

        # Deduplicate edges for undirected display
        processed_pairs: Set[Tuple[str, str]] = set()
        deduped_edges: List[Dict[str, Any]] = []
        blocked_count = 0
        congested_count = 0

        for u, neighbors in self.adjacency_list.items():
            for v, edge in neighbors.items():
                pair_key = tuple(sorted([u, v]))
                if pair_key in processed_pairs:
                    continue

                processed_pairs.add(pair_key)
                rev_edge = self.adjacency_list.get(v, {}).get(u)

                is_bidi = (
                    rev_edge is not None
                    and rev_edge.base_distance_km == edge.base_distance_km
                    and rev_edge.traffic_multiplier == edge.traffic_multiplier
                    and rev_edge.is_blocked == edge.is_blocked
                )

                edge_dict = edge.to_dict()
                edge_dict["bidirectional"] = is_bidi
                deduped_edges.append(edge_dict)

                if edge.is_blocked or (rev_edge and rev_edge.is_blocked):
                    blocked_count += 1
                elif edge.traffic_multiplier > 1.05 or (rev_edge and rev_edge.traffic_multiplier > 1.05):
                    congested_count += 1

        # Adjacency list representation
        adj_dict: Dict[str, List[Dict[str, Any]]] = {}
        total_degree = 0
        for u in self.nodes:
            adj_dict[u] = []
            neighbors = self.adjacency_list.get(u, {})
            total_degree += len(neighbors)
            for v, edge in neighbors.items():
                adj_dict[u].append({
                    "target": v,
                    "target_name": self.nodes[v].name if v in self.nodes else v,
                    "road_name": edge.road_name,
                    "base_distance_km": edge.base_distance_km,
                    "traffic_multiplier": edge.traffic_multiplier,
                    "is_blocked": edge.is_blocked,
                    "speed_limit_kmh": edge.speed_limit_kmh,
                    "weight": edge.effective_weight,
                    "estimated_time_min": edge.estimated_time_min,
                })

        avg_degree = round(total_degree / max(len(self.nodes), 1), 2)

        return {
            "nodes": node_dicts,
            "edges": deduped_edges,
            "adjacency_list": adj_dict,
            "stats": {
                "node_count": len(self.nodes),
                "edge_count": len(deduped_edges),
                "total_directed_edges": sum(len(adj) for adj in self.adjacency_list.values()),
                "blocked_edges": blocked_count,
                "congested_edges": congested_count,
                "avg_degree": avg_degree,
            },
        }
