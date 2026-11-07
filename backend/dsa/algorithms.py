"""
Pathfinding & Spatial Graph Algorithms for Route Optimization.

Implements from-scratch graph traversal algorithms with step-by-step state tracking
for visualizer animation and comparative analysis:
1. Dijkstra's Algorithm (MinHeap Priority Queue, traffic-aware/distance-aware)
2. A* Search Algorithm (MinHeap Priority Queue, Haversine admissible heuristic)
3. Breadth-First Search (FIFOQueue, minimum hop count)
4. Depth-First Search (LIFOStack, structural path exploration)
5. Multi-Stop Waypoint Navigation
6. Multi-Algorithm Benchmarking and Comparison
"""

import time
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.dsa.graph import Edge, WeightedGraph, haversine_distance
from backend.dsa.structures import FIFOQueue, LIFOStack, MinHeap


def _build_route_result(
    graph: WeightedGraph,
    algorithm: str,
    algorithm_name: str,
    complexity: Dict[str, str],
    found: bool,
    source: str,
    target: str,
    weight_mode: str,
    path: List[str],
    nodes_explored: int,
    frontier_peak_size: int,
    start_time: float,
    steps: List[Dict[str, Any]],
    message: str = "",
) -> Dict[str, Any]:
    """
    Standardize the result payload across all pathfinding algorithms.
    Computes directions, geospatial coordinates, and cumulative metrics.
    """
    exec_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

    if not found or not path:
        return {
            "algorithm": algorithm,
            "algorithm_name": algorithm_name,
            "complexity": complexity,
            "found": False,
            "source": source,
            "target": target,
            "weight_mode": weight_mode,
            "path": [],
            "path_coordinates": [],
            "path_nodes": [],
            "total_distance_km": 0.0,
            "distance_km": 0.0,
            "effective_cost": 0.0,
            "total_cost": 0.0,
            "weighted_cost": 0.0,
            "estimated_time_min": 0.0,
            "hop_count": 0,
            "nodes_explored": nodes_explored,
            "frontier_peak_size": frontier_peak_size,
            "execution_time_ms": exec_time_ms,
            "directions": [],
            "steps": steps,
            "message": message or f"No viable path found between '{source}' and '{target}'.",
        }

    # Reconstruct edges and directions along the path
    path_nodes = [graph.nodes[nid].to_dict() for nid in path if nid in graph.nodes]
    path_coords = [[graph.nodes[nid].lat, graph.nodes[nid].lng] for nid in path if nid in graph.nodes]

    total_distance_km = 0.0
    effective_cost = 0.0
    weighted_cost = 0.0
    estimated_time_min = 0.0
    directions: List[Dict[str, Any]] = []

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge = graph.get_edge(u, v)

        if edge is None:
            # Fallback for virtual segment if edge is missing
            src_node = graph.nodes[u]
            dst_node = graph.nodes[v]
            dist = haversine_distance(src_node.lat, src_node.lng, dst_node.lat, dst_node.lng)
            road_name = "Direct Route"
            traffic_mult = 1.0
            eff_wt = dist
            est_time = round((dist / 60.0) * 60.0, 1)
        else:
            dist = edge.base_distance_km
            road_name = edge.road_name
            traffic_mult = edge.traffic_multiplier
            eff_wt = edge.effective_weight
            est_time = edge.estimated_time_min

        total_distance_km += dist
        effective_cost += eff_wt
        weighted_cost += dist if weight_mode == "distance" else eff_wt
        estimated_time_min += est_time

        from_name = graph.nodes[u].name if u in graph.nodes else u
        to_name = graph.nodes[v].name if v in graph.nodes else v

        directions.append({
            "step": i + 1,
            "from_id": u,
            "from_name": from_name,
            "to_id": v,
            "to_name": to_name,
            "road_name": road_name,
            "distance_km": round(dist, 1),
            "traffic_multiplier": traffic_mult,
            "effective_weight": round(eff_wt, 1),
            "estimated_time_min": round(est_time, 1),
            "instruction": f"Take {road_name} from {from_name} to {to_name} ({round(dist, 1)} km)",
        })

    return {
        "algorithm": algorithm,
        "algorithm_name": algorithm_name,
        "complexity": complexity,
        "found": True,
        "source": source,
        "target": target,
        "weight_mode": weight_mode,
        "path": path,
        "path_coordinates": path_coords,
        "path_nodes": path_nodes,
        "total_distance_km": round(total_distance_km, 2),
        "distance_km": round(total_distance_km, 2),
        "effective_cost": round(effective_cost, 2),
        "total_cost": round(effective_cost, 2),
        "weighted_cost": round(weighted_cost, 2),
        "estimated_time_min": round(estimated_time_min, 1),
        "hop_count": max(0, len(path) - 1),
        "nodes_explored": nodes_explored,
        "frontier_peak_size": frontier_peak_size,
        "execution_time_ms": exec_time_ms,
        "directions": directions,
        "steps": steps,
        "message": message or f"Optimal path found with {len(path) - 1} hops ({round(total_distance_km, 1)} km).",
    }


