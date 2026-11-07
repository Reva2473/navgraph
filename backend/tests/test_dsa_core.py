"""
Unit tests for Pure Data Structures, Graph Engine, and Route Optimization Algorithms.
"""

import unittest
from backend.dsa import (
    MinHeap,
    FIFOQueue,
    LIFOStack,
    Node,
    Edge,
    WeightedGraph,
    haversine_distance,
    dijkstra,
    a_star,
    bfs_shortest_hops,
    dfs_path,
    multi_stop_route,
    compare_algorithms,
)
from backend.data import PRESETS_METADATA, load_preset_graph


class TestDSAStructures(unittest.TestCase):
    def test_min_heap_operations(self):
        heap = MinHeap()
        self.assertTrue(heap.is_empty())
        self.assertEqual(len(heap), 0)

        # Push items with arbitrary payloads (dicts) and tie breaking
        heap.push(15.5, {"id": "node_b"})
        heap.push(3.2, {"id": "node_a"})
        heap.push(28.0, {"id": "node_c"})
        heap.push(3.2, {"id": "node_d"})  # same priority

        self.assertEqual(len(heap), 4)
        self.assertFalse(heap.is_empty())

        # Peek
        pri, item = heap.peek()
        self.assertEqual(round(pri, 1), 3.2)

        # Pop order
        p1, i1 = heap.pop()
        p2, i2 = heap.pop()
        p3, i3 = heap.pop()
        p4, i4 = heap.pop()

        self.assertEqual(round(p1, 1), 3.2)
        self.assertEqual(round(p2, 1), 3.2)
        self.assertEqual(round(p3, 1), 15.5)
        self.assertEqual(round(p4, 1), 28.0)
        self.assertTrue(heap.is_empty())

        with self.assertRaises(IndexError):
            heap.pop()

    def test_fifo_queue(self):
        q = FIFOQueue()
        self.assertTrue(q.is_empty())
        q.enqueue("alpha")
        q.enqueue("beta")
        q.enqueue("gamma")
        self.assertEqual(len(q), 3)
        self.assertEqual(q.peek(), "alpha")
        self.assertEqual(q.dequeue(), "alpha")
        self.assertEqual(q.dequeue(), "beta")
        self.assertEqual(q.dequeue(), "gamma")
        self.assertTrue(q.is_empty())

        with self.assertRaises(IndexError):
            q.dequeue()

    def test_lifo_stack(self):
        s = LIFOStack()
        self.assertTrue(s.is_empty())
        s.push(100)
        s.push(200)
        s.push(300)
        self.assertEqual(len(s), 3)
        self.assertEqual(s.peek(), 300)
        self.assertEqual(s.pop(), 300)
        self.assertEqual(s.pop(), 200)
        self.assertEqual(s.pop(), 100)
        self.assertTrue(s.is_empty())

        with self.assertRaises(IndexError):
            s.pop()


class TestGraphEngine(unittest.TestCase):
    def test_haversine(self):
        # Distance between New Delhi (28.6139, 77.2090) and Jaipur (26.9124, 75.7873) is ~238 km straight line
        dist = haversine_distance(28.6139, 77.2090, 26.9124, 75.7873)
        self.assertTrue(230.0 < dist < 250.0)

    def test_weighted_graph_topology(self):
        g = WeightedGraph()
        n1 = Node("n1", "Node 1", 10.0, 20.0)
        n2 = Node("n2", "Node 2", 10.5, 20.5)
        g.add_node(n1)
        g.add_node(n2)
        self.assertIn("n1", g.nodes)
        self.assertIn("n2", g.nodes)

        # Add edge with automatic distance computation
        edge = g.add_edge("n1", "n2", road_name="Test Way", speed_limit_kmh=60.0)
        self.assertIsNotNone(edge)
        self.assertGreater(edge.base_distance_km, 0)
        self.assertEqual(edge.effective_weight, edge.base_distance_km)

        # Traffic update
        g.update_edge_traffic("n1", "n2", traffic_multiplier=1.5)
        e_updated = g.get_edge("n1", "n2")
        self.assertEqual(e_updated.traffic_multiplier, 1.5)
        self.assertEqual(e_updated.effective_weight, round(edge.base_distance_km * 1.5, 2))

        # Blockage
        g.update_edge_traffic("n1", "n2", is_blocked=True)
        self.assertEqual(e_updated.effective_weight, float("inf"))

        # Serialization
        g_dict = g.to_dict()
        self.assertEqual(len(g_dict["nodes"]), 2)
        self.assertEqual(len(g_dict["edges"]), 1)
        self.assertEqual(g_dict["stats"]["blocked_edges"], 1)


