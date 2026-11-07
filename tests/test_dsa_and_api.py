"""
Comprehensive Automated Test Suite for NavGraph DSA & REST API.

Covers:
1. Pure Data Structures (MinHeap, FIFOQueue, LIFOStack)
2. Geospatial Graph Engine (WeightedGraph, Haversine formula, dynamic traffic & roadblocks)
3. Algorithmic Routing (Dijkstra, A*, BFS, DFS, Multi-Stop Itineraries, Algorithm Benchmarking)
4. Full FastAPI REST API Endpoints Integration (System Health, Presets, Routing, CRUD, Traffic)
"""

import math
import pytest
from fastapi.testclient import TestClient

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
from backend.dsa.structures import FIFOQueue, LIFOStack, MinHeap
from backend.main import app, app_state


# ==============================================================================
# 1. DSA Core Structure Tests: MinHeap
# ==============================================================================

class TestMinHeap:
    """Unit tests for the custom Binary Min-Heap Priority Queue."""

    def test_min_heap_initialization(self):
        heap = MinHeap()
        assert heap.is_empty() is True
        assert len(heap) == 0
        with pytest.raises(IndexError):
            heap.pop()
        with pytest.raises(IndexError):
            heap.peek()

    def test_min_heap_push_pop_order(self):
        heap = MinHeap()
        values = [42.0, 10.5, 3.14, 99.9, 1.0, 18.2]
        for v in values:
            heap.push(v, f"item_{v}")

        assert len(heap) == len(values)
        assert heap.is_empty() is False

        # Peek should show the minimum element
        pri, item = heap.peek()
        assert pri == 1.0
        assert item == "item_1.0"

        # Pop elements in strictly ascending priority order
        popped = []
        while not heap.is_empty():
            p, it = heap.pop()
            popped.append(p)

        assert popped == sorted(values)
        assert heap.is_empty() is True

    def test_min_heap_duplicate_priorities_with_uncomparable_payloads(self):
        """Monotonic counter prevents arbitrary item comparison errors when priorities match."""
        heap = MinHeap()
        # Non-comparable dict payloads with identical priorities
        payload1 = {"name": "first", "data": [1, 2, 3]}
        payload2 = {"name": "second", "data": [4, 5, 6]}
        payload3 = {"name": "third", "data": [7, 8, 9]}

        heap.push(5.0, payload1)
        heap.push(5.0, payload2)
        heap.push(2.0, payload3)

        p1, i1 = heap.pop()
        assert p1 == 2.0
        assert i1 == payload3

        p2, i2 = heap.pop()
        assert p2 == 5.0
        assert i2 == payload1  # FIFO stability for ties

        p3, i3 = heap.pop()
        assert p3 == 5.0
        assert i3 == payload2

    def test_min_heap_to_list(self):
        heap = MinHeap()
        heap.push(10.0, "NodeA")
        heap.push(2.5, "NodeB")
        heap.push(7.8, "NodeC")

        snapshot = heap.to_list()
        assert len(snapshot) == 3
        # Should be sorted by priority
        assert snapshot[0]["priority"] == 2.5
        assert snapshot[0]["item"] == "NodeB"
        assert snapshot[1]["priority"] == 7.8
        assert snapshot[2]["priority"] == 10.0


# ==============================================================================
# 2. DSA Core Structure Tests: FIFOQueue & LIFOStack
# ==============================================================================

class TestFIFOQueue:
    """Unit tests for the pointer-linked First-In First-Out Queue."""

    def test_queue_operations(self):
        q = FIFOQueue()
        assert q.is_empty() is True
        assert len(q) == 0

        with pytest.raises(IndexError):
            q.dequeue()
        with pytest.raises(IndexError):
            q.peek()

        items = ["alpha", "beta", "gamma", "delta"]
        for it in items:
            q.enqueue(it)

        assert len(q) == 4
        assert q.peek() == "alpha"
        assert q.to_list() == items

        # Dequeue must preserve First-In First-Out ordering
        for it in items:
            assert q.dequeue() == it

        assert q.is_empty() is True
        assert len(q) == 0


class TestLIFOStack:
    """Unit tests for the pointer-linked Last-In First-Out Stack."""

    def test_stack_operations(self):
        s = LIFOStack()
        assert s.is_empty() is True
        assert len(s) == 0

        with pytest.raises(IndexError):
            s.pop()
        with pytest.raises(IndexError):
            s.peek()

        items = [10, 20, 30, 40]
        for it in items:
            s.push(it)

        assert len(s) == 4
        assert s.peek() == 40
        assert s.to_list() == [40, 30, 20, 10]

        # Pop must preserve Last-In First-Out ordering
        popped = []
        while not s.is_empty():
            popped.append(s.pop())

        assert popped == [40, 30, 20, 10]
        assert s.is_empty() is True