def dijkstra(
    graph: WeightedGraph,
    start_id: str,
    end_id: str,
    weight_mode: str = "effective",
) -> Dict[str, Any]:
    """
    Dijkstra's Shortest Path Algorithm using from-scratch MinHeap.

    Explores vertices in increasing order of cumulative distance/weight from source.
    Guarantees mathematically optimal shortest path on graphs with non-negative edge weights.

    Complexity:
        Time:  O((V + E) log V)
        Space: O(V)
    """
    start_time = time.perf_counter()
    complexity = {"time": "O((V + E) log V)", "space": "O(V)"}
    algo_name = "Dijkstra's Shortest Path (Min-Heap PQ)"

    # Validate endpoints
    if start_id not in graph.nodes or end_id not in graph.nodes:
        return _build_route_result(
            graph=graph,
            algorithm="dijkstra",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=0,
            frontier_peak_size=0,
            start_time=start_time,
            steps=[],
            message=f"Source '{start_id}' or Destination '{end_id}' does not exist.",
        )

    if start_id == end_id:
        return _build_route_result(
            graph=graph,
            algorithm="dijkstra",
            algorithm_name=algo_name,
            complexity=complexity,
            found=True,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[start_id],
            nodes_explored=1,
            frontier_peak_size=1,
            start_time=start_time,
            steps=[],
            message="Source and Destination are identical.",
        )

    heap = MinHeap()
    dist: Dict[str, float] = {start_id: 0.0}
    prev: Dict[str, Optional[str]] = {start_id: None}
    visited: Set[str] = set()
    steps: List[Dict[str, Any]] = []

    heap.push(0.0, start_id)
    frontier_peak = 1
    step_num = 0

    while not heap.is_empty():
        frontier_peak = max(frontier_peak, len(heap))
        current_dist, u = heap.pop()

        if u in visited:
            continue
        visited.add(u)

        u_name = graph.nodes[u].name if u in graph.nodes else u
        explored_edges: List[List[str]] = []

        # Check for destination reached
        if u == end_id:
            step_num += 1
            steps.append({
                "step_number": step_num,
                "action": "reached_target",
                "current_node": u,
                "current_node_name": u_name,
                "visited_nodes": list(visited),
                "explored_edges": explored_edges,
                "frontier": heap.to_list(),
                "distances": {k: round(v, 1) for k, v in dist.items()},
                "message": f"Target '{u_name}' reached with cumulative cost {round(current_dist, 2)}.",
            })
            break

        # Relax incident edges
        outgoing_edges = graph.get_neighbors(u)
        relaxed_count = 0

        for edge in outgoing_edges:
            # Blocked roads are strictly impassable
            if edge.is_blocked:
                continue

            v = edge.target
            if v in visited:
                continue

            weight = edge.effective_weight if weight_mode == "effective" else edge.base_distance_km
            new_cost = current_dist + weight
            explored_edges.append([u, v])

            if v not in dist or new_cost < dist[v]:
                dist[v] = round(new_cost, 2)
                prev[v] = u
                heap.push(dist[v], v)
                relaxed_count += 1

        step_num += 1
        steps.append({
            "step_number": step_num,
            "action": "visit",
            "current_node": u,
            "current_node_name": u_name,
            "visited_nodes": list(visited),
            "explored_edges": explored_edges,
            "frontier": heap.to_list(),
            "distances": {k: round(v, 1) for k, v in dist.items()},
            "message": f"Popped {u_name} (cost {round(current_dist, 1)}); evaluated {len(outgoing_edges)} roads, relaxed {relaxed_count} neighbors.",
        })

    # Reconstruct path if target was reached
    if end_id not in visited:
        return _build_route_result(
            graph=graph,
            algorithm="dijkstra",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=len(visited),
            frontier_peak_size=frontier_peak,
            start_time=start_time,
            steps=steps,
            message=f"No viable road route connects '{start_id}' to '{end_id}'.",
        )

    # Backtrack path
    path = []
    curr: Optional[str] = end_id
    while curr is not None:
        path.append(curr)
        curr = prev.get(curr)
    path.reverse()

    return _build_route_result(
        graph=graph,
        algorithm="dijkstra",
        algorithm_name=algo_name,
        complexity=complexity,
        found=True,
        source=start_id,
        target=end_id,
        weight_mode=weight_mode,
        path=path,
        nodes_explored=len(visited),
        frontier_peak_size=frontier_peak,
        start_time=start_time,
        steps=steps,
    )


