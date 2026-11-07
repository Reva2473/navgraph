"""
Integration & Unit Test Suite for FastAPI Backend (Experiment 14 & 15)
Covers all endpoints, algorithms, topology CRUD, and traffic simulations.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app, app_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_to_default_preset():
    """Ensure every test runs on a fresh 'india_highways' graph."""
    app_state.reload_preset("india_highways")
    yield
    app_state.reload_preset("india_highways")


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["experiment_14"] == "Map Navigator API Active"
    assert data["experiment_15"] == "Frontend Integration Ready"
    assert data["active_preset"] == "india_highways"
    assert data["stats"]["node_count"] == 18


def test_presets_endpoints():
    # 1. Get presets catalog
    res = client.get("/api/presets")
    assert res.status_code == 200
    catalog = res.json()
    assert "india_highways" in catalog["presets_map"]
    assert "campus_navigator" in catalog["presets_map"]

    # 2. Switch to campus_navigator
    res_load = client.post("/api/presets/campus_navigator/load")
    assert res_load.status_code == 200
    loaded_data = res_load.json()
    assert loaded_data["active_preset"] == "campus_navigator"
    assert loaded_data["graph"]["stats"]["node_count"] == 14

    # 3. Invalid preset 404
    res_invalid = client.post("/api/presets/non_existent_preset/load")
    assert res_invalid.status_code == 404


def test_get_graph_endpoint():
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert data["active_preset"] == "india_highways"
    assert len(data["graph"]["nodes"]) == 18
    assert len(data["graph"]["edges"]) > 0
    assert "delhi" in data["graph"]["adjacency_list"]


def test_route_dijkstra_and_astar():
    # Dijkstra
    res_dijkstra = client.post(
        "/api/route",
        json={
            "source": "delhi",
            "target": "bengaluru",
            "algorithm": "dijkstra",
            "weight_mode": "effective",
        },
    )
    assert res_dijkstra.status_code == 200
    data_d = res_dijkstra.json()
    assert data_d["found"] is True
    assert data_d["path"][0] == "delhi"
    assert data_d["path"][-1] == "bengaluru"
    assert data_d["total_distance_km"] > 0
    assert len(data_d["directions"]) > 0

    # A*
    res_astar = client.post(
        "/api/route",
        json={
            "source": "delhi",
            "target": "bengaluru",
            "algorithm": "astar",
            "weight_mode": "distance",
        },
    )
    assert res_astar.status_code == 200
    data_a = res_astar.json()
    assert data_a["found"] is True
    assert data_a["path"][0] == "delhi"
    assert data_a["path"][-1] == "bengaluru"


def test_route_bfs_and_dfs():
    # BFS
    res_bfs = client.post(
        "/api/route",
        json={
            "source": "delhi",
            "target": "mumbai",
            "algorithm": "bfs",
        },
    )
    assert res_bfs.status_code == 200
    data_bfs = res_bfs.json()
    assert data_bfs["found"] is True
    assert data_bfs["path"][0] == "delhi"
    assert data_bfs["path"][-1] == "mumbai"

    # DFS
    res_dfs = client.post(
        "/api/route",
        json={
            "source": "delhi",
            "target": "mumbai",
            "algorithm": "dfs",
        },
    )
    assert res_dfs.status_code == 200
    data_dfs = res_dfs.json()
    assert data_dfs["found"] is True
    assert data_dfs["path"][0] == "delhi"
    assert data_dfs["path"][-1] == "mumbai"


def test_route_multi_stop_waypoints():
    res = client.post(
        "/api/route",
        json={
            "waypoints": ["delhi", "jaipur", "bhopal", "nagpur", "hyderabad", "bengaluru"],
            "algorithm": "dijkstra",
            "weight_mode": "effective",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["path"][0] == "delhi"
    assert data["path"][-1] == "bengaluru"
    for wp in ["jaipur", "bhopal", "nagpur", "hyderabad"]:
        assert wp in data["path"]


def test_route_error_handling():
    # Unknown node -> 404
    res_missing = client.post(
        "/api/route",
        json={"source": "delhi", "target": "atlantis", "algorithm": "dijkstra"},
    )
    assert res_missing.status_code == 404

    # Unsupported algorithm -> 400
    res_algo = client.post(
        "/api/route",
        json={"source": "delhi", "target": "mumbai", "algorithm": "quantum_leap"},
    )
    assert res_algo.status_code == 400

    # Insufficient nodes -> 400
    res_few = client.post(
        "/api/route",
        json={"source": "delhi", "algorithm": "dijkstra"},
    )
    assert res_few.status_code == 400


def test_benchmark_compare_endpoint():
    res = client.post(
        "/api/compare",
        json={"source": "delhi", "target": "kolkata", "weight_mode": "effective"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert "dijkstra" in data["results"]
    assert "astar" in data["results"]
    assert "bfs" in data["results"]
    assert "dfs" in data["results"]
    assert "comparison_table" in data
    assert len(data["comparison_table"]) == 4
    assert "analysis" in data


def test_node_crud():
    # 1. Add node
    res_add = client.post(
        "/api/node",
        json={
            "name": "Varanasi",
            "lat": 25.3176,
            "lng": 82.9739,
            "category": "spiritual_hub",
            "description": "Ancient cultural city along the Ganga",
        },
    )
    assert res_add.status_code == 200
    added_node = res_add.json()["node"]
    assert added_node["name"] == "Varanasi"
    node_id = added_node["id"]
    assert node_id in app_state.graph.nodes

    # 2. Prevent duplicate ID
    res_dup = client.post(
        "/api/node",
        json={"id": node_id, "name": "Varanasi Duplicate", "lat": 25.3, "lng": 82.9},
    )
    assert res_dup.status_code == 400

    # 3. Delete node
    res_del = client.delete(f"/api/node/{node_id}")
    assert res_del.status_code == 200
    assert node_id not in app_state.graph.nodes

    # 4. Delete non-existent node -> 404
    res_del_404 = client.delete(f"/api/node/{node_id}")
    assert res_del_404.status_code == 404


def test_edge_crud():
    # 1. Add edge with auto-calculated Haversine distance
    res_add = client.post(
        "/api/edge",
        json={
            "source": "chandigarh",
            "target": "jaipur",
            "road_name": "Trans-Haryana Expy",
            "traffic_multiplier": 1.05,
            "bidirectional": True,
        },
    )
    assert res_add.status_code == 200
    edge_data = res_add.json()["edge"]
    assert edge_data["source"] == "chandigarh"
    assert edge_data["target"] == "jaipur"
    assert edge_data["base_distance_km"] > 0

    # 2. Self-loop prevention -> 400
    res_loop = client.post(
        "/api/edge",
        json={"source": "delhi", "target": "delhi"},
    )
    assert res_loop.status_code == 400

    # 3. Delete edge
    res_del = client.delete("/api/edge?source=chandigarh&target=jaipur&bidirectional=true")
    assert res_del.status_code == 200

    # 4. Delete non-existent edge -> 404
    res_del_404 = client.delete("/api/edge?source=chandigarh&target=jaipur")
    assert res_del_404.status_code == 404


def test_traffic_controls():
    # 1. Patch traffic condition
    res_patch = client.patch(
        "/api/edge/traffic",
        json={
            "source": "delhi",
            "target": "jaipur",
            "traffic_multiplier": 2.2,
            "is_blocked": False,
            "bidirectional": True,
        },
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["edge"]["traffic_multiplier"] == 2.2

    # 2. Simulate traffic
    res_sim = client.post(
        "/api/graph/simulate-traffic",
        json={"congestion_probability": 0.4, "block_probability": 0.1},
    )
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert "congested_count" in sim_data
    assert "blocked_count" in sim_data

    # 3. Reset traffic
    res_reset = client.post("/api/graph/reset-traffic")
    assert res_reset.status_code == 200
    stats = res_reset.json()["stats"]
    assert stats["blocked_edges"] == 0
    assert stats["congested_edges"] == 0


def test_frontend_fallback_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_route_with_roadblock_rerouting():
    # Block direct road between delhi and chandigarh
    res_block = client.patch(
        "/api/edge/traffic",
        json={"source": "delhi", "target": "chandigarh", "is_blocked": True, "bidirectional": True},
    )
    assert res_block.status_code == 200

    # Route should either fail or find alternative path without NH44 direct link
    res_route = client.post(
        "/api/route",
        json={"source": "delhi", "target": "chandigarh", "algorithm": "dijkstra"},
    )
    assert res_route.status_code == 200
    route_data = res_route.json()
    # Since chandigarh only connects to delhi in india_highways preset, route should not be found when blocked
    assert route_data["found"] is False


def test_simulate_traffic_with_reset_flag():
    # Simulate with reset=true query param
    res = client.post("/api/graph/simulate-traffic?reset=true")
    assert res.status_code == 200
    data = res.json()
    assert data["congested_count"] == 0
    assert data["blocked_count"] == 0


def test_node_auto_slugify_and_duplicate_slug():
    res1 = client.post("/api/node", json={"name": "Tech Hub", "lat": 12.0, "lng": 77.0})
    assert res1.status_code == 200
    id1 = res1.json()["node"]["id"]
    assert id1 == "tech_hub"

    # Second node with same name should get unique slug
    res2 = client.post("/api/node", json={"name": "Tech Hub", "lat": 12.1, "lng": 77.1})
    assert res2.status_code == 200
    id2 = res2.json()["node"]["id"]
    assert id2 == "tech_hub_1"

    # Cleanup
    client.delete(f"/api/node/{id1}")
    client.delete(f"/api/node/{id2}")


def test_delete_node_removes_incident_edges():
    # Add temporary node and connect to delhi
    client.post("/api/node", json={"id": "temp_city", "name": "Temp City", "lat": 28.0, "lng": 77.0})
    client.post("/api/edge", json={"source": "delhi", "target": "temp_city", "base_distance_km": 80.0})

    assert "temp_city" in app_state.graph.adjacency_list["delhi"]

    # Delete temp_city
    res_del = client.delete("/api/node/temp_city")
    assert res_del.status_code == 200

    # Check incoming edge from delhi is removed
    assert "temp_city" not in app_state.graph.adjacency_list.get("delhi", {})

