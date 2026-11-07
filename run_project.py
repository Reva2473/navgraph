#!/usr/bin/env python3
"""
================================================================================
Launcher Script: Route & Campus Navigator
Experiment 14 (Backend API Deployment) & Experiment 15 (Interactive Map Navigator)
================================================================================
"""

import sys
import os
import argparse
import uvicorn

BANNER = r"""
================================================================================
   ____    ___    _   _   _____   _____     _   _      _     __     __
  |  _ \  / _ \  | | | | |_   _| | ____|   | \ | |    / \    \ \   / /
  | |_) || | | | | | | |   | |   |  _|     |  \| |   / _ \    \ \ / / 
  |  _ < | |_| | | |_| |   | |   | |___    | |\  |  / ___ \    \ V /  
  |_| \_\ \___/   \___/    |_|   |_____|   |_| \_| /_/   \_\    \_/   
                                                                      
    Minor Project: Graph Data Structures & Shortest Path Navigation
================================================================================
  [x] Experiment 14: REST API Server & Algorithmic Backend
      -> Swagger UI (Interactive API Docs): http://{host}:{port}/docs
      -> ReDoc (API Reference):            http://{host}:{port}/redoc
      -> Health Check Endpoint:             http://{host}:{port}/api/health
      -> Active Presets Endpoint:           http://{host}:{port}/api/presets

  [x] Experiment 15: Interactive Frontend Map Navigator
      -> Web Client UI:                     http://{host}:{port}/
================================================================================
  Supported Algorithms: Dijkstra | A* (Haversine Heuristic) | BFS | DFS
  Dynamic Features: Live Traffic Simulation | Road Closures | Multi-Stop Waypoints
================================================================================
"""

def main():
    parser = argparse.ArgumentParser(description="Run Route & Campus Navigator API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    # Ensure project root is in sys.path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print(BANNER.format(host=args.host, port=args.port))
    print(f"[*] Starting server on http://{args.host}:{args.port} ...")
    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