def a_star(
    graph: WeightedGraph,
    start_id: str,
    end_id: str,
    weight_mode: str = "effective",
) -> Dict[str, Any]:
    """
    A* Heuristic Search Algorithm using from-scratch MinHeap.

    Guides exploration towards the destination using the Haversine spherical distance
    as an admissible and consistent heuristic: h(n) <= true remaining road distance.
    f(n) = g(n) + h(n), where g(n) is actual cost so far.

    Complexity:
        Time:  O((V + E) log V) worst-case; significantly fewer nodes explored in practice.
        Space: O(V)
    """
    start_time = time.perf_counter()
    complexity = {"time": "O((V + E) log V)", "space": "O(V)"}
    algo_name = "A* Heuristic Search (Haversine Euclidean h(n))"

    if start_id not in graph.nodes or end_id not in graph.nodes:
        return _build_route_result(
            graph=graph,
            algorithm="astar",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=0,
            frontier_peak_size=0,
            start_time=start_time,
            steps=[],
            message=f"Source '{start_id}' or Destination '{end_id}' does not exist.",
        )

    if start_id == end_id:
        return _build_route_result(
            graph=graph,
            algorithm="astar",
            algorithm_name=algo_name,
            complexity=complexity,
            found=True,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[start_id],
            nodes_explored=1,
            frontier_peak_size=1,
            start_time=start_time,
            steps=[],
            message="Source and Destination are identical.",
        )

    target_node = graph.nodes[end_id]

    def heuristic(node_id: str) -> float:
        n = graph.nodes.get(node_id)
        if not n:
            return 0.0
        return haversine_distance(n.lat, n.lng, target_node.lat, target_node.lng)

    heap = MinHeap()
    g_score: Dict[str, float] = {start_id: 0.0}
    f_score: Dict[str, float] = {start_id: round(heuristic(start_id), 2)}
    prev: Dict[str, Optional[str]] = {start_id: None}
    visited: Set[str] = set()
    steps: List[Dict[str, Any]] = []

    heap.push(f_score[start_id], start_id)
    frontier_peak = 1
    step_num = 0

    while not heap.is_empty():
        frontier_peak = max(frontier_peak, len(heap))
        curr_f, u = heap.pop()

        if u in visited:
            continue
        visited.add(u)

        u_name = graph.nodes[u].name if u in graph.nodes else u
        explored_edges: List[List[str]] = []

        if u == end_id:
            step_num += 1
            steps.append({
                "step_number": step_num,
                "action": "reached_target",
                "current_node": u,
                "current_node_name": u_name,
                "visited_nodes": list(visited),
                "explored_edges": explored_edges,
                "frontier": heap.to_list(),
                "distances": {k: round(v, 1) for k, v in g_score.items()},
                "message": f"Target '{u_name}' reached with optimal cost {round(g_score[u], 2)}.",
            })
            break

        outgoing_edges = graph.get_neighbors(u)
        relaxed_count = 0

        for edge in outgoing_edges:
            if edge.is_blocked:
                continue

            v = edge.target
            if v in visited:
                continue

            weight = edge.effective_weight if weight_mode == "effective" else edge.base_distance_km
            tentative_g = g_score[u] + weight
            explored_edges.append([u, v])

            if v not in g_score or tentative_g < g_score[v]:
                g_score[v] = round(tentative_g, 2)
                h_val = round(heuristic(v), 2)
                f_val = round(g_score[v] + h_val, 2)
                f_score[v] = f_val
                prev[v] = u
                heap.push(f_val, v)
                relaxed_count += 1

        step_num += 1
        steps.append({
            "step_number": step_num,
            "action": "visit",
            "current_node": u,
            "current_node_name": u_name,
            "visited_nodes": list(visited),
            "explored_edges": explored_edges,
            "frontier": heap.to_list(),
            "distances": {k: round(v, 1) for k, v in g_score.items()},
            "message": f"Popped {u_name} (f={curr_f}, g={round(g_score[u], 1)}, h={round(heuristic(u), 1)}); relaxed {relaxed_count} neighbors.",
        })

    if end_id not in visited:
        return _build_route_result(
            graph=graph,
            algorithm="astar",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=len(visited),
            frontier_peak_size=frontier_peak,
            start_time=start_time,
            steps=steps,
            message=f"No viable road route connects '{start_id}' to '{end_id}'.",
        )

    # Reconstruct path
    path = []
    curr = end_id
    while curr is not None:
        path.append(curr)
        curr = prev.get(curr)
    path.reverse()

    return _build_route_result(
        graph=graph,
        algorithm="astar",
        algorithm_name=algo_name,
        complexity=complexity,
        found=True,
        source=start_id,
        target=end_id,
        weight_mode=weight_mode,
        path=path,
        nodes_explored=len(visited),
        frontier_peak_size=frontier_peak,
        start_time=start_time,
        steps=steps,
    )


