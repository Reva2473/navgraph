"""
================================================================================
NavGraph DSA - End-to-End Frontend-Backend Contract Integration Tests
Experiment 14: REST API Server & Algorithmic Deployment
Experiment 15: Interactive Frontend Map Navigator Integration
================================================================================
"""

import os
import re
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")
INDEX_HTML_PATH = os.path.join(PUBLIC_DIR, "index.html")
STYLE_CSS_PATH = os.path.join(PUBLIC_DIR, "css", "style.css")
APP_JS_PATH = os.path.join(PUBLIC_DIR, "js", "app.js")


# ==============================================================================
# 1. API Contract Verification Suite
# ==============================================================================

class TestFrontendBackendAPIContract:
    """Verifies that the FastAPI backend strictly fulfills the contract needed by the frontend."""

    def test_serve_frontend_index_and_static_assets(self):
        """GET / serves public/index.html (no-store); CSS and JS are served with revalidation (no-cache)."""
        # 1. Root index.html
        res_index = client.get("/")
        assert res_index.status_code == 200
        assert "text/html" in res_index.headers.get("content-type", "")
        assert "no-store" in res_index.headers.get("cache-control", "")
        # newline="" keeps the file's exact line endings, matching the bytes served.
        with open(INDEX_HTML_PATH, "r", encoding="utf-8", newline="") as f:
            expected_html = f.read()
        assert res_index.text == expected_html

        # 2. Stylesheet
        res_css = client.get("/css/style.css")
        assert res_css.status_code == 200
        assert "text/css" in res_css.headers.get("content-type", "")
        assert res_css.headers.get("cache-control") == "no-cache"
        assert res_css.headers.get("etag")
        assert len(res_css.text) > 0

        # 3. Application JavaScript
        res_js = client.get("/js/app.js")
        assert res_js.status_code == 200
        assert res_js.headers.get("cache-control") == "no-cache"
        assert res_js.headers.get("etag")
        assert len(res_js.text) > 0

    def test_static_cache_control_headers(self):
        """HTML shell and API are never cached; static assets must revalidate and support 304."""
        for path in ["/", "/api/health"]:
            res = client.get(path)
            assert res.status_code == 200
            assert res.headers.get("Cache-Control") == "no-store, no-cache, must-revalidate, max-age=0"
            assert res.headers.get("Pragma") == "no-cache"
            assert res.headers.get("Expires") == "0"
        for path in ["/css/style.css", "/js/app.js"]:
            res = client.get(path)
            assert res.status_code == 200
            assert res.headers.get("Cache-Control") == "no-cache"
            etag = res.headers.get("etag")
            assert etag
            assert client.get(path, headers={"If-None-Match": etag}).status_code == 304

    def test_presets_default_traffic_multiplier_all_unity(self):
        """Verify every edge in campus_navigator and india_highways starts with traffic_multiplier == 1.0."""
        from backend.data.presets import load_preset_graph

        for preset_id in ["campus_navigator", "india_highways"]:
            graph = load_preset_graph(preset_id)
            for u, neighbors in graph.adjacency_list.items():
                for v, edge in neighbors.items():
                    assert edge.traffic_multiplier == 1.0, (
                        f"Preset '{preset_id}' edge ({u} -> {v}) has traffic_multiplier {edge.traffic_multiplier} != 1.0"
                    )

    def test_cache_busting_query_strings_in_index_html(self):
        """Verify public/index.html includes ?v= cache-busting query strings on css/style.css and js/app.js."""
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()

        assert re.search(r'href=["\']css/style\.css\?v=[a-zA-Z0-9_-]+["\']', html_content), (
            "public/index.html must link to css/style.css with a ?v= cache-busting parameter"
        )
        assert re.search(r'src=["\']js/app\.js\?v=[a-zA-Z0-9_-]+["\']', html_content), (
            "public/index.html must load js/app.js with a ?v= cache-busting parameter"
        )

    def test_get_graph_contract_campus_navigator(self):
        """
        GET /api/graph returns:
        {
            active_preset: 'campus_navigator',
            preset_metadata: {...},
            graph: { nodes: [...], edges: [...], adjacency_list: {...}, stats: {...} }
        }
        with exactly 14 nodes on campus_navigator.
        """
        # Ensure campus_navigator is active
        load_res = client.post("/api/presets/campus_navigator/load")
        assert load_res.status_code == 200

        res = client.get("/api/graph")
        assert res.status_code == 200
        data = res.json()

        assert "active_preset" in data
        assert data["active_preset"] == "campus_navigator"
        assert "preset_metadata" in data
        assert isinstance(data["preset_metadata"], dict)

        assert "graph" in data
        graph = data["graph"]
        assert "nodes" in graph
        assert "edges" in graph
        assert "adjacency_list" in graph
        assert "stats" in graph

        # Campus navigator has 14 nodes
        assert isinstance(graph["nodes"], list)
        assert len(graph["nodes"]) == 14

    def test_preset_switching_and_restoration(self):
        """
        POST /api/presets/india_highways/load followed by GET /api/graph returns
        18 nodes on india_highways, and restore campus_navigator afterward.
        """
        # 1. Load india_highways
        load_india = client.post("/api/presets/india_highways/load")
        assert load_india.status_code == 200
        assert load_india.json()["active_preset"] == "india_highways"

        # Verify graph topology contains 18 nodes
        res_india = client.get("/api/graph")
        assert res_india.status_code == 200
        data_india = res_india.json()
        assert data_india["active_preset"] == "india_highways"
        assert len(data_india["graph"]["nodes"]) == 18

        # 2. Restore campus_navigator
        load_campus = client.post("/api/presets/campus_navigator/load")
        assert load_campus.status_code == 200
        assert load_campus.json()["active_preset"] == "campus_navigator"

        res_campus = client.get("/api/graph")
        assert res_campus.status_code == 200
        data_campus = res_campus.json()
        assert data_campus["active_preset"] == "campus_navigator"
        assert len(data_campus["graph"]["nodes"]) == 14

    @pytest.mark.parametrize("algo", ["dijkstra", "a_star", "bfs", "dfs"])
    def test_route_for_all_algorithms(self, algo):
        """
        POST /api/route for all 4 algorithms (dijkstra, a_star, bfs, dfs) returns:
        found: True, path, path_coordinates, steps, total_cost, distance_km, estimated_time_min.
        """
        client.post("/api/presets/campus_navigator/load")

        payload = {
            "source": "main_gate",
            "target": "metro_gate",
            "algorithm": algo,
            "weight_mode": "effective",
        }
        res = client.post("/api/route", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["found"] is True
        assert isinstance(data["path"], list)
        assert len(data["path"]) >= 2
        assert data["path"][0] == "main_gate"
        assert data["path"][-1] == "metro_gate"

        assert isinstance(data["path_coordinates"], list)
        assert len(data["path_coordinates"]) == len(data["path"])

        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0

        assert "total_cost" in data
        assert isinstance(data["total_cost"], (int, float))
        assert data["total_cost"] > 0

        assert "distance_km" in data
        assert isinstance(data["distance_km"], (int, float))
        assert data["distance_km"] > 0

        assert "estimated_time_min" in data
        assert isinstance(data["estimated_time_min"], (int, float))
        assert data["estimated_time_min"] > 0

    def test_compare_endpoint_contract(self):
        """
        POST /api/compare returns:
        - analysis (string)
        - comparison_table (list of 4 algorithm rows with is_optimal_cost and complexity_time).
        """
        client.post("/api/presets/campus_navigator/load")

        payload = {
            "source": "main_gate",
            "target": "metro_gate",
            "weight_mode": "effective",
        }
        res = client.post("/api/compare", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert "analysis" in data
        assert isinstance(data["analysis"], str)
        assert len(data["analysis"]) > 0

        assert "comparison_table" in data
        table = data["comparison_table"]
        assert isinstance(table, list)
        assert len(table) == 4

        algos_in_table = set()
        for row in table:
            assert "algorithm" in row
            algos_in_table.add(row["algorithm"])
            assert "is_optimal_cost" in row
            assert isinstance(row["is_optimal_cost"], bool)
            assert "complexity_time" in row
            assert isinstance(row["complexity_time"], str)

        assert algos_in_table == {"dijkstra", "astar", "bfs", "dfs"}

    def test_multi_stop_endpoint_contract(self):
        """
        POST /api/multi-stop returns:
        found: True, full_path, legs, total_cost, total_distance_km, total_time_min.
        """
        client.post("/api/presets/campus_navigator/load")

        payload = {
            "waypoints": ["main_gate", "central_library", "hostel_north", "metro_gate"],
            "algorithm": "dijkstra",
            "weight_mode": "effective",
        }
        res = client.post("/api/multi-stop", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["found"] is True
        assert "full_path" in data
        assert isinstance(data["full_path"], list)
        assert data["full_path"][0] == "main_gate"
        assert data["full_path"][-1] == "metro_gate"
        assert "central_library" in data["full_path"]
        assert "hostel_north" in data["full_path"]

        assert "legs" in data
        assert isinstance(data["legs"], list)
        assert len(data["legs"]) == 3

        assert "total_cost" in data
        assert isinstance(data["total_cost"], (int, float))
        assert data["total_cost"] > 0

        assert "total_distance_km" in data
        assert isinstance(data["total_distance_km"], (int, float))
        assert data["total_distance_km"] > 0

        assert "total_time_min" in data
        assert isinstance(data["total_time_min"], (int, float))
        assert data["total_time_min"] > 0

    def test_traffic_simulate_endpoint_contract(self):
        """
        POST /api/traffic/simulate returns:
        status: 'success', message, and stats.congested_edges.
        """
        client.post("/api/presets/campus_navigator/load")

        res = client.post("/api/traffic/simulate", json={"congestion_probability": 0.4, "block_probability": 0.1})
        assert res.status_code == 200
        data = res.json()

        assert data.get("status") == "success"
        assert "message" in data
        assert isinstance(data["message"], str)
        assert "stats" in data
        assert "congested_edges" in data["stats"]
        assert isinstance(data["stats"]["congested_edges"], int)

        # Reset traffic back to normal state
        reset_res = client.post("/api/traffic/simulate", json={"reset": True})
        assert reset_res.status_code == 200
        assert reset_res.json().get("status") == "success"


# ==============================================================================
# 2. DOM & JS Integrity Verification Suite
# ==============================================================================

class TestFrontendDOMAndJSIntegrity:
    """Verifies that the static frontend files have zero dead DOM IDs, no broken buttons, and valid API unwrapping."""

    def test_all_js_get_element_by_id_exist_in_html(self):
        """
        Parse public/index.html and public/js/app.js:
        Every getElementById('...') in public/js/app.js corresponds to an existing id="..." in public/index.html.
        """
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read()

        html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_content))
        # Match both single and double quotes for getElementById
        js_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', js_content))

        assert len(js_ids) > 0, "No getElementById calls found in app.js"
        assert len(html_ids) > 0, "No element IDs found in index.html"

        missing_ids = js_ids - html_ids
        assert len(missing_ids) == 0, f"Found dead / missing DOM IDs referenced in JS but absent from HTML: {sorted(list(missing_ids))}"

    def test_btn_sidebar_reset_completely_removed(self):
        """Verify #btn-sidebar-reset (the broken back button) is completely removed from both index.html and app.js."""
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read()

        assert "btn-sidebar-reset" not in html_content, "btn-sidebar-reset still present in public/index.html"
        assert "btn-sidebar-reset" not in js_content, "btn-sidebar-reset still present in public/js/app.js"

    def test_refresh_graph_data_unwraps_graph(self):
        """Verify refreshGraphData in public/js/app.js unwraps .graph from API.getGraph()."""
        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read()

        # Search for refreshGraphData function definition
        func_match = re.search(
            r'async\s+function\s+refreshGraphData\s*\(\s*\)\s*\{([\s\S]*?)(?:async\s+function|\n\s*function|\Z)',
            js_content,
        )
        assert func_match is not None, "refreshGraphData function not found in app.js"
        func_body = func_match.group(1)

        # Should unwrap .graph from response (e.g., res.graph, graphData.graph, (await API.getGraph()).graph)
        has_graph_unwrap = (
            re.search(r'\.graph\b', func_body) is not None
            or re.search(r'const\s+\{\s*graph\s*\}\s*=', func_body) is not None
        )
        assert has_graph_unwrap, "refreshGraphData does not unwrap .graph from API.getGraph() payload"

    def test_harsh_neon_green_removed_from_css_and_js(self):
        """Verify harsh neon green #5effb1 is removed from public/css/style.css and public/js/app.js."""
        with open(STYLE_CSS_PATH, "r", encoding="utf-8") as f:
            css_content = f.read().lower()

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read().lower()

        assert "#5effb1" not in css_content, "Harsh neon green #5effb1 found in public/css/style.css"
        assert "#5effb1" not in js_content, "Harsh neon green #5effb1 found in public/js/app.js"

    def test_marker_hover_popup_and_card_sync(self):
        """Verify marker hover popup and sidebar destination card hover sync are implemented."""
        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read()

        with open(STYLE_CSS_PATH, "r", encoding="utf-8") as f:
            css_content = f.read()

        # JS checks
        assert "markerMap: new Map()" in js_content
        assert "node-hover-popup" in js_content
        assert "navgraph-dark-tooltip" in js_content
        assert "marker-hover-active" in js_content
        assert "state.markerMap.set(node.id, marker)" in js_content
        assert "state.markerMap.get(node.id)" in js_content

        # CSS checks
        assert ".navgraph-dark-tooltip" in css_content
        assert ".node-hover-popup" in css_content
        assert ".node-hover-header" in css_content
        assert ".node-hover-title" in css_content
        assert ".tt-role" in css_content
        assert ".marker-hover-active" in css_content

    def test_nh16_coastal_geometry_and_waypoint_overrides(self):
        """Verify coastal highway overrides prevent NH16 from cutting across the Bay of Bengal."""
        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read()

        assert "COASTAL_EDGE_WAYPOINTS" in js_content
        assert "visakhapatnam__chennai" in js_content
        assert "bhubaneswar__visakhapatnam" in js_content
        assert "getEdgeLatLngs" in js_content
        assert "getEdgeGeometry" in js_content
        # Coordinates of Vijayawada and Rajahmundry on NH16 land route
        assert "16.5062" in js_content
        assert "17.0005" in js_content

    def test_campus_preset_label_and_nsut_dwarka_coordinates(self):
        """Verify campus preset label is NSUT Dwarka Campus and default map center is NSUT Dwarka."""
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read()

        assert "NSUT Dwarka Campus" in html_content
        assert "DEFAULT_CENTER: [28.6103, 77.0375]" in js_content or "[28.6103, 77.0375]" in js_content

    def test_only_selected_route_highlighted_and_marker_anchor_aligned(self):
        """
        Verify:
        1. .outlet-marker-wrapper in public/css/style.css does NOT contain translate(-50%, -50%).
        2. iconSize: [44, 44] and iconAnchor: [22, 22] are used in public/js/app.js.
        3. updatePlayerUI checks isPlayerVisible || state.stepPlayer.isPlaying before calling renderStepOnMap.
        4. Background graph edges do NOT highlight unselected traffic roads in amber/orange.
        """
        with open(STYLE_CSS_PATH, "r", encoding="utf-8") as f:
            css_content = f.read()

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            js_content = f.read()

        # 1. No translate(-50%, -50%) on outlet marker wrapper
        assert "translate(-50%, -50%)" not in css_content
        assert ".outlet-marker-wrapper" in css_content
        assert "width: 44px" in css_content
        assert "height: 44px" in css_content

        # 2. iconSize and iconAnchor are [44, 44] and [22, 22]
        assert "iconSize: [44, 44]" in js_content
        assert "iconAnchor: [22, 22]" in js_content

        # 3. updatePlayerUI gates renderStepOnMap behind drawer open state or isPlaying
        assert "isPlayerVisible || state.stepPlayer.isPlaying" in js_content
        assert "renderStepOnMap(step)" in js_content

        # 4. Background graph edges do not light up in amber/orange based on traffic
        assert "edge.traffic_multiplier > 1.0" not in js_content

        # 5. Active route is drawn after renderGraphOnMap() so it stays crisp on top
        render_pos = js_content.find("renderGraphOnMap()")
        route_pos = js_content.find("drawGlowingMintRoute(result.path_coordinates)")
        assert render_pos != -1 and route_pos != -1
        # In computeRoute(), renderGraphOnMap() is invoked prior to drawGlowingMintRoute()
        compute_fn_match = re.search(r"async function computeRoute[\s\S]*?populateDirectionsList", js_content)
        assert compute_fn_match is not None
        compute_body = compute_fn_match.group(0)
        assert compute_body.find("renderGraphOnMap()") < compute_body.find("drawGlowingMintRoute(result.path_coordinates)"), (
            "computeRoute must call renderGraphOnMap() BEFORE drawGlowingMintRoute() so the route is cleanly drawn on top"
        )

        # 6. Step 0 is not automatically drawn on map when drawer is closed
        assert "state.layers.stepExploration.clearLayers()" in compute_body
        assert "state.layers.stepCurrentMarker.clearLayers()" in compute_body
        assert "dsa-player-drawer" in compute_body


