"""
Regression tests for per-session graph state, input validation, and
algorithm output fixes (comparison optimality, BFS/DFS step data).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.data.presets import load_preset_graph
from backend.dsa.algorithms import bfs_shortest_hops, compare_algorithms, dfs_path
from backend.main import MAX_NODES, app, app_state, sessions

client = TestClient(app)


def _sid() -> dict:
    return {"X-Session-Id": str(uuid.uuid4())}


@pytest.fixture(autouse=True)
def _clean_state():
    app_state.reload_preset("india_highways")
    sessions.clear()
    yield
    app_state.reload_preset("india_highways")
    sessions.clear()


# ------------------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------------------

def test_sessions_are_isolated():
    a, b = _sid(), _sid()
    assert client.post("/api/presets/india_highways/load", headers=a).status_code == 200
    assert client.post("/api/presets/india_highways/load", headers=b).status_code == 200

    res = client.post("/api/node", headers=a, json={"name": "Agra", "lat": 27.17, "lng": 78.0})
    assert res.status_code == 200

    ids_a = {n["id"] for n in client.get("/api/graph", headers=a).json()["graph"]["nodes"]}
    ids_b = {n["id"] for n in client.get("/api/graph", headers=b).json()["graph"]["nodes"]}
    assert "agra" in ids_a
    assert "agra" not in ids_b
    assert "agra" not in app_state.graph.nodes


def test_unknown_session_returns_409_until_restored():
    h = _sid()
    res = client.post("/api/route", headers=h, json={"source": "delhi", "target": "mumbai"})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "session_expired"

    # Restore from a client snapshot that includes a custom node and a blocked road.
    graph = load_preset_graph("india_highways").to_dict()
    graph["nodes"].append({"id": "agra", "name": "Agra", "lat": 27.17, "lng": 78.0, "category": "custom", "description": ""})
    graph["adjacency_list"]["agra"] = [{"target": "delhi", "base_distance_km": 230.0}]
    for e in graph["adjacency_list"]["delhi"]:
        if e["target"] == "jaipur":
            e["is_blocked"] = True

    res = client.post(
        "/api/session/restore",
        headers=h,
        json={"preset": "india_highways", "nodes": graph["nodes"], "adjacency_list": graph["adjacency_list"]},
    )
    assert res.status_code == 200, res.text

    restored = client.get("/api/graph", headers=h).json()["graph"]
    assert any(n["id"] == "agra" for n in restored["nodes"])
    delhi_jaipur = [e for e in restored["adjacency_list"]["delhi"] if e["target"] == "jaipur"][0]
    assert delhi_jaipur["is_blocked"] is True
    # Directed edge restored exactly as sent (agra -> delhi only).
    assert not any(e["target"] == "agra" for e in restored["adjacency_list"]["delhi"])

    assert client.post("/api/route", headers=h, json={"source": "delhi", "target": "mumbai"}).status_code == 200


def test_restore_rejects_bad_snapshots():
    h = _sid()
    base = {"preset": "india_highways", "nodes": [
        {"id": "a", "name": "A", "lat": 28.0, "lng": 77.0},
        {"id": "b", "name": "B", "lat": 29.0, "lng": 77.0},
    ]}
    # Edge to unknown node
    assert client.post("/api/session/restore", headers=h, json={**base, "adjacency_list": {"a": [{"target": "zzz", "base_distance_km": 5}]}}).status_code == 400
    # Edge shorter than straight line (~111 km)
    assert client.post("/api/session/restore", headers=h, json={**base, "adjacency_list": {"a": [{"target": "b", "base_distance_km": 5}]}}).status_code == 400
    # Unsafe node ID
    bad = {"preset": "india_highways", "nodes": [{"id": "\"><img src=x>", "name": "X", "lat": 0, "lng": 0}]}
    assert client.post("/api/session/restore", headers=h, json=bad).status_code == 422
    # Header required
    assert client.post("/api/session/restore", json={**base, "adjacency_list": {}}).status_code == 400


def test_invalid_session_header_rejected():
    res = client.get("/api/graph", headers={"X-Session-Id": "bad id!"})
    assert res.status_code == 400


def test_route_no_longer_switches_preset_silently():
    client.post("/api/node", json={"name": "Agra", "lat": 27.17, "lng": 78.0})
    res = client.post("/api/route", json={"source": "main_gate", "target": "cs_dept"})
    assert res.status_code == 404
    assert app_state.current_preset == "india_highways"
    assert "agra" in app_state.graph.nodes


# ------------------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [
    {"name": "X", "lat": 999, "lng": 0},
    {"name": "X", "lat": 0, "lng": -999},
    {"name": "   ", "lat": 0, "lng": 0},
    {"id": "\"><script>alert(1)</script>", "name": "X", "lat": 0, "lng": 0},
    {"name": "X" * 101, "lat": 0, "lng": 0},
])
def test_add_node_validation(payload):
    assert client.post("/api/node", json=payload).status_code == 422


def test_blank_id_is_auto_generated():
    res = client.post("/api/node", json={"id": "", "name": "New Town", "lat": 22.0, "lng": 88.0})
    assert res.status_code == 200
    assert res.json()["node"]["id"] == "new_town"


def test_edge_shorter_than_straight_line_rejected():
    # Delhi -> Chandigarh is ~238 km in a straight line.
    res = client.post("/api/edge", json={"source": "delhi", "target": "chandigarh", "base_distance_km": 10})
    assert res.status_code == 400
    assert "straight-line" in res.json()["detail"]


def test_node_limit_enforced():
    h = _sid()
    client.post("/api/presets/campus_navigator/load", headers=h)
    st = sessions.get(h["X-Session-Id"])
    for i in range(MAX_NODES - len(st.graph.nodes)):
        assert client.post("/api/node", headers=h, json={"name": f"N{i}", "lat": 28.6, "lng": 77.03}).status_code == 200
    assert client.post("/api/node", headers=h, json={"name": "Overflow", "lat": 28.6, "lng": 77.03}).status_code == 400


def test_traffic_get_aliases_removed():
    assert client.get("/api/graph/simulate-traffic").status_code == 405
    assert client.get("/api/graph/reset-traffic").status_code == 405


# ------------------------------------------------------------------------------
# Algorithm output fixes
# ------------------------------------------------------------------------------

def test_compare_optimal_flag_uses_distance_in_distance_mode():
    g = load_preset_graph("india_highways")
    g.update_edge_traffic("hyderabad", "bengaluru", traffic_multiplier=3.0)
    comp = compare_algorithms(g, "delhi", "bengaluru", weight_mode="distance")
    rows = {r["algorithm"]: r for r in comp["comparison_table"]}

    assert rows["dijkstra"]["is_optimal_cost"] is True
    assert rows["astar"]["is_optimal_cost"] is True
    shortest = min(r["total_distance_km"] for r in rows.values() if r["found"])
    for r in rows.values():
        if r["is_optimal_cost"]:
            assert r["total_distance_km"] == shortest


def test_compare_optimal_flag_effective_mode():
    g = load_preset_graph("india_highways")
    g.update_edge_traffic("hyderabad", "bengaluru", traffic_multiplier=3.0)
    comp = compare_algorithms(g, "delhi", "bengaluru", weight_mode="effective")
    rows = {r["algorithm"]: r for r in comp["comparison_table"]}
    best = min(r["effective_cost"] for r in rows.values() if r["found"])
    assert rows["dijkstra"]["is_optimal_cost"] is True
    assert rows["dijkstra"]["effective_cost"] == best


def test_bfs_steps_hold_per_step_hop_snapshots():
    g = load_preset_graph("india_highways")
    res = bfs_shortest_hops(g, "delhi", "kochi")
    sizes = [len(s["distances"]) for s in res["steps"]]
    assert sizes == sorted(sizes)
    assert sizes[0] < sizes[-1]


def test_dfs_path_follows_traversal_tree():
    g = load_preset_graph("india_highways")
    res = dfs_path(g, "delhi", "kochi")
    assert res["found"]
    path = res["path"]
    # Each hop is a real edge, and depth increases by one along the path.
    depths = res["steps"][-1]["distances"]
    for i, (u, v) in enumerate(zip(path, path[1:])):
        assert g.get_edge(u, v) is not None
        assert depths[u] == i and depths[v] == i + 1
    # Frontier is reported as plain node IDs for the UI.
    assert all(isinstance(x, str) for s in res["steps"] for x in s["frontier"])