def bfs_shortest_hops(
    graph: WeightedGraph,
    start_id: str,
    end_id: str,
    weight_mode: str = "effective",
) -> Dict[str, Any]:
    """
    Breadth-First Search (BFS) using from-scratch pointer FIFOQueue.

    Finds the route with the fewest road segments / hops regardless of physical length.
    Demonstrates unweighted topological shortest-path logic.

    Complexity:
        Time:  O(V + E)
        Space: O(V)
    """
    start_time = time.perf_counter()
    complexity = {"time": "O(V + E)", "space": "O(V)"}
    algo_name = "Breadth-First Search (Fewest Hops Queue)"

    if start_id not in graph.nodes or end_id not in graph.nodes:
        return _build_route_result(
            graph=graph,
            algorithm="bfs",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=0,
            frontier_peak_size=0,
            start_time=start_time,
            steps=[],
            message=f"Source '{start_id}' or Destination '{end_id}' does not exist.",
        )

    if start_id == end_id:
        return _build_route_result(
            graph=graph,
            algorithm="bfs",
            algorithm_name=algo_name,
            complexity=complexity,
            found=True,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[start_id],
            nodes_explored=1,
            frontier_peak_size=1,
            start_time=start_time,
            steps=[],
            message="Source and Destination are identical.",
        )

    queue = FIFOQueue()
    queue.enqueue(start_id)

    visited: Set[str] = {start_id}
    prev: Dict[str, Optional[str]] = {start_id: None}
    hops: Dict[str, int] = {start_id: 0}
    steps: List[Dict[str, Any]] = []

    frontier_peak = 1
    step_num = 0
    target_found = False

    while not queue.is_empty():
        frontier_peak = max(frontier_peak, len(queue))
        u = queue.dequeue()
        u_name = graph.nodes[u].name if u in graph.nodes else u
        explored_edges: List[List[str]] = []

        if u == end_id:
            target_found = True
            step_num += 1
            steps.append({
                "step_number": step_num,
                "action": "reached_target",
                "current_node": u,
                "current_node_name": u_name,
                "visited_nodes": list(visited),
                "explored_edges": explored_edges,
                "frontier": queue.to_list(),
                "distances": dict(hops),
                "message": f"Target '{u_name}' reached in {hops[u]} hops.",
            })
            break

        outgoing_edges = graph.get_neighbors(u)
        enqueued_count = 0

        for edge in outgoing_edges:
            if edge.is_blocked:
                continue

            v = edge.target
            explored_edges.append([u, v])

            if v not in visited:
                visited.add(v)
                prev[v] = u
                hops[v] = hops[u] + 1
                queue.enqueue(v)
                enqueued_count += 1

                if v == end_id:
                    # Target discovered in BFS frontier
                    target_found = True
                    break

        step_num += 1
        steps.append({
            "step_number": step_num,
            "action": "visit",
            "current_node": u,
            "current_node_name": u_name,
            "visited_nodes": list(visited),
            "explored_edges": explored_edges,
            "frontier": queue.to_list(),
            "distances": dict(hops),
            "message": f"Dequeued {u_name} (hop level {hops[u]}); enqueued {enqueued_count} unvisited neighbors.",
        })

        if target_found:
            break

    if not target_found or end_id not in prev:
        return _build_route_result(
            graph=graph,
            algorithm="bfs",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=len(visited),
            frontier_peak_size=frontier_peak,
            start_time=start_time,
            steps=steps,
            message=f"No viable road route connects '{start_id}' to '{end_id}'.",
        )

    # Reconstruct path
    path = []
    curr = end_id
    while curr is not None:
        path.append(curr)
        curr = prev.get(curr)
    path.reverse()

    return _build_route_result(
        graph=graph,
        algorithm="bfs",
        algorithm_name=algo_name,
        complexity=complexity,
        found=True,
        source=start_id,
        target=end_id,
        weight_mode=weight_mode,
        path=path,
        nodes_explored=len(visited),
        frontier_peak_size=frontier_peak,
        start_time=start_time,
        steps=steps,
    )