# ==============================================================================
# 3. Geospatial Graph Engine Tests
# ==============================================================================

class TestGeospatialGraph:
    """Unit tests for Haversine distance, WeightedGraph operations, traffic, and roadblocks."""

    def test_haversine_distance(self):
        # Known coordinates: New Delhi (28.6139, 77.2090) to Mumbai (19.0760, 72.8777)
        # Great circle geodesic distance is approximately 1148 - 1160 km
        dist = haversine_distance(28.6139, 77.2090, 19.0760, 72.8777)
        assert 1140.0 <= dist <= 1170.0

        # Self-distance should be 0.0
        assert haversine_distance(28.6139, 77.2090, 28.6139, 77.2090) == 0.0

    def test_weighted_graph_node_and_edge_crud(self):
        graph = WeightedGraph()

        # Add nodes
        n1 = Node(id="city_a", name="City A", lat=28.0, lng=77.0, category="metro")
        n2 = Node(id="city_b", name="City B", lat=29.0, lng=78.0, category="hub")
        graph.add_node(n1)
        graph.add_node(n2)

        assert "city_a" in graph.nodes
        assert "city_b" in graph.nodes
        assert len(graph.nodes) == 2

        # Add bidirectional edge with automatic Haversine distance
        edge = graph.add_edge(
            source="city_a",
            target="city_b",
            road_name="Exp-1",
            speed_limit_kmh=100.0,
            bidirectional=True,
        )
        assert edge.base_distance_km > 0
        assert graph.get_edge("city_a", "city_b") is not None
        assert graph.get_edge("city_b", "city_a") is not None

        # Traffic multiplier updates
        graph.update_edge_traffic("city_a", "city_b", traffic_multiplier=1.8, bidirectional=True)
        e_forward = graph.get_edge("city_a", "city_b")
        e_reverse = graph.get_edge("city_b", "city_a")
        assert e_forward.traffic_multiplier == 1.8
        assert e_reverse.traffic_multiplier == 1.8
        assert e_forward.effective_weight == round(edge.base_distance_km * 1.8, 2)

        # Blocked road updates
        graph.update_edge_traffic("city_a", "city_b", is_blocked=True, bidirectional=True)
        assert e_forward.is_blocked is True
        assert e_forward.effective_weight == float("inf")
        assert e_forward.estimated_time_min == float("inf")

        # Remove edge
        assert graph.remove_edge("city_a", "city_b", bidirectional=True) is True
        assert graph.get_edge("city_a", "city_b") is None
        assert graph.get_edge("city_b", "city_a") is None

        # Remove node
        assert graph.remove_node("city_a") is True
        assert "city_a" not in graph.nodes
        assert "city_a" not in graph.adjacency_list


# ==============================================================================
# 4. Pathfinding Algorithms & Optimality Tests
# ==============================================================================