class TestAlgorithms(unittest.TestCase):
    def setUp(self):
        self.g = load_preset_graph("india_highways")

    def test_dijkstra_optimal_path(self):
        res = dijkstra(self.g, "delhi", "bengaluru", weight_mode="effective")
        self.assertTrue(res["found"])
        self.assertEqual(res["source"], "delhi")
        self.assertEqual(res["target"], "bengaluru")
        self.assertEqual(res["path"][0], "delhi")
        self.assertEqual(res["path"][-1], "bengaluru")
        self.assertGreater(len(res["directions"]), 0)
        self.assertGreater(len(res["steps"]), 0)

    def test_astar_exploration(self):
        res_d = dijkstra(self.g, "delhi", "bengaluru", weight_mode="effective")
        res_a = a_star(self.g, "delhi", "bengaluru", weight_mode="effective")

        self.assertTrue(res_a["found"])
        # Both must find the optimal cost
        self.assertEqual(res_a["effective_cost"], res_d["effective_cost"])
        # A* heuristic should explore fewer or equal nodes
        self.assertLessEqual(res_a["nodes_explored"], res_d["nodes_explored"])

    def test_bfs_fewest_hops(self):
        res_bfs = bfs_shortest_hops(self.g, "delhi", "bengaluru")
        self.assertTrue(res_bfs["found"])
        self.assertGreater(res_bfs["hop_count"], 0)

    def test_dfs_reachability(self):
        res_dfs = dfs_path(self.g, "delhi", "bengaluru")
        self.assertTrue(res_dfs["found"])
        self.assertEqual(res_dfs["path"][0], "delhi")
        self.assertEqual(res_dfs["path"][-1], "bengaluru")

    def test_blocked_road_avoidance(self):
        # Create a copy / modify graph
        g_test = load_preset_graph("india_highways")
        g_test.update_edge_traffic("delhi", "jaipur", is_blocked=True)

        res = dijkstra(g_test, "delhi", "jaipur")
        self.assertTrue(res["found"])
        # Path cannot be direct 1-hop ['delhi', 'jaipur']
        self.assertNotEqual(res["path"], ["delhi", "jaipur"])

    def test_multi_stop_route(self):
        waypoints = ["delhi", "jaipur", "mumbai", "bengaluru"]
        res = multi_stop_route(self.g, waypoints, algorithm="dijkstra")
        self.assertTrue(res["found"])
        self.assertEqual(res["waypoints"], waypoints)
        self.assertEqual(len(res["legs"]), 3)
        self.assertEqual(res["path"][0], "delhi")
        self.assertEqual(res["path"][-1], "bengaluru")

    def test_compare_algorithms(self):
        comp = compare_algorithms(self.g, "delhi", "bengaluru")
        self.assertEqual(len(comp["comparison_table"]), 4)
        self.assertGreater(len(comp["analysis"]), 0)
        self.assertIn("dijkstra", comp["results"])
        self.assertIn("astar", comp["results"])
        self.assertIn("bfs", comp["results"])
        self.assertIn("dfs", comp["results"])


class TestPresets(unittest.TestCase):
    def test_presets_metadata(self):
        self.assertIn("india_highways", PRESETS_METADATA)
        self.assertIn("campus_navigator", PRESETS_METADATA)

    def test_campus_navigator(self):
        g_campus = load_preset_graph("campus_navigator")
        self.assertEqual(len(g_campus.nodes), 14)
        res = a_star(g_campus, "main_gate", "cs_dept")
        self.assertTrue(res["found"])
        self.assertEqual(res["path"][0], "main_gate")
        self.assertEqual(res["path"][-1], "cs_dept")


if __name__ == "__main__":
    unittest.main()