def dfs_path(
    graph: WeightedGraph,
    start_id: str,
    end_id: str,
    weight_mode: str = "effective",
) -> Dict[str, Any]:
    """
    Depth-First Search (DFS) using from-scratch pointer LIFOStack.

    Explores deep paths into the network before backtracking. Demonstrates
    non-optimal topological reachability and stack-based recursion simulation.

    Complexity:
        Time:  O(V + E)
        Space: O(V)
    """
    start_time = time.perf_counter()
    complexity = {"time": "O(V + E)", "space": "O(V)"}
    algo_name = "Depth-First Search (LIFO Stack)"

    if start_id not in graph.nodes or end_id not in graph.nodes:
        return _build_route_result(
            graph=graph,
            algorithm="dfs",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=0,
            frontier_peak_size=0,
            start_time=start_time,
            steps=[],
            message=f"Source '{start_id}' or Destination '{end_id}' does not exist.",
        )

    if start_id == end_id:
        return _build_route_result(
            graph=graph,
            algorithm="dfs",
            algorithm_name=algo_name,
            complexity=complexity,
            found=True,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[start_id],
            nodes_explored=1,
            frontier_peak_size=1,
            start_time=start_time,
            steps=[],
            message="Source and Destination are identical.",
        )

    # Stack entries are (node, parent) so a node's parent is fixed when it is
    # actually visited, giving the true DFS tree path rather than the first discoverer.
    stack = LIFOStack()
    stack.push((start_id, None))

    visited: Set[str] = set()
    prev: Dict[str, Optional[str]] = {}
    depth: Dict[str, int] = {}
    steps: List[Dict[str, Any]] = []

    frontier_peak = 1
    step_num = 0
    target_found = False

    def frontier_ids() -> List[str]:
        return [n for n, _ in stack.to_list()]

    while not stack.is_empty():
        frontier_peak = max(frontier_peak, len(stack))
        u, parent = stack.pop()

        if u in visited:
            continue
        visited.add(u)
        prev[u] = parent
        depth[u] = 0 if parent is None else depth[parent] + 1

        u_name = graph.nodes[u].name if u in graph.nodes else u
        explored_edges: List[List[str]] = []

        if u == end_id:
            target_found = True
            step_num += 1
            steps.append({
                "step_number": step_num,
                "action": "reached_target",
                "current_node": u,
                "current_node_name": u_name,
                "visited_nodes": list(visited),
                "explored_edges": explored_edges,
                "frontier": frontier_ids(),
                "distances": dict(depth),
                "message": f"Target '{u_name}' found via DFS traversal at depth {depth[u]}.",
            })
            break

        outgoing_edges = graph.get_neighbors(u)
        pushed_count = 0

        for edge in outgoing_edges:
            if edge.is_blocked:
                continue

            v = edge.target
            explored_edges.append([u, v])

            if v not in visited:
                stack.push((v, u))
                pushed_count += 1

        step_num += 1
        steps.append({
            "step_number": step_num,
            "action": "visit",
            "current_node": u,
            "current_node_name": u_name,
            "visited_nodes": list(visited),
            "explored_edges": explored_edges,
            "frontier": frontier_ids(),
            "distances": dict(depth),
            "message": f"Popped {u_name} from stack (depth {depth[u]}); pushed {pushed_count} unexplored branches.",
        })

    if not target_found or end_id not in prev:
        return _build_route_result(
            graph=graph,
            algorithm="dfs",
            algorithm_name=algo_name,
            complexity=complexity,
            found=False,
            source=start_id,
            target=end_id,
            weight_mode=weight_mode,
            path=[],
            nodes_explored=len(visited),
            frontier_peak_size=frontier_peak,
            start_time=start_time,
            steps=steps,
            message=f"No viable road route connects '{start_id}' to '{end_id}'.",
        )

    # Reconstruct path
    path = []
    curr = end_id
    while curr is not None:
        path.append(curr)
        curr = prev.get(curr)
    path.reverse()

    return _build_route_result(
        graph=graph,
        algorithm="dfs",
        algorithm_name=algo_name,
        complexity=complexity,
        found=True,
        source=start_id,
        target=end_id,
        weight_mode=weight_mode,
        path=path,
        nodes_explored=len(visited),
        frontier_peak_size=frontier_peak,
        start_time=start_time,
        steps=steps,
    )


