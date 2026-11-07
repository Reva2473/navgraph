"""
DSA Core Package - Graph Algorithms and Data Structures.

Exports foundational abstract data types and spatial graph algorithms.
"""

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

__all__ = [
    "MinHeap",
    "FIFOQueue",
    "LIFOStack",
    "Node",
    "Edge",
    "WeightedGraph",
    "haversine_distance",
    "dijkstra",
    "a_star",
    "bfs_shortest_hops",
    "dfs_path",
    "multi_stop_route",
    "compare_algorithms",
]