class TestPathfindingAlgorithms:
    """Verification of Dijkstra, A*, BFS, DFS, and Multi-Stop route correctness."""

    @pytest.fixture(autouse=True)
    def setup_graph(self):
        self.graph = load_preset_graph("india_highways")

    def test_dijkstra_and_astar_optimality_match(self):
        """
        Verify Dijkstra and A* find the exact same optimal distance on the India Highway Network
        when weight_mode='distance' (uncongested baseline).
        """
        dijkstra_res = dijkstra(self.graph, "delhi", "bengaluru", weight_mode="distance")
        astar_res = a_star(self.graph, "delhi", "bengaluru", weight_mode="distance")

        assert dijkstra_res["found"] is True
        assert astar_res["found"] is True

        # Optimal path distances must be mathematically identical
        assert dijkstra_res["total_distance_km"] == pytest.approx(astar_res["total_distance_km"], rel=1e-3)
        assert dijkstra_res["path"][0] == "delhi"
        assert dijkstra_res["path"][-1] == "bengaluru"
        assert astar_res["path"][0] == "delhi"
        assert astar_res["path"][-1] == "bengaluru"

    def test_astar_explores_fewer_or_equal_nodes_than_dijkstra(self):
        """
        Verify that A* heuristic pruning explores fewer or equal nodes compared to uniform Dijkstra.
        """
        dijkstra_res = dijkstra(self.graph, "delhi", "bengaluru", weight_mode="effective")
        astar_res = a_star(self.graph, "delhi", "bengaluru", weight_mode="effective")

        assert astar_res["found"] is True
        assert dijkstra_res["found"] is True
        # A* should evaluate fewer or equal nodes because of directional Haversine heuristic
        assert astar_res["nodes_explored"] <= dijkstra_res["nodes_explored"]

    def test_dynamic_rerouting_around_blocked_road(self):
        """
        Verify that blocking an edge on the optimal path forces Dijkstra and A* to dynamically reroute.
        """
        # Baseline path from Delhi to Jaipur is direct NH48: ['delhi', 'jaipur']
        initial_route = dijkstra(self.graph, "delhi", "jaipur", weight_mode="effective")
        assert initial_route["found"] is True
        assert initial_route["path"] == ["delhi", "jaipur"]

        # Now simulate emergency roadblock on the Delhi-Jaipur highway segment
        self.graph.update_edge_traffic("delhi", "jaipur", is_blocked=True, bidirectional=True)

        rerouted = dijkstra(self.graph, "delhi", "jaipur", weight_mode="effective")
        assert rerouted["found"] is True
        # Path MUST NOT be direct 1-hop
        assert rerouted["path"] != ["delhi", "jaipur"]
        assert "delhi" == rerouted["path"][0]
        assert "jaipur" == rerouted["path"][-1]
        assert len(rerouted["path"]) > 2  # Must take a multi-hop detour (e.g., via Bhopal)

        # A* must also find the detour
        astar_reroute = a_star(self.graph, "delhi", "jaipur", weight_mode="effective")
        assert astar_reroute["found"] is True
        assert astar_reroute["path"] != ["delhi", "jaipur"]
        assert astar_reroute["effective_cost"] == pytest.approx(rerouted["effective_cost"], rel=1e-2)

    def test_bfs_shortest_hops(self):
        bfs_res = bfs_shortest_hops(self.graph, "delhi", "bengaluru")
        assert bfs_res["found"] is True
        assert bfs_res["path"][0] == "delhi"
        assert bfs_res["path"][-1] == "bengaluru"
        assert bfs_res["hop_count"] == len(bfs_res["path"]) - 1

    def test_dfs_path_reachability(self):
        dfs_res = dfs_path(self.graph, "delhi", "bengaluru")
        assert dfs_res["found"] is True
        assert dfs_res["path"][0] == "delhi"
        assert dfs_res["path"][-1] == "bengaluru"
        assert len(dfs_res["path"]) >= 2

    def test_multi_stop_route_chaining(self):
        waypoints = ["delhi", "jaipur", "mumbai"]
        multi_res = multi_stop_route(self.graph, waypoints, algorithm="dijkstra", weight_mode="distance")

        assert multi_res["found"] is True
        assert multi_res["waypoints"] == waypoints
        assert len(multi_res["legs"]) == 2
        assert multi_res["path"][0] == "delhi"
        assert multi_res["path"][-1] == "mumbai"
        assert "jaipur" in multi_res["path"]
        assert multi_res["total_distance_km"] > 0

    def test_compare_algorithms_benchmark(self):
        comp = compare_algorithms(self.graph, "delhi", "bengaluru", weight_mode="effective")
        assert "results" in comp
        assert "comparison_table" in comp
        assert "analysis" in comp

        assert "dijkstra" in comp["results"]
        assert "astar" in comp["results"]
        assert "bfs" in comp["results"]
        assert "dfs" in comp["results"]

        assert len(comp["comparison_table"]) == 4
        algo_keys = [row["algorithm"] for row in comp["comparison_table"]]
        assert set(algo_keys) == {"dijkstra", "astar", "bfs", "dfs"}


# ==============================================================================
# 5. FastAPI Integration Tests (via TestClient)
# ==============================================================================