def multi_stop_route(
    graph: WeightedGraph,
    waypoints: List[str],
    algorithm: str = "dijkstra",
    weight_mode: str = "effective",
) -> Dict[str, Any]:
    """
    Compute multi-waypoint transit itineraries by stitching consecutive leg computations.

    Args:
        graph: Loaded WeightedGraph instance.
        waypoints: Ordered list of node IDs to visit, e.g. ['delhi', 'jaipur', 'mumbai'].
        algorithm: Pathfinding algorithm to execute ('dijkstra', 'astar', 'bfs', 'dfs').
        weight_mode: Traversal optimization criterion ('effective' or 'distance').

    Returns:
        Consolidated route result dictionary containing all stitched legs and cumulative totals.
    """
    algo_runners = {
        "dijkstra": dijkstra,
        "astar": a_star,
        "bfs": bfs_shortest_hops,
        "dfs": dfs_path,
    }

    runner = algo_runners.get(algorithm.lower(), dijkstra)
    start_time = time.perf_counter()

    if not waypoints or len(waypoints) < 2:
        return {
            "algorithm": algorithm,
            "algorithm_name": f"Multi-Stop Itinerary ({algorithm.upper()})",
            "complexity": {"time": "O(K * (V + E) log V)", "space": "O(V)"},
            "found": False,
            "waypoints": waypoints,
            "legs": [],
            "source": waypoints[0] if waypoints else "",
            "target": waypoints[-1] if waypoints else "",
            "weight_mode": weight_mode,
            "path": [],
            "path_coordinates": [],
            "path_nodes": [],
            "total_distance_km": 0.0,
            "distance_km": 0.0,
            "effective_cost": 0.0,
            "total_cost": 0.0,
            "weighted_cost": 0.0,
            "estimated_time_min": 0.0,
            "hop_count": 0,
            "nodes_explored": 0,
            "frontier_peak_size": 0,
            "execution_time_ms": 0.0,
            "directions": [],
            "steps": [],
            "message": "At least 2 waypoints are required to construct an itinerary.",
        }

    combined_path: List[str] = []
    legs: List[Dict[str, Any]] = []
    combined_directions: List[Dict[str, Any]] = []
    combined_steps: List[Dict[str, Any]] = []

    total_distance_km = 0.0
    effective_cost = 0.0
    weighted_cost = 0.0
    estimated_time_min = 0.0
    total_explored = 0
    max_peak = 0
    step_offset = 0

    for i in range(len(waypoints) - 1):
        src = waypoints[i]
        dst = waypoints[i + 1]

        leg_res = runner(graph, src, dst, weight_mode=weight_mode)
        legs.append(leg_res)

        if not leg_res["found"]:
            return {
                "algorithm": algorithm,
                "algorithm_name": f"Multi-Stop Itinerary ({algorithm.upper()})",
                "complexity": {"time": "O(K * (V + E) log V)", "space": "O(V)"},
                "found": False,
                "waypoints": waypoints,
                "failed_leg": {"from": src, "to": dst, "leg_index": i + 1},
                "legs": legs,
                "source": waypoints[0],
                "target": waypoints[-1],
                "weight_mode": weight_mode,
                "path": [],
                "path_coordinates": [],
                "path_nodes": [],
                "total_distance_km": 0.0,
                "distance_km": 0.0,
                "effective_cost": 0.0,
                "total_cost": 0.0,
                "weighted_cost": 0.0,
                "estimated_time_min": 0.0,
                "hop_count": 0,
                "nodes_explored": total_explored + leg_res.get("nodes_explored", 0),
                "frontier_peak_size": max(max_peak, leg_res.get("frontier_peak_size", 0)),
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000.0, 3),
                "directions": [],
                "steps": combined_steps,
                "message": f"Route segment from '{src}' to '{dst}' failed: {leg_res.get('message')}",
            }

        # Stitch path (avoid duplicating junction node)
        leg_path = leg_res["path"]
        if not combined_path:
            combined_path.extend(leg_path)
        else:
            combined_path.extend(leg_path[1:])

        # Accumulate metrics
        total_distance_km += leg_res["total_distance_km"]
        effective_cost += leg_res["effective_cost"]
        weighted_cost += leg_res["weighted_cost"]
        estimated_time_min += leg_res["estimated_time_min"]
        total_explored += leg_res["nodes_explored"]
        max_peak = max(max_peak, leg_res["frontier_peak_size"])

        # Re-index directions
        dir_offset = len(combined_directions)
        for d in leg_res["directions"]:
            d_copy = dict(d)
            d_copy["step"] = dir_offset + d["step"]
            combined_directions.append(d_copy)

        # Re-index steps
        for st in leg_res["steps"]:
            st_copy = dict(st)
            step_offset += 1
            st_copy["step_number"] = step_offset
            combined_steps.append(st_copy)

    path_nodes = [graph.nodes[nid].to_dict() for nid in combined_path if nid in graph.nodes]
    path_coords = [[graph.nodes[nid].lat, graph.nodes[nid].lng] for nid in combined_path if nid in graph.nodes]

    return {
        "algorithm": algorithm,
        "algorithm_name": f"Multi-Stop Itinerary ({len(waypoints)} Waypoints)",
        "complexity": {"time": f"O({len(waypoints)-1} * (V + E) log V)", "space": "O(V)"},
        "found": True,
        "waypoints": waypoints,
        "legs": legs,
        "source": waypoints[0],
        "target": waypoints[-1],
        "weight_mode": weight_mode,
        "path": combined_path,
        "path_coordinates": path_coords,
        "path_nodes": path_nodes,
        "total_distance_km": round(total_distance_km, 2),
        "distance_km": round(total_distance_km, 2),
        "effective_cost": round(effective_cost, 2),
        "total_cost": round(effective_cost, 2),
        "weighted_cost": round(weighted_cost, 2),
        "estimated_time_min": round(estimated_time_min, 1),
        "hop_count": max(0, len(combined_path) - 1),
        "nodes_explored": total_explored,
        "frontier_peak_size": max_peak,
        "execution_time_ms": round((time.perf_counter() - start_time) * 1000.0, 3),
        "directions": combined_directions,
        "steps": combined_steps,
        "message": f"Successfully planned complete {len(waypoints)}-waypoint itinerary across {len(legs)} segments.",
    }


def compare_algorithms(
    graph: WeightedGraph,
    start_id: str,
    end_id: str,
    weight_mode: str = "effective",
) -> Dict[str, Any]:
    """
    Run all 4 pathfinding algorithms against the same graph instance and query endpoints.
    Produces a side-by-side benchmark matrix and pedagogical DSA comparative analysis.

    Returns:
        Structured dictionary with source, target, individual algo outputs, comparison table, and insights.
    """
    algos = [
        ("dijkstra", "Dijkstra's Shortest Path", dijkstra),
        ("astar", "A* Heuristic Search", a_star),
        ("bfs", "Breadth-First Search", bfs_shortest_hops),
        ("dfs", "Depth-First Search", dfs_path),
    ]

    results: Dict[str, Any] = {}
    for key, _, func in algos:
        results[key] = func(graph, start_id, end_id, weight_mode=weight_mode)

    # Optimality is judged on the metric being optimised: traffic-adjusted cost in
    # "effective" mode, physical km in "distance" mode.
    valid_costs = [res["weighted_cost"] for res in results.values() if res["found"]]
    min_cost = min(valid_costs) if valid_costs else None

    comparison_table: List[Dict[str, Any]] = []
    for key, name, _ in algos:
        res = results[key]
        is_opt = (
            res["found"] and min_cost is not None and abs(res["weighted_cost"] - min_cost) <= 0.011
        )
        path_names = [graph.nodes[n].name for n in res["path"] if n in graph.nodes]

        comparison_table.append({
            "algorithm": key,
            "algorithm_name": name,
            "found": res["found"],
            "path": res["path"],
            "path_names": path_names,
            "total_distance_km": res["total_distance_km"],
            "effective_cost": res["effective_cost"],
            "weighted_cost": res["weighted_cost"],
            "estimated_time_min": res["estimated_time_min"],
            "hop_count": res["hop_count"],
            "nodes_explored": res["nodes_explored"],
            "frontier_peak_size": res["frontier_peak_size"],
            "execution_time_ms": res["execution_time_ms"],
            "complexity_time": res["complexity"]["time"],
            "complexity_space": res["complexity"]["space"],
            "is_optimal_cost": is_opt,
        })

    # Generate analytical insights
    analysis_points: List[str] = []

    dijkstra_res = results["dijkstra"]
    astar_res = results["astar"]
    bfs_res = results["bfs"]
    dfs_res = results["dfs"]

    if dijkstra_res["found"] and astar_res["found"]:
        d_exp = dijkstra_res["nodes_explored"]
        a_exp = astar_res["nodes_explored"]
        if d_exp > 0:
            reduction = round(((d_exp - a_exp) / d_exp) * 100.0, 1)
            if reduction > 0:
                analysis_points.append(
                    f"A* explored {reduction}% fewer nodes than Dijkstra ({a_exp} vs {d_exp}) "
                    f"due to Haversine heuristic pruning toward destination coordinates."
                )
            elif reduction == 0:
                analysis_points.append(
                    f"A* and Dijkstra explored an equal number of nodes ({a_exp}) on this topology."
                )
            else:
                analysis_points.append(
                    f"A* explored {a_exp} nodes compared to {d_exp} by Dijkstra."
                )

        if abs(astar_res["weighted_cost"] - dijkstra_res["weighted_cost"]) <= 0.011:
            analysis_points.append(
                "A* matched Dijkstra's optimal cost, as expected from an admissible heuristic: "
                "straight-line distance never exceeds the road distance remaining."
            )
        else:
            analysis_points.append(
                f"A* cost ({astar_res['weighted_cost']}) differs from Dijkstra's optimum "
                f"({dijkstra_res['weighted_cost']}); the heuristic overestimated on this graph."
            )

    if bfs_res["found"] and dijkstra_res["found"]:
        b_hops = bfs_res["hop_count"]
        d_hops = dijkstra_res["hop_count"]
        if b_hops < d_hops:
            analysis_points.append(
                f"BFS discovered a path with fewer hops ({b_hops} vs {d_hops}), but Dijkstra's route has the lower "
                f"{'distance' if weight_mode == 'distance' else 'traffic-weighted cost'} "
                f"({dijkstra_res['weighted_cost']} vs {bfs_res['weighted_cost']})."
            )
        else:
            analysis_points.append(
                f"BFS and Dijkstra matched hop count ({b_hops} hops) for this corridor."
            )

    if dfs_res["found"]:
        analysis_points.append(
            f"DFS constructed an unweighted exploratory path ({dfs_res['hop_count']} hops, cost {dfs_res['weighted_cost']}). "
            f"Unlike Dijkstra or BFS, DFS does not guarantee optimality but exhibits minimal memory overhead."
        )

    return {
        "source": start_id,
        "target": end_id,
        "weight_mode": weight_mode,
        "results": results,
        "comparison_table": comparison_table,
        "analysis": analysis_points,
    }