class TestFastAPIEndpoints:
    """Integration tests validating REST API endpoints, schemas, and graph mutations."""

    @pytest.fixture(autouse=True)
    def client(self):
        # Reset state before each test
        app_state.reload_preset("india_highways")
        return TestClient(app)

    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "experiment_14" in data
        assert "experiment_15" in data
        assert data["active_preset"] == "india_highways"
        assert "stats" in data
        assert data["stats"]["node_count"] == 18

    def test_presets_endpoints(self, client):
        # 1. GET /api/presets
        res = client.get("/api/presets")
        assert res.status_code == 200
        data = res.json()
        preset_ids = [p["id"] for p in data["presets"]]
        assert "india_highways" in preset_ids
        assert "campus_navigator" in preset_ids

        # 2. POST /api/presets/campus_navigator/load
        load_res = client.post("/api/presets/campus_navigator/load")
        assert load_res.status_code == 200
        load_data = load_res.json()
        assert load_data["active_preset"] == "campus_navigator"
        assert load_data["graph"]["stats"]["node_count"] == 14

        # 3. POST /api/presets/invalid/load -> 404
        bad_res = client.post("/api/presets/invalid_preset/load")
        assert bad_res.status_code == 404

    def test_get_graph_endpoint(self, client):
        response = client.get("/api/graph")
        assert response.status_code == 200
        data = response.json()
        assert "graph" in data
        assert len(data["graph"]["nodes"]) == 18
        assert len(data["graph"]["edges"]) >= 20
        assert "stats" in data["graph"]

    def test_compute_route_endpoints(self, client):
        # Dijkstra route
        payload = {
            "source": "delhi",
            "target": "bengaluru",
            "algorithm": "dijkstra",
            "weight_mode": "effective",
        }
        res = client.post("/api/route", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["found"] is True
        assert data["source"] == "delhi"
        assert data["target"] == "bengaluru"
        assert len(data["path"]) > 0
        assert len(data["steps"]) > 0

        # A* route
        payload["algorithm"] = "astar"
        res_astar = client.post("/api/route", json=payload)
        assert res_astar.status_code == 200
        assert res_astar.json()["found"] is True

        # Multi-stop waypoints route
        multi_payload = {
            "waypoints": ["delhi", "jaipur", "mumbai"],
            "algorithm": "dijkstra",
            "weight_mode": "distance",
        }
        res_multi = client.post("/api/route", json=multi_payload)
        assert res_multi.status_code == 200
        data_multi = res_multi.json()
        assert data_multi["found"] is True
        assert len(data_multi["legs"]) == 2

    def test_compare_endpoint(self, client):
        payload = {"source": "delhi", "target": "bengaluru", "weight_mode": "effective"}
        res = client.post("/api/compare", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert "comparison_table" in data
        assert len(data["comparison_table"]) == 4

    def test_node_and_edge_crud_lifecycle(self, client):
        # 1. Create a new Node
        node_data = {
            "id": "agra_city",
            "name": "Agra Heritage City",
            "lat": 27.1767,
            "lng": 78.0081,
            "category": "heritage",
            "description": "City of the Taj Mahal and NH19 transit hub",
        }
        create_res = client.post("/api/node", json=node_data)
        assert create_res.status_code == 200
        assert create_res.json()["node"]["id"] == "agra_city"

        # Duplicate node error check
        dup_res = client.post("/api/node", json=node_data)
        assert dup_res.status_code == 400

        # 2. Connect new Node to Delhi via Edge
        edge_data = {
            "source": "delhi",
            "target": "agra_city",
            "road_name": "Yamuna Expressway",
            "speed_limit_kmh": 120.0,
            "bidirectional": True,
        }
        edge_res = client.post("/api/edge", json=edge_data)
        assert edge_res.status_code == 200
        edge_json = edge_res.json()["edge"]
        assert edge_json["source"] == "delhi"
        assert edge_json["target"] == "agra_city"
        assert edge_json["base_distance_km"] > 0

        # 3. Update Edge Traffic Multiplier & Blockage
        patch_res = client.patch(
            "/api/edge/traffic",
            json={
                "source": "delhi",
                "target": "agra_city",
                "traffic_multiplier": 2.2,
                "is_blocked": False,
                "bidirectional": True,
            },
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["edge"]["traffic_multiplier"] == 2.2

        # 4. Delete Edge
        del_edge_res = client.delete("/api/edge?source=delhi&target=agra_city&bidirectional=true")
        assert del_edge_res.status_code == 200

        # 5. Delete Node
        del_node_res = client.delete("/api/node/agra_city")
        assert del_node_res.status_code == 200

        # Verify node is removed
        not_found_res = client.delete("/api/node/agra_city")
        assert not_found_res.status_code == 404

    def test_traffic_simulation_and_reset(self, client):
        # 1. Simulate traffic
        sim_res = client.post(
            "/api/graph/simulate-traffic",
            json={"congestion_probability": 0.4, "block_probability": 0.1},
        )
        assert sim_res.status_code == 200
        sim_data = sim_res.json()
        assert "congested_count" in sim_data
        assert "blocked_count" in sim_data

        # 2. Reset traffic
        reset_res = client.post("/api/graph/reset-traffic")
        assert reset_res.status_code == 200
        reset_data = reset_res.json()
        assert reset_data["stats"]["blocked_edges"] == 0
