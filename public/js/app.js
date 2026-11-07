/**
 * navgraph dsa - Intelligent Route Navigator & Graph Visualizer
 * Frontend Engine (DSA Experiments 14 & 15: Minor Project)
 * OutletBuddy-Style Dark-Matte UX with Dijkstra, A*, BFS, DFS & Step-by-Step Traversal Inspector
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. CARTO BASEMAP TILE & API CONFIGURATION
  // =========================================================================
  const CONFIG = {
    // CARTO Basemaps API Key
    CARTO_API_KEY: 'cb1_52hf_1_adb51a7ad8aecbeb23421216',
    DEFAULT_CENTER: [28.6103, 77.0375], // NSUT Dwarka Sector 3
    DEFAULT_PRESET: 'campus_navigator', // Starts on NSUT Dwarka Campus
    DEFAULT_SOURCE: 'main_gate',
    DEFAULT_TARGET: 'metro_gate'
  };

  /**
   * Safely extracts the clean API key whether the user pasted the raw key
   * or a full URL like "https://basemaps.cartocdn.com/...?key=xyz"
   */
  function extractCartoKey(input) {
    if (!input || typeof input !== 'string') return '';
    const trimmed = input.trim();
    const match = trimmed.match(/[?&](?:key|api_key)=([a-zA-Z0-9_\-]+)/i);
    if (match && match[1]) {
      return match[1];
    }
    return trimmed;
  }

  // =========================================================================
  // 2. NODE VISUAL IDENTITY REGISTRY (PASTEL COLORS & CRISP DARK ICONS)
  // =========================================================================
  const NODE_STYLE_REGISTRY = {
    // Campus Navigator Landmarks
    main_gate: { icon: 'fa-location-arrow', color: '#ffffff', textColor: '#111111', pillText: 'Gate' },
    security_hub: { icon: 'fa-shield-halved', color: '#fecdd3', textColor: '#111111', pillText: 'Security' },
    admin_block: { icon: 'fa-building-columns', color: '#ddd6fe', textColor: '#111111', pillText: 'Admin' },
    central_library: { icon: 'fa-book-bookmark', color: '#bae6fd', textColor: '#111111', pillText: 'Library' },
    cs_dept: { icon: 'fa-laptop-code', color: '#93c5fd', textColor: '#111111', pillText: 'CSE' },
    ece_dept: { icon: 'fa-microchip', color: '#f6d06b', textColor: '#111111', pillText: 'ECE' },
    innovation_hub: { icon: 'fa-lightbulb', color: '#f9c8e0', textColor: '#111111', pillText: 'TNP' },
    auditorium: { icon: 'fa-masks-theater', color: '#fed7aa', textColor: '#111111', pillText: 'Auditorium' },
    cafeteria: { icon: 'fa-utensils', color: '#fde047', textColor: '#111111', pillText: 'Dining' },
    hostel_north: { icon: 'fa-bed', color: '#cbd5e1', textColor: '#111111', pillText: 'Hostel N' },
    hostel_south: { icon: 'fa-hotel', color: '#e2e8f0', textColor: '#111111', pillText: 'Hostel S' },
    sports_arena: { icon: 'fa-futbol', color: '#a5b4fc', textColor: '#111111', pillText: 'Sports' },
    medical_center: { icon: 'fa-heart-pulse', color: '#fca5a5', textColor: '#111111', pillText: 'Medical' },
    metro_gate: { icon: 'fa-train-subway', color: '#ffffff', textColor: '#111111', pillText: 'Metro' },

    // India Highways Cities
    delhi: { icon: 'fa-landmark-dome', color: '#ffffff', textColor: '#111111', pillText: 'DL · Hub' },
    chandigarh: { icon: 'fa-tree', color: '#93c5fd', textColor: '#111111', pillText: 'CH' },
    jaipur: { icon: 'fa-fort-awesome', color: '#f9c8e0', textColor: '#111111', pillText: 'RJ' },
    lucknow: { icon: 'fa-feather', color: '#fed7aa', textColor: '#111111', pillText: 'UP' },
    ahmedabad: { icon: 'fa-industry', color: '#fde047', textColor: '#111111', pillText: 'GJ' },
    bhopal: { icon: 'fa-crosshairs', color: '#e2e8f0', textColor: '#111111', pillText: 'MP' },
    patna: { icon: 'fa-water', color: '#bae6fd', textColor: '#111111', pillText: 'BR' },
    guwahati: { icon: 'fa-mountain', color: '#a5b4fc', textColor: '#111111', pillText: 'AS' },
    kolkata: { icon: 'fa-bridge-water', color: '#fed7aa', textColor: '#111111', pillText: 'WB' },
    mumbai: { icon: 'fa-building', color: '#bae6fd', textColor: '#111111', pillText: 'MH · West' },
    pune: { icon: 'fa-graduation-cap', color: '#fecdd3', textColor: '#111111', pillText: 'MH' },
    nagpur: { icon: 'fa-bullseye', color: '#ddd6fe', textColor: '#111111', pillText: 'MH · Core' },
    bhubaneswar: { icon: 'fa-place-of-worship', color: '#f6d06b', textColor: '#111111', pillText: 'OD' },
    hyderabad: { icon: 'fa-gem', color: '#ddd6fe', textColor: '#111111', pillText: 'TG' },
    visakhapatnam: { icon: 'fa-ship', color: '#bae6fd', textColor: '#111111', pillText: 'AP · Port' },
    bengaluru: { icon: 'fa-microchip', color: '#93c5fd', textColor: '#111111', pillText: 'KA · South' },
    chennai: { icon: 'fa-anchor', color: '#fde68a', textColor: '#111111', pillText: 'TN · Port' },
    kochi: { icon: 'fa-compass', color: '#86efac', textColor: '#111111', pillText: 'KL' }
  };

  const CATEGORY_STYLE_FALLBACKS = {
    gate: { icon: 'fa-door-open', color: '#ffffff', textColor: '#111111', pillText: 'Gate' },
    admin: { icon: 'fa-building-columns', color: '#ddd6fe', textColor: '#111111', pillText: 'Admin' },
    academic: { icon: 'fa-book-bookmark', color: '#bae6fd', textColor: '#111111', pillText: 'Academic' },
    research: { icon: 'fa-lightbulb', color: '#f9c8e0', textColor: '#111111', pillText: 'Research' },
    cultural: { icon: 'fa-masks-theater', color: '#fed7aa', textColor: '#111111', pillText: 'Cultural' },
    amenity: { icon: 'fa-utensils', color: '#fde047', textColor: '#111111', pillText: 'Dining' },
    residence: { icon: 'fa-bed', color: '#cbd5e1', textColor: '#111111', pillText: 'Hostel' },
    sports: { icon: 'fa-futbol', color: '#86efac', textColor: '#111111', pillText: 'Sports' },
    health: { icon: 'fa-heart-pulse', color: '#fca5a5', textColor: '#111111', pillText: 'Medical' },
    metro: { icon: 'fa-city', color: '#bae6fd', textColor: '#111111', pillText: 'Metro' },
    hub: { icon: 'fa-arrows-split-up-and-left', color: '#ddd6fe', textColor: '#111111', pillText: 'Hub' },
    capital: { icon: 'fa-landmark', color: '#fed7aa', textColor: '#111111', pillText: 'Capital' }
  };

  function getNodeStyle(node) {
    if (!node) return { icon: 'fa-location-dot', color: '#ffffff', textColor: '#111111', pillText: 'Vertex' };
    if (NODE_STYLE_REGISTRY[node.id]) {
      return NODE_STYLE_REGISTRY[node.id];
    }
    const cat = (node.category || '').toLowerCase();
    if (CATEGORY_STYLE_FALLBACKS[cat]) {
      return CATEGORY_STYLE_FALLBACKS[cat];
    }
    return { icon: 'fa-location-dot', color: '#ffffff', textColor: '#111111', pillText: 'Vertex' };
  }

  // =========================================================================
  // 3. APPLICATION STATE
  // =========================================================================
  const state = {
    currentTheme: 'amber',
    activePreset: CONFIG.DEFAULT_PRESET,
    presets: [],
    graph: { nodes: [], edges: [], adjacency_list: {}, stats: {} },
    nodeMap: new Map(), // node_id -> node object
    markerMap: new Map(), // node_id -> Leaflet marker instance

    // Route configuration
    selectedSource: CONFIG.DEFAULT_SOURCE,
    selectedTarget: CONFIG.DEFAULT_TARGET,
    waypoints: [],
    selectedAlgorithm: 'dijkstra',
    weightMode: 'effective', // 'effective' (traffic-aware) | 'distance' (pure km)

    // Interaction modes
    pickingMode: null, // null | 'source' | 'target' | 'waypoint' | 'map-add-node'
    activeWaypointIdx: null,
    selectedEdgeForEdit: null,
    searchQuery: '',

    // Traversal step player
    stepPlayer: {
      steps: [],
      currentIndex: 0,
      isPlaying: false,
      intervalId: null,
      speedMs: 650
    },

    // Latest results
    routeResult: null,
    comparisonResult: null,

    // Leaflet handles
    map: null,
    layers: {
      tile: null,
      edges: null,
      pathOuter: null,
      pathMid: null,
      pathCore: null,
      stepExploration: null,
      markers: null,
      stepCurrentMarker: null
    },

    // Display options
    showEdgesProminent: true,
    showTraffic: true
  };

  // =========================================================================
  // 4. API CLIENT (FASTAPI BACKEND INTEGRATION)
  // =========================================================================
  const API = {
    baseUrl: '',

    async request(endpoint, options = {}) {
      const url = `${this.baseUrl}${endpoint}`;
      const defaultHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      };

      try {
        const response = await fetch(url, {
          ...options,
          headers: { ...defaultHeaders, ...options.headers }
        });

        if (!response.ok) {
          let errorDetail = `HTTP ${response.status} ${response.statusText}`;
          try {
            const errorJson = await response.json();
            if (errorJson.detail) {
              errorDetail = typeof errorJson.detail === 'string'
                ? errorJson.detail
                : JSON.stringify(errorJson.detail);
            }
          } catch (_) { }
          throw new Error(errorDetail);
        }

        return await response.json();
      } catch (err) {
        console.error(`API Request Failed [${options.method || 'GET'} ${url}]:`, err);
        throw err;
      }
    },

    healthCheck() {
      return this.request('/api/health');
    },

    getPresets() {
      return this.request('/api/presets');
    },

    loadPreset(presetId) {
      return this.request(`/api/presets/${encodeURIComponent(presetId)}/load`, {
        method: 'POST'
      });
    },

    getGraph(presetId) {
      const q = presetId ? `?preset=${encodeURIComponent(presetId)}` : '';
      return this.request(`/api/graph${q}`);
    },

    computeRoute(body) {
      return this.request('/api/route', {
        method: 'POST',
        body: JSON.stringify(body)
      });
    },

    compareAlgorithms(body) {
      return this.request('/api/compare', {
        method: 'POST',
        body: JSON.stringify(body)
      });
    },

    addNode(node) {
      return this.request('/api/node', {
        method: 'POST',
        body: JSON.stringify(node)
      });
    },

    deleteNode(nodeId) {
      return this.request(`/api/node/${encodeURIComponent(nodeId)}`, {
        method: 'DELETE'
      });
    },

    addEdge(edge) {
      return this.request('/api/edge', {
        method: 'POST',
        body: JSON.stringify(edge)
      });
    },

    deleteEdge(source, target) {
      return this.request(`/api/edge?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}&bidirectional=true`, {
        method: 'DELETE'
      });
    },

    updateEdgeTraffic(payload) {
      return this.request('/api/edge/traffic', {
        method: 'PATCH',
        body: JSON.stringify(payload)
      });
    },

    simulateTraffic() {
      return this.request('/api/graph/simulate-traffic', {
        method: 'POST'
      });
    },

    resetTraffic() {
      return this.request('/api/graph/reset-traffic', {
        method: 'POST'
      });
    }
  };

  // =========================================================================
  // 5. TOAST NOTIFICATIONS
  // =========================================================================
  function showToast(message, type = 'info', title = null) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-circle-info text-cyan';
    if (type === 'success') iconClass = 'fa-circle-check text-mint';
    if (type === 'error') iconClass = 'fa-triangle-exclamation text-rose';
    if (type === 'warning') iconClass = 'fa-circle-exclamation text-amber';

    const defaultTitle = type.charAt(0).toUpperCase() + type.slice(1);

    toast.innerHTML = `
      <div class="toast-icon"><i class="fa-solid ${iconClass}"></i></div>
      <div class="toast-content flex-1">
        <div class="toast-title">${title || defaultTitle}</div>
        <div class="toast-msg">${escapeHtml(message)}</div>
      </div>
      <button class="btn-circle-icon btn-xs" style="border:none; background:transparent;" onclick="this.parentElement.remove()">
        <i class="fa-solid fa-xmark"></i>
      </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 250);
    }, 4200);
  }

  // =========================================================================
  // 6. MAP INITIALIZATION (CARTO dark_nolabels)
  // =========================================================================
  function initMap() {
    state.map = L.map('map', {
      center: CONFIG.DEFAULT_CENTER || [28.6103, 77.0375],
      zoom: 16,
      zoomControl: false,
      attributionControl: false
    });

    const cleanKey = extractCartoKey(CONFIG.CARTO_API_KEY);
    const tileUrl = cleanKey
      ? `https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${encodeURIComponent(cleanKey)}`
      : 'https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png';

    state.layers.tile = L.tileLayer(tileUrl, {
      subdomains: 'abcd',
      tileSize: 256,
      maxZoom: 19
    }).addTo(state.map);

    // Keep map resized on viewport changes
    const mapEl = document.getElementById('map');
    if (mapEl && typeof ResizeObserver !== 'undefined') {
      const resizeObserver = new ResizeObserver(() => {
        if (state.map) state.map.invalidateSize();
      });
      resizeObserver.observe(mapEl);
    }

    // Layer Groups
    state.layers.edges = L.layerGroup().addTo(state.map);
    state.layers.pathOuter = L.layerGroup().addTo(state.map);
    state.layers.pathMid = L.layerGroup().addTo(state.map);
    state.layers.pathCore = L.layerGroup().addTo(state.map);
    state.layers.stepExploration = L.layerGroup().addTo(state.map);
    state.layers.markers = L.layerGroup().addTo(state.map);
    state.layers.stepCurrentMarker = L.layerGroup().addTo(state.map);

    state.map.on('click', handleMapClick);
  }

  // =========================================================================
  // 7. ROUTE POLYLINE RENDERING & DYNAMIC PALETTE THEMES
  // =========================================================================
  const THEMES = {
    amber: {
      id: 'amber',
      name: 'Warm Amber',
      accentPrimary: '#f59e0b',
      accentLight: '#fbbf24',
      accentDark: '#d97706',
      accentGlow: 'rgba(245, 158, 11, 0.35)',
      accentSubtle: 'rgba(245, 158, 11, 0.14)',
      routeGlow: 'rgba(245, 158, 11, 0.35)',
      routePrimary: '#f59e0b',
      routeCore: '#fef08a'
    },
    sky: {
      id: 'sky',
      name: 'Sky Blue',
      accentPrimary: '#38bdf8',
      accentLight: '#7dd3fc',
      accentDark: '#0284c7',
      accentGlow: 'rgba(56, 189, 248, 0.35)',
      accentSubtle: 'rgba(56, 189, 248, 0.14)',
      routeGlow: 'rgba(56, 189, 248, 0.35)',
      routePrimary: '#38bdf8',
      routeCore: '#e0f2fe'
    },
    violet: {
      id: 'violet',
      name: 'Electric Violet',
      accentPrimary: '#a855f7',
      accentLight: '#c084fc',
      accentDark: '#7e22ce',
      accentGlow: 'rgba(168, 85, 247, 0.35)',
      accentSubtle: 'rgba(168, 85, 247, 0.14)',
      routeGlow: 'rgba(168, 85, 247, 0.35)',
      routePrimary: '#a855f7',
      routeCore: '#f3e8ff'
    },
    emerald: {
      id: 'emerald',
      name: 'Emerald Mint',
      accentPrimary: '#10b981',
      accentLight: '#34d399',
      accentDark: '#059669',
      accentGlow: 'rgba(16, 185, 129, 0.35)',
      accentSubtle: 'rgba(16, 185, 129, 0.14)',
      routeGlow: 'rgba(16, 185, 129, 0.35)',
      routePrimary: '#10b981',
      routeCore: '#d1fae5'
    }
  };

  function getCurrentTheme() {
    const id = state.currentTheme || 'amber';
    return THEMES[id] || THEMES.amber;
  }

  function applyTheme(themeId, shouldRedraw = true) {
    if (!THEMES[themeId]) themeId = 'amber';
    state.currentTheme = themeId;
    try {
      localStorage.setItem('navgraph_theme', themeId);
    } catch (_) {}

    const theme = THEMES[themeId];
    const root = document.documentElement;
    root.style.setProperty('--accent-primary', theme.accentPrimary);
    root.style.setProperty('--accent-primary-light', theme.accentLight);
    root.style.setProperty('--accent-primary-dark', theme.accentDark);
    root.style.setProperty('--accent-primary-glow', theme.accentGlow);
    root.style.setProperty('--accent-primary-subtle', theme.accentSubtle);
    root.style.setProperty('--accent-mint', theme.accentPrimary);
    root.style.setProperty('--accent-mint-light', theme.accentLight);
    root.style.setProperty('--accent-mint-dark', theme.accentDark);
    root.style.setProperty('--accent-mint-glow', theme.accentGlow);
    root.style.setProperty('--accent-mint-subtle', theme.accentSubtle);

    const container = document.getElementById('theme-picker-container');
    if (container) {
      container.querySelectorAll('.theme-dot').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === themeId);
      });
    }

    if (shouldRedraw && state.routeResult && state.routeResult.path_coordinates) {
      drawGlowingMintRoute(state.routeResult.path_coordinates, false);
    }
  }

  // =========================================================================
  // 7. COASTAL HIGHWAY GEOMETRY & WAYPOINT OVERRIDES (NH16 BAY OF BENGAL FIX)
  // =========================================================================
  const COASTAL_EDGE_WAYPOINTS = {
    'visakhapatnam__chennai': [
      [17.6868, 83.2185], // Visakhapatnam
      [17.0005, 81.8040], // Rajahmundry (NH16)
      [16.5062, 80.6480], // Vijayawada (NH16)
      [15.5057, 80.0499], // Ongole (NH16)
      [14.4426, 79.9865], // Nellore (NH16)
      [13.0827, 80.2707]  // Chennai
    ],
    'bhubaneswar__visakhapatnam': [
      [20.2961, 85.8245], // Bhubaneswar
      [19.3150, 84.7941], // Brahmapur (NH16)
      [18.2949, 83.8938], // Srikakulam (NH16)
      [17.6868, 83.2185]  // Visakhapatnam
    ]
  };

  function getEdgeLatLngs(uId, vId, uLatLng, vLatLng) {
    const fwdKey = `${uId}__${vId}`;
    const revKey = `${vId}__${uId}`;
    if (COASTAL_EDGE_WAYPOINTS[fwdKey]) {
      return COASTAL_EDGE_WAYPOINTS[fwdKey];
    }
    if (COASTAL_EDGE_WAYPOINTS[revKey]) {
      return [...COASTAL_EDGE_WAYPOINTS[revKey]].reverse();
    }
    return [uLatLng, vLatLng];
  }

  function getEdgeGeometry(uId, vId, uLatLng, vLatLng) {
    return getEdgeLatLngs(uId, vId, uLatLng, vLatLng);
  }

  /**
   * Draws the route polyline with coastal geometry expansion.
   * If state.routeResult.path (or pathNodeIds) is present, consecutive node pairs are expanded
   * through getEdgeLatLngs so coastal highways like NH16 (Visakhapatnam <-> Chennai) follow
   * real-world land geometry and align 100% pixel-perfectly on top of underlying edges.
   */
  function drawGlowingMintRoute(coordinates, shouldFitBounds = true, pathNodeIds = null) {
    state.layers.pathOuter.clearLayers();
    state.layers.pathMid.clearLayers();
    state.layers.pathCore.clearLayers();

    if (!coordinates || coordinates.length < 2) return;

    let routeCoords = coordinates;
    const nodesInPath = pathNodeIds || (state.routeResult && state.routeResult.path);
    if (nodesInPath && Array.isArray(nodesInPath) && nodesInPath.length >= 2) {
      const expanded = [];
      for (let i = 0; i < nodesInPath.length - 1; i++) {
        const uId = nodesInPath[i];
        const vId = nodesInPath[i + 1];
        const uNode = state.nodeMap.get(uId);
        const vNode = state.nodeMap.get(vId);
        const uPt = uNode ? [uNode.lat, uNode.lng] : (coordinates[i] || [0, 0]);
        const vPt = vNode ? [vNode.lat, vNode.lng] : (coordinates[i + 1] || [0, 0]);
        const seg = getEdgeLatLngs(uId, vId, uPt, vPt);
        if (expanded.length === 0) {
          expanded.push(...seg);
        } else {
          expanded.push(...seg.slice(1));
        }
      }
      if (expanded.length >= 2) {
        routeCoords = expanded;
      }
    }

    const theme = getCurrentTheme();

    // Layer 1: Outer Soft Radiant Glow
    const outerGlow = L.polyline(routeCoords, {
      color: theme.routeGlow,
      weight: 12,
      opacity: 0.35,
      lineCap: 'round',
      lineJoin: 'round'
    });

    // Layer 2: Mid Saturated Glow
    const midGlow = L.polyline(routeCoords, {
      color: theme.routePrimary,
      weight: 6,
      opacity: 0.65,
      lineCap: 'round',
      lineJoin: 'round'
    });

    // Layer 3: Crisp Bright Core
    const coreLine = L.polyline(routeCoords, {
      color: theme.routeCore,
      weight: 3.5,
      opacity: 1.0,
      lineCap: 'round',
      lineJoin: 'round'
    });

    state.layers.pathOuter.addLayer(outerGlow);
    state.layers.pathMid.addLayer(midGlow);
    state.layers.pathCore.addLayer(coreLine);

    if (shouldFitBounds) {
      // Zoom and pan comfortably to fit the route
      const bounds = L.latLngBounds(routeCoords);
      state.map.fitBounds(bounds, { padding: [80, 80], maxZoom: 17, animate: true, duration: 0.7 });
    }
  }

  // Alias for semantic clarity
  const drawRouteLine = drawGlowingMintRoute;

  function clearRouteVisuals() {
    state.layers.pathOuter.clearLayers();
    state.layers.pathMid.clearLayers();
    state.layers.pathCore.clearLayers();
    state.layers.stepExploration.clearLayers();
    state.layers.stepCurrentMarker.clearLayers();
    const detailCard = document.getElementById('floating-detail-card');
    if (detailCard) detailCard.classList.add('hidden');
  }

  // =========================================================================
  // 8. RENDER GRAPH ON MAP (SUBTLE EDGES & CIRCULAR AVATAR MARKERS)
  // =========================================================================
  function renderGraphOnMap() {
    if (!state.map) return;

    state.layers.edges.clearLayers();
    state.layers.markers.clearLayers();
    state.layers.stepExploration.clearLayers();
    state.layers.stepCurrentMarker.clearLayers();
    state.markerMap.clear();

    const nodes = state.graph.nodes || [];
    const edges = state.graph.edges || [];

    // Rebuild nodeMap
    state.nodeMap.clear();
    nodes.forEach(n => state.nodeMap.set(n.id, n));

    // 1. Draw Subtle Edges (with Coastal NH16 Geometry where applicable)
    edges.forEach(edge => {
      const u = state.nodeMap.get(edge.source);
      const v = state.nodeMap.get(edge.target);
      if (!u || !v) return;

      const latlngs = getEdgeLatLngs(edge.source, edge.target, [u.lat, u.lng], [v.lat, v.lng]);

      let edgeColor = state.showEdgesProminent ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.04)';
      let weight = 2.0;
      let dashArray = null;
      let opacity = 0.8;

      if (edge.is_blocked) {
        edgeColor = 'rgba(244, 63, 94, 0.65)';
        weight = 2.5;
        dashArray = '4, 8';
        opacity = 0.95;
      }

      // Invisible wide hit-area
      const hitLine = L.polyline(latlngs, {
        color: 'transparent',
        weight: 16,
        opacity: 0,
        interactive: true
      });

      const line = L.polyline(latlngs, {
        color: edgeColor,
        weight: weight,
        opacity: opacity,
        dashArray: dashArray,
        lineCap: 'round',
        lineJoin: 'round'
      });

      const openInspector = () => openEdgeModal(edge, u, v);
      hitLine.on('click', openInspector);
      line.on('click', openInspector);

      const timeStr = edge.estimated_time_min ? `${Math.round(edge.estimated_time_min)} min` : '';
      hitLine.bindTooltip(`
        <div class="edge-hover-popup">
          <div class="edge-hover-title">${escapeHtml(edge.road_name || 'Corridor')}</div>
          <div class="edge-hover-sub">${edge.base_distance_km} km ${timeStr ? '• ' + timeStr : ''}</div>
          <div class="edge-hover-traffic">Traffic: <strong>${edge.is_blocked ? 'BLOCKED' : (edge.traffic_multiplier || 1.0) + 'x'}</strong></div>
        </div>
      `, { sticky: true, opacity: 1, className: 'navgraph-dark-tooltip edge-dark-tooltip' });

      state.layers.edges.addLayer(line);
      state.layers.edges.addLayer(hitLine);
    });

    // 2. Draw Circular Avatar Markers Matching frame_0.jpg
    const query = (state.searchQuery || '').trim().toLowerCase();

    nodes.forEach(node => {
      const isOrigin = state.selectedSource === node.id;
      const isTarget = state.selectedTarget === node.id;
      const isWaypoint = state.waypoints.includes(node.id);
      const isActive = isOrigin || isTarget || isWaypoint;

      const matchesQuery = !query ||
        (node.name || '').toLowerCase().includes(query) ||
        (node.category || '').toLowerCase().includes(query) ||
        (node.id || '').toLowerCase().includes(query) ||
        (node.description || '').toLowerCase().includes(query);

      const style = getNodeStyle(node);

      let shortLabel = style.pillText;
      if (isOrigin) shortLabel = 'Origin';
      else if (isTarget && state.routeResult) {
        shortLabel = `${state.routeResult.total_distance_km} km`;
      }

      const dimStyle = matchesQuery ? '' : 'opacity: 0.22; filter: grayscale(80%);';

      const icon = L.divIcon({
        className: 'custom-outlet-marker',
        html: `
          <div class="outlet-marker-wrapper ${isActive ? 'active' : ''}" style="${dimStyle}">
            <div class="outlet-marker-circle" style="background-color:${style.color}; color:${style.textColor};">
              <i class="fa-solid ${style.icon}"></i>
            </div>
            <div class="outlet-marker-pill ${isActive ? 'active-pill' : 'inactive-pill'}">
              ${escapeHtml(shortLabel)}
            </div>
          </div>
        `,
        iconSize: [44, 44],
        iconAnchor: [22, 22]
      });

      const marker = L.marker([node.lat, node.lng], {
        icon,
        interactive: true,
        opacity: matchesQuery ? 1.0 : 0.35,
        zIndexOffset: isActive ? 1000 : (matchesQuery ? 100 : 10)
      });

      // Rich hover popup above every marker on the map
      const roleTag = isOrigin ? '<span class="tt-role origin">Origin</span>' : (isTarget ? '<span class="tt-role dest">Destination</span>' : '');
      const rawCat = (node.category || 'node');
      const catFormatted = rawCat.charAt(0).toUpperCase() + rawCat.slice(1).toLowerCase();
      const tooltipHtml = `
        <div class="node-hover-popup">
          <div class="node-hover-header">
            <span class="node-hover-title">${escapeHtml(node.name)}</span>
            ${roleTag}
          </div>
          <div class="node-hover-meta">
            <span class="node-hover-cat">${escapeHtml(catFormatted)}</span>
            <span class="node-hover-coords">${node.lat.toFixed(4)}°N, ${node.lng.toFixed(4)}°E</span>
          </div>
          ${node.description ? `<div class="node-hover-desc">${escapeHtml(node.description)}</div>` : ''}
        </div>
      `;
      marker.bindTooltip(tooltipHtml, {
        direction: 'top',
        offset: [0, -26],
        opacity: 1,
        className: 'navgraph-dark-tooltip',
        sticky: false
      });

      marker.on('mouseover', () => {
        const el = marker.getElement();
        if (el) el.classList.add('marker-hover-active');
      });
      marker.on('mouseout', () => {
        const el = marker.getElement();
        if (el) el.classList.remove('marker-hover-active');
      });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        handleNodeClick(node);
      });

      state.layers.markers.addLayer(marker);
      state.markerMap.set(node.id, marker);
    });
  }

  function fitGraphBounds() {
    if (!state.map || !state.graph.nodes || state.graph.nodes.length === 0) return;
    const bounds = L.latLngBounds(state.graph.nodes.map(n => [n.lat, n.lng]));
    state.map.fitBounds(bounds, { padding: [60, 60], maxZoom: 17, animate: true, duration: 0.8 });
  }

  // =========================================================================
  // 9. INTERACTIVE SIDEBAR LOCATION LIST (THE STAR OF THE SIDEBAR)
  // =========================================================================
  function renderSidebarLocationList() {
    const container = document.getElementById('locations-list-container');
    const countLabel = document.getElementById('locations-count-label');
    if (!container) return;

    container.innerHTML = '';
    const nodes = state.graph.nodes || [];
    const query = (state.searchQuery || '').trim().toLowerCase();

    // Filter nodes by query and exclude or separate origin
    const filteredNodes = nodes.filter(node => {
      if (!query) return true;
      const matchName = (node.name || '').toLowerCase().includes(query);
      const matchCat = (node.category || '').toLowerCase().includes(query);
      const matchDesc = (node.description || '').toLowerCase().includes(query);
      return matchName || matchCat || matchDesc;
    });

    if (countLabel) {
      countLabel.textContent = `Destinations (${filteredNodes.length})`;
    }

    if (filteredNodes.length === 0) {
      container.innerHTML = '<div class="empty-state" style="padding:20px; text-align:center;">No locations match your search.</div>';
      return;
    }

    filteredNodes.forEach(node => {
      const isSelected = state.selectedTarget === node.id;
      const isOrigin = state.selectedSource === node.id;
      const style = getNodeStyle(node);

      // Distance estimation or optimal route info
      const origNode = state.nodeMap.get(state.selectedSource);
      let distText = '--';
      let estMin = 3;
      if (origNode) {
        const direct = haversineDistanceKm(origNode.lat, origNode.lng, node.lat, node.lng);
        distText = direct < 1 ? direct.toFixed(2) : direct.toFixed(1);
        estMin = Math.round(direct * 2.5) || 1;
      }

      let statusText = '~' + estMin + ' min est.';
      let isOptimal = false;

      if (isOrigin) {
        distText = '0.0';
        statusText = 'Origin point';
        isOptimal = false;
      } else if (isSelected && state.routeResult) {
        distText = String(state.routeResult.total_distance_km);
        statusText = 'Selected · ~' + Math.round(state.routeResult.estimated_time_min) + ' min';
        isOptimal = true;
      } else {
        statusText = '~' + estMin + ' min est.';
        isOptimal = false;
      }

      const degree = Array.isArray(state.graph.adjacency_list?.[node.id])
        ? state.graph.adjacency_list[node.id].length
        : (state.graph.edges || []).filter(e => e.source === node.id || e.target === node.id).length;

      const row = document.createElement('div');
      row.className = `location-row location-card ${isSelected ? 'selected' : ''}`;
      row.dataset.id = node.id;

      row.innerHTML = `
        <div class="loc-avatar" style="background-color:${style.color}; color:${style.textColor};">
          <i class="fa-solid ${style.icon}"></i>
        </div>
        <div class="loc-info">
          <div class="loc-name">${escapeHtml(node.name)}</div>
          <div class="loc-sub">
            <span class="loc-dist">${distText} km</span>
            <span class="loc-bullet">•</span>
            <span class="loc-status ${isOptimal ? 'mint' : ''}">${statusText}</span>
          </div>
        </div>
        <div class="loc-badges font-mono" title="Connected edges (vertex degree)">
          <span>${degree}e</span>
        </div>
      `;

      // Sidebar Card Hover Sync with Leaflet Map Marker & Rich Popup
      row.addEventListener('mouseenter', () => {
        const marker = state.markerMap.get(node.id);
        if (marker) {
          marker.openTooltip();
          const el = marker.getElement();
          if (el) el.classList.add('marker-hover-active');
        }
      });

      row.addEventListener('mouseleave', () => {
        const marker = state.markerMap.get(node.id);
        if (marker) {
          marker.closeTooltip();
          const el = marker.getElement();
          if (el) el.classList.remove('marker-hover-active');
        }
      });

      row.addEventListener('click', () => {
        if (!state.selectedSource) {
          setOrigin(node.id);
          showToast(`Set ${node.name} as Origin.`, 'info');
          return;
        }
        if (node.id === state.selectedSource) {
          showToast(`${node.name} is currently selected as your Origin.`, 'info');
          return;
        }
        setDestination(node.id, true);
      });

      container.appendChild(row);
    });
  }

  // Aliases for accessibility and programmatic dispatch
  function renderLocationCardsList() {
    return renderSidebarLocationList();
  }
  function selectLocationCard(nodeId) {
    if (!state.selectedSource) {
      setOrigin(nodeId);
    } else {
      setDestination(nodeId, true);
    }
  }

  // =========================================================================
  // 10. FLOATING DETAIL CARD (MATCHING "ADIDAS" IN frame_0.jpg)
  // =========================================================================
  function updateFloatingDetailCard(result) {
    const card = document.getElementById('floating-detail-card');
    if (!card) return;

    if (!result || !result.found || !state.selectedTarget) {
      card.classList.add('hidden');
      return;
    }

    const targetNode = state.nodeMap.get(state.selectedTarget);
    if (!targetNode) return;

    const style = getNodeStyle(targetNode);
    const sourceNode = state.nodeMap.get(state.selectedSource);
    const algoName = result.algorithm_name || state.selectedAlgorithm;

    // Avatar
    const avatarEl = document.getElementById('detail-card-avatar');
    if (avatarEl) {
      avatarEl.style.backgroundColor = style.color;
      avatarEl.style.color = style.textColor;
      avatarEl.innerHTML = `<i class="fa-solid ${style.icon}"></i>`;
    }

    // Titles
    document.getElementById('detail-card-title').textContent = targetNode.name;
    document.getElementById('detail-card-dist').textContent = `${result.total_distance_km} km`;
    document.getElementById('detail-card-time').textContent = `~${Math.round(result.estimated_time_min)} min via ${algoName}`;

    // Stats Pill Bar (3 items)
    document.getElementById('detail-stat-optimal').textContent = `${result.hop_count} Hops`;
    document.getElementById('detail-stat-time').textContent = `~${Math.round(result.estimated_time_min)} min`;
    document.getElementById('detail-stat-explored').textContent = `${result.nodes_explored} Explored`;

    // Headline
    const headlineEl = document.getElementById('detail-card-headline');
    const roadNames = (result.directions || []).map(d => d.road_name).filter(Boolean);
    const topRoad = roadNames.length > 0 ? roadNames[0] : 'Academic Spine';
    headlineEl.textContent = `Optimal Shortest Path via ${topRoad}`;

    // Description bullet
    const descEl = document.getElementById('detail-card-desc');
    let summaryText = targetNode.description || `Connecting ${sourceNode ? sourceNode.name : 'Origin'} to ${targetNode.name}.`;
    if (result.path && result.path.length > 1) {
      const pathNames = result.path.map(id => state.nodeMap.get(id)?.name || id);
      summaryText += ` Route: ${pathNames.join(' → ')}.`;
    }
    descEl.textContent = summaryText;

    card.classList.remove('hidden');
  }

  // =========================================================================
  // 11. ROUTE COMPUTATION & ORCHESTRATION
  // =========================================================================
  async function computeRoute(autoFit = true) {
    const source = state.selectedSource;
    const target = state.selectedTarget;

    if (!source || !target) return;
    if (source === target) {
      showToast('Origin and Destination must be distinct vertices', 'warning');
      return;
    }

    const payload = {
      source,
      target,
      waypoints: state.waypoints.filter(w => !!w),
      algorithm: state.selectedAlgorithm,
      weight_mode: state.weightMode,
      preset: state.activePreset
    };

    try {
      const result = await API.computeRoute(payload);
      state.routeResult = result;

      if (!result.found) {
        showToast(
          `No viable path found between nodes using ${result.algorithm_name || 'selected algorithm'}. Road closures may have partitioned the graph.`,
          'error',
          'Path Blocked / Disconnected'
        );
        clearRouteVisuals();
        renderSidebarLocationList();
        renderGraphOnMap();
        return;
      }

      // 1. Update Map Markers & Sidebar List FIRST
      renderGraphOnMap();
      renderSidebarLocationList();

      // 2. Draw glowing mint route on map AFTER renderGraphOnMap()
      drawGlowingMintRoute(result.path_coordinates);

      // 3. Update Floating Detail Card
      updateFloatingDetailCard(result);

      // 4. Update Step Player & Directions Drawer
      if (result.steps && result.steps.length > 0) {
        initStepPlayer(result.steps, result.algorithm_name);
      }

      // Explicitly clear step exploration layers unless the DSA player drawer is actively open
      const playerDrawer = document.getElementById('dsa-player-drawer');
      const isPlayerDrawerOpen = playerDrawer && playerDrawer.classList.contains('open');
      if (!isPlayerDrawerOpen && !state.stepPlayer.isPlaying) {
        state.layers.stepExploration.clearLayers();
        state.layers.stepCurrentMarker.clearLayers();
      }

      populateDirectionsList(result);

    } catch (err) {
      showToast(`Route computation failed: ${err.message}`, 'error');
    }
  }

  function setOrigin(nodeId) {
    if (!nodeId || nodeId === state.selectedSource) return;
    state.selectedSource = nodeId;

    const select = document.getElementById('select-origin-node');
    if (select) select.value = nodeId;

    if (state.selectedTarget === nodeId) {
      // Pick another node for destination
      const other = state.graph.nodes.find(n => n.id !== nodeId);
      state.selectedTarget = other ? other.id : null;
    }

    renderGraphOnMap();
    renderSidebarLocationList();

    if (state.selectedTarget) {
      computeRoute();
    }
  }

  function setDestination(nodeId, triggerRoute = true) {
    if (!nodeId) return;
    state.selectedTarget = nodeId;

    renderGraphOnMap();
    renderSidebarLocationList();

    if (triggerRoute && state.selectedSource) {
      computeRoute();
    }
  }

  function handleNodeClick(node) {
    if (state.pickingMode === 'source') {
      setOrigin(node.id);
      exitPickingMode();
      showToast(`Selected origin: ${node.name}`, 'success');
      return;
    }
    if (state.pickingMode === 'target') {
      setDestination(node.id, true);
      exitPickingMode();
      showToast(`Selected destination: ${node.name}`, 'success');
      return;
    }
    if (state.pickingMode === 'waypoint') {
      if (state.activeWaypointIdx !== null) {
        updateWaypoint(state.activeWaypointIdx, node.id);
      } else {
        addWaypoint(node.id);
      }
      exitPickingMode();
      showToast(`Added waypoint: ${node.name}`, 'info');
      return;
    }

    // Default: clicking node on map sets it as destination and computes route!
    if (node.id === state.selectedSource) {
      showToast(`${node.name} is currently your Origin. Click "Route from" or another node to change.`, 'info');
      return;
    }
    setDestination(node.id, true);
  }

  function handleMapClick(e) {
    if (state.pickingMode === 'map-add-node') {
      document.getElementById('new-node-lat').value = e.latlng.lat.toFixed(5);
      document.getElementById('new-node-lng').value = e.latlng.lng.toFixed(5);
      exitPickingMode();
      showToast(`Captured GPS: ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`, 'info');
      openToolsDrawer();
      document.getElementById('new-node-name').focus();
    }
  }

  function startPickingMode(mode, waypointIdx = null) {
    state.pickingMode = mode;
    state.activeWaypointIdx = waypointIdx;

    const banner = document.getElementById('map-interaction-banner');
    const textEl = document.getElementById('map-interaction-text');

    let prompt = 'Click any node on the map';
    if (mode === 'source') prompt = 'Click a node on map to set ORIGIN';
    if (mode === 'target') prompt = 'Click a node on map to set DESTINATION';
    if (mode === 'waypoint') prompt = 'Click a node on map to set WAYPOINT';
    if (mode === 'map-add-node') prompt = 'Click anywhere on map to capture GPS Coordinates';

    textEl.textContent = prompt;
    banner.classList.remove('hidden');
  }

  function exitPickingMode() {
    state.pickingMode = null;
    state.activeWaypointIdx = null;
    document.getElementById('map-interaction-banner').classList.add('hidden');
  }

  // =========================================================================
  // 12. STEP-BY-STEP DSA TRAVERSAL PLAYER
  // =========================================================================
  function initStepPlayer(steps, algoName) {
    state.stepPlayer.steps = steps;
    state.stepPlayer.currentIndex = 0;
    state.stepPlayer.isPlaying = false;
    clearInterval(state.stepPlayer.intervalId);

    const badge = document.getElementById('player-algo-badge');
    if (badge) badge.textContent = `${algoName || 'Algorithm'} Exploration`;
    updatePlayerUI();

    // Never render Step 0 on map automatically unless the player drawer is explicitly open
    const playerDrawer = document.getElementById('dsa-player-drawer');
    const isPlayerDrawerOpen = playerDrawer && playerDrawer.classList.contains('open');
    if (!isPlayerDrawerOpen && !state.stepPlayer.isPlaying) {
      state.layers.stepExploration.clearLayers();
      state.layers.stepCurrentMarker.clearLayers();
    }
  }

  function resetStepPlayer() {
    state.stepPlayer.steps = [];
    state.stepPlayer.currentIndex = 0;
    state.stepPlayer.isPlaying = false;
    clearInterval(state.stepPlayer.intervalId);

    document.getElementById('step-counter').textContent = 'Step 0 / 0';
    document.getElementById('step-action-badge').textContent = 'READY';
    document.getElementById('step-action-badge').className = 'badge badge-muted';
    document.getElementById('step-node-badge').textContent = '--';
    document.getElementById('step-narration').textContent = 'Run a route to record algorithm execution steps.';
    document.getElementById('step-progress-bar').style.width = '0%';
    document.getElementById('btn-player-play').innerHTML = '<i class="fa-solid fa-play"></i>';

    document.getElementById('frontier-container').innerHTML = '<div class="empty-state">No active frontier. Route to inspect.</div>';
    document.getElementById('visited-container').innerHTML = '<div class="empty-state">No nodes visited yet.</div>';
    document.getElementById('distances-table-container').innerHTML = '<div class="empty-state">Distances will update at each edge relaxation step.</div>';

    state.layers.stepExploration.clearLayers();
    state.layers.stepCurrentMarker.clearLayers();
  }

  function updatePlayerUI() {
    const steps = state.stepPlayer.steps;
    if (!steps || steps.length === 0) return;

    const idx = state.stepPlayer.currentIndex;
    const step = steps[idx];
    if (!step) return;

    // Step counter & progress
    document.getElementById('step-counter').textContent = `Step ${idx + 1} / ${steps.length}`;
    const progressPercent = steps.length > 1 ? (idx / (steps.length - 1)) * 100 : 100;
    document.getElementById('step-progress-bar').style.width = `${progressPercent}%`;

    // Action Badge
    const actionBadge = document.getElementById('step-action-badge');
    actionBadge.textContent = step.action || 'STEP';
    if (step.action === 'VISIT' || step.action === 'EXTRACT_MIN' || step.action === 'POP_QUEUE') {
      actionBadge.className = 'badge badge-cyan';
    } else if (step.action === 'RELAX' || step.action === 'UPDATE_DISTANCE') {
      actionBadge.className = 'badge badge-amber';
    } else if (step.action === 'TARGET_REACHED' || step.action === 'FINISH') {
      actionBadge.className = 'badge badge-mint';
    } else {
      actionBadge.className = 'badge badge-muted';
    }

    document.getElementById('step-node-badge').textContent = step.current_node_name || step.current_node || '--';
    document.getElementById('step-narration').textContent = step.message || 'Processing algorithm step...';

    // 1. Live Frontier / Min-Heap Inspector
    const frontierContainer = document.getElementById('frontier-container');
    frontierContainer.innerHTML = '';
    const frontierItems = step.frontier || [];
    document.getElementById('frontier-count-badge').textContent = `${frontierItems.length} items`;

    if (frontierItems.length === 0) {
      frontierContainer.innerHTML = '<div class="empty-state">Frontier queue is currently empty.</div>';
    } else {
      frontierItems.forEach(item => {
        const chip = document.createElement('div');
        chip.className = 'frontier-chip';
        const itemNodeId = item.item || item.node || (typeof item === 'string' ? item : '');
        const nodeObj = state.nodeMap.get(itemNodeId);
        const displayName = item.node_name || (nodeObj ? nodeObj.name : itemNodeId);
        const isCurrent = itemNodeId === step.current_node;
        if (isCurrent) chip.classList.add('active-extracted');

        const priorityLabel = item.priority !== undefined
          ? `${typeof item.priority === 'number' ? item.priority.toFixed(1) : item.priority}`
          : (item.cost !== undefined ? item.cost : '');

        chip.innerHTML = `
          <span>${escapeHtml(displayName)}</span>
          <span class="font-mono text-cyan">${priorityLabel}</span>
        `;
        frontierContainer.appendChild(chip);
      });
    }

    // 2. Visited Closed Set
    const visitedContainer = document.getElementById('visited-container');
    visitedContainer.innerHTML = '';
    const visitedNodes = step.visited_nodes || [];
    document.getElementById('visited-count-badge').textContent = `${visitedNodes.length} visited`;

    if (visitedNodes.length === 0) {
      visitedContainer.innerHTML = '<div class="empty-state">No vertices added to closed set yet.</div>';
    } else {
      visitedNodes.forEach((nodeId, vIdx) => {
        const nodeObj = state.nodeMap.get(nodeId);
        const name = nodeObj ? nodeObj.name : nodeId;
        const chip = document.createElement('div');
        chip.className = 'visited-chip';
        chip.innerHTML = `
          <span class="visited-idx">#${vIdx + 1}</span>
          <span>${escapeHtml(name)}</span>
        `;
        visitedContainer.appendChild(chip);
      });
    }

    // 3. Relaxation Distance Table
    const distContainer = document.getElementById('distances-table-container');
    distContainer.innerHTML = '';
    if (step.distances && Object.keys(step.distances).length > 0) {
      let tableHtml = `
        <table class="mini-table font-mono">
          <thead>
            <tr><th>Vertex</th><th>Distance / Cost</th></tr>
          </thead>
          <tbody>
      `;
      for (const [nId, distVal] of Object.entries(step.distances)) {
        const nodeObj = state.nodeMap.get(nId);
        const name = nodeObj ? nodeObj.name : nId;
        const isCur = nId === step.current_node;
        tableHtml += `
          <tr style="${isCur ? 'background:rgba(6,182,212,0.18); font-weight:bold;' : ''}">
            <td>${escapeHtml(name)}</td>
            <td class="text-cyan">${distVal === Infinity ? '&infin;' : distVal.toFixed(1)}</td>
          </tr>
        `;
      }
      tableHtml += '</tbody></table>';
      distContainer.innerHTML = tableHtml;
    } else {
      distContainer.innerHTML = '<div class="empty-state">No distance relaxations recorded for this step.</div>';
    }

    // 4. Render Step Highlight on Map (only when player drawer is open or playing)
    const playerDrawer = document.getElementById('dsa-player-drawer');
    const isPlayerVisible = playerDrawer && playerDrawer.classList.contains('open');
    if (isPlayerVisible || state.stepPlayer.isPlaying) {
      renderStepOnMap(step);
    } else {
      state.layers.stepExploration.clearLayers();
      state.layers.stepCurrentMarker.clearLayers();
    }
  }

  function renderStepOnMap(step) {
    state.layers.stepExploration.clearLayers();
    state.layers.stepCurrentMarker.clearLayers();

    // Explored edges in glowing cyan (with Coastal NH16 Geometry where applicable)
    if (step.explored_edges && step.explored_edges.length > 0) {
      step.explored_edges.forEach(edge => {
        const u = state.nodeMap.get(edge[0]);
        const v = state.nodeMap.get(edge[1]);
        if (!u || !v) return;

        const segLatLngs = getEdgeLatLngs(edge[0], edge[1], [u.lat, u.lng], [v.lat, v.lng]);
        const line = L.polyline(segLatLngs, {
          color: '#06b6d4',
          weight: 4,
          opacity: 0.85,
          lineCap: 'round'
        });
        state.layers.stepExploration.addLayer(line);
      });
    }

    // Highlight current node with glowing pulse
    if (step.current_node) {
      const cur = state.nodeMap.get(step.current_node);
      if (cur) {
        const curMarker = L.circleMarker([cur.lat, cur.lng], {
          radius: 18,
          color: '#06b6d4',
          fillColor: '#06b6d4',
          fillOpacity: 0.35,
          weight: 3
        });
        state.layers.stepCurrentMarker.addLayer(curMarker);
      }
    }
  }

  function playStepPlayer() {
    if (state.stepPlayer.steps.length === 0) return;
    state.stepPlayer.isPlaying = true;
    document.getElementById('btn-player-play').innerHTML = '<i class="fa-solid fa-pause"></i>';

    clearInterval(state.stepPlayer.intervalId);
    state.stepPlayer.intervalId = setInterval(() => {
      if (state.stepPlayer.currentIndex < state.stepPlayer.steps.length - 1) {
        state.stepPlayer.currentIndex++;
        updatePlayerUI();
      } else {
        pauseStepPlayer();
      }
    }, state.stepPlayer.speedMs);
  }

  function pauseStepPlayer() {
    state.stepPlayer.isPlaying = false;
    clearInterval(state.stepPlayer.intervalId);
    document.getElementById('btn-player-play').innerHTML = '<i class="fa-solid fa-play"></i>';
  }

  function stepNext() {
    pauseStepPlayer();
    if (state.stepPlayer.currentIndex < state.stepPlayer.steps.length - 1) {
      state.stepPlayer.currentIndex++;
      updatePlayerUI();
    }
  }

  function stepPrev() {
    pauseStepPlayer();
    if (state.stepPlayer.currentIndex > 0) {
      state.stepPlayer.currentIndex--;
      updatePlayerUI();
    }
  }

  function stepReset() {
    pauseStepPlayer();
    state.stepPlayer.currentIndex = 0;
    updatePlayerUI();
  }

  function stepEnd() {
    pauseStepPlayer();
    if (state.stepPlayer.steps.length > 0) {
      state.stepPlayer.currentIndex = state.stepPlayer.steps.length - 1;
      updatePlayerUI();
    }
  }

  function populateDirectionsList(result) {
    const list = document.getElementById('directions-list');
    const countBadge = document.getElementById('directions-count');
    if (!list) return;

    list.innerHTML = '';
    const directions = result.directions || [];
    if (countBadge) countBadge.textContent = `${directions.length} legs`;

    // Complexity
    if (result.complexity) {
      document.getElementById('metric-time-complexity').textContent = result.complexity.time || 'O((V+E) log V)';
      document.getElementById('metric-space-complexity').textContent = result.complexity.space || 'O(V)';
    }
    document.getElementById('metric-hops').textContent = `${result.hop_count} hops`;

    if (directions.length === 0) {
      list.innerHTML = '<div class="empty-state">Source and destination are adjacent or identical.</div>';
      return;
    }

    directions.forEach(step => {
      const card = document.createElement('div');
      card.className = 'direction-step-card';

      let trafficPill = '';
      const mult = step.traffic_multiplier || 1.0;
      if (mult >= 1.6) {
        trafficPill = `<span class="traffic-pill heavy">${mult.toFixed(1)}x Heavy</span>`;
      } else if (mult > 1.0) {
        trafficPill = `<span class="traffic-pill moderate">${mult.toFixed(1)}x Traffic</span>`;
      } else {
        trafficPill = `<span class="traffic-pill clear">1.0x Flow</span>`;
      }

      card.innerHTML = `
        <div class="step-number-badge">${step.step}</div>
        <div class="direction-details flex-1">
          <div class="direction-instruction">${escapeHtml(step.instruction || `Head from ${step.from_name} to ${step.to_name}`)}</div>
          <div class="direction-meta">
            <span><i class="fa-solid fa-road text-cyan"></i> ${escapeHtml(step.road_name || 'Corridor')}</span>
            <span><i class="fa-solid fa-ruler"></i> ${step.distance_km} km</span>
            <span><i class="fa-solid fa-clock"></i> ~${Math.round(step.estimated_time_min)} min</span>
            ${trafficPill}
          </div>
        </div>
      `;
      list.appendChild(card);
    });
  }

  // =========================================================================
  // 13. ALGORITHM BENCHMARK & COMPARISON MODAL
  // =========================================================================
  async function compareAlgorithms() {
    const source = state.selectedSource;
    const target = state.selectedTarget;

    if (!source || !target) {
      showToast('Please select both Origin and Destination first', 'warning');
      return;
    }

    const payload = {
      source,
      target,
      waypoints: state.waypoints.filter(w => !!w),
      weight_mode: state.weightMode,
      preset: state.activePreset
    };

    openModal('modal-compare');
    const tbody = document.getElementById('comparison-tbody');
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:20px;"><i class="fa-solid fa-spinner fa-spin"></i> Running benchmark across Dijkstra, A*, BFS, and DFS...</td></tr>';

    try {
      const res = await API.compareAlgorithms(payload);
      state.comparisonResult = res;

      // Update DSA Analysis Text
      const analysisEl = document.getElementById('comparison-analysis-text');
      if (analysisEl && res.analysis) {
        if (Array.isArray(res.analysis) && res.analysis.length > 0) {
          analysisEl.innerHTML = `<ul style="margin: 0; padding-left: 18px; line-height: 1.6;">` +
            res.analysis.map(pt => `<li>${escapeHtml(pt)}</li>`).join('') +
            `</ul>`;
        } else if (typeof res.analysis === 'string') {
          analysisEl.textContent = res.analysis;
        } else if (res.analysis?.summary) {
          analysisEl.innerHTML = `<strong>Primary Finding:</strong> ${escapeHtml(res.analysis.summary)}`;
        } else {
          analysisEl.textContent = 'Benchmark execution completed across all pathfinding algorithms.';
        }
      }

      tbody.innerHTML = '';
      const rows = Array.isArray(res.comparison_table) && res.comparison_table.length > 0
        ? res.comparison_table
        : ['dijkstra', 'astar', 'bfs', 'dfs'].map(k => res.results?.[k]).filter(Boolean);

      rows.forEach(row => {
        const tr = document.createElement('tr');
        const algoKey = row.algorithm || row.key || '';
        const algoLabel = row.algorithm_name || row.label || algoKey.toUpperCase();
        const found = row.found !== false;

        const isOpt = row.is_optimal_cost ?? row.is_optimal ?? false;
        const optBadge = isOpt
          ? '<span class="badge badge-mint">Optimal Cost</span>'
          : (algoKey === 'bfs' || row.is_fewest_hops ? '<span class="badge badge-cyan">Min Hops</span>' : '<span class="badge badge-muted">Unweighted</span>');

        const distVal = row.total_distance_km ?? row.distance_km;
        const distStr = found && distVal !== undefined ? `${typeof distVal === 'number' ? distVal.toFixed(2) : distVal} km` : 'N/A';
        const costVal = row.effective_cost ?? row.total_cost;
        const costStr = found && costVal !== undefined ? (typeof costVal === 'number' ? costVal.toFixed(1) : costVal) : 'N/A';
        const timeVal = row.estimated_time_min;
        const timeStr = found && timeVal !== undefined ? `~${Math.round(timeVal)} min` : 'N/A';
        const hopsVal = row.hop_count ?? row.hops;
        const hopsStr = found && hopsVal !== undefined ? hopsVal : 'N/A';
        const nodesExplored = row.nodes_explored ?? row.visited_count ?? '--';
        const peakFrontier = row.frontier_peak_size ?? '--';
        const execMs = row.execution_time_ms !== undefined ? `${Number(row.execution_time_ms).toFixed(2)} ms` : '--';
        const timeComplexity = row.complexity_time || row.complexity?.time || 'O((V+E)logV)';

        tr.innerHTML = `
          <td><strong>${escapeHtml(algoLabel)}</strong></td>
          <td class="font-mono">${distStr}</td>
          <td class="font-mono text-mint">${costStr}</td>
          <td class="font-mono">${timeStr}</td>
          <td class="font-mono">${hopsStr}</td>
          <td class="font-mono text-cyan">${nodesExplored}</td>
          <td class="font-mono">${peakFrontier}</td>
          <td class="font-mono">${execMs}</td>
          <td><code>${escapeHtml(timeComplexity)}</code></td>
          <td>${optBadge}</td>
        `;
        tbody.appendChild(tr);
      });

      showToast('Algorithm benchmark completed successfully', 'success');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="10" style="color:var(--accent-rose); padding:20px;">Benchmark failed: ${escapeHtml(err.message)}</td></tr>`;
      showToast(`Comparison failed: ${err.message}`, 'error');
    }
  }

  // =========================================================================
  // 14. PRESET & GRAPH LOADERS
  // =========================================================================
  async function loadPreset(presetId) {
    try {
      showToast(`Loading preset '${presetId}'...`, 'info');
      const res = await API.loadPreset(presetId);
      state.activePreset = presetId;

      // Update preset dropdown if different
      const presetSelect = document.getElementById('preset-select');
      if (presetSelect && presetSelect.value !== presetId) {
        presetSelect.value = presetId;
      }

      await refreshGraphData();

      // Configure default origin & destination
      if (presetId === 'campus_navigator') {
        state.selectedSource = 'main_gate';
        state.selectedTarget = 'metro_gate';
      } else {
        state.selectedSource = 'delhi';
        state.selectedTarget = 'bengaluru';
      }

      populateOriginDropdown();
      populateEdgeVertexDropdowns();
      fitGraphBounds();

      // Automatically compute initial route
      await computeRoute();

      showToast(`Loaded preset: ${presetId.replace('_', ' ')}`, 'success');
    } catch (err) {
      showToast(`Failed to load preset: ${err.message}`, 'error');
    }
  }

  async function refreshGraphData() {
    try {
      const res = await API.getGraph(state.activePreset);
      const graphData = (res && res.graph) ? res.graph : res;
      state.graph = {
        nodes: Array.isArray(graphData?.nodes) ? graphData.nodes : [],
        edges: Array.isArray(graphData?.edges) ? graphData.edges : [],
        adjacency_list: graphData?.adjacency_list || {},
        stats: graphData?.stats || {}
      };
      if (res && res.active_preset) {
        state.activePreset = res.active_preset;
        const presetSel = document.getElementById('preset-select');
        if (presetSel) presetSel.value = res.active_preset;
      }
      state.nodeMap.clear();
      (state.graph.nodes || []).forEach(n => state.nodeMap.set(n.id, n));

      renderGraphOnMap();
      renderSidebarLocationList();
      populateOriginDropdown();
      populateEdgeVertexDropdowns();
    } catch (err) {
      showToast(`Failed to fetch graph topology: ${err.message}`, 'error');
    }
  }

  function populateOriginDropdown() {
    const select = document.getElementById('select-origin-node');
    if (!select) return;

    select.innerHTML = '';
    const nodes = state.graph.nodes || [];

    nodes.forEach(node => {
      const opt = document.createElement('option');
      opt.value = node.id;
      opt.textContent = node.name;
      if (node.id === state.selectedSource) opt.selected = true;
      select.appendChild(opt);
    });
  }

  function populateEdgeVertexDropdowns() {
    const edgeSrc = document.getElementById('edge-source');
    const edgeTgt = document.getElementById('edge-target');
    if (!edgeSrc || !edgeTgt) return;

    const buildOptions = () => {
      let html = '<option value="">-- Choose Vertex --</option>';
      (state.graph.nodes || []).forEach(n => {
        html += `<option value="${n.id}">${escapeHtml(n.name)}</option>`;
      });
      return html;
    };

    edgeSrc.innerHTML = buildOptions();
    edgeTgt.innerHTML = buildOptions();
  }

  // =========================================================================
  // 15. TRAFFIC SIMULATION & EDGE MODAL
  // =========================================================================
  async function simulateLiveTraffic() {
    try {
      const res = await API.simulateTraffic();
      await refreshGraphData();
      if (state.selectedTarget) {
        await computeRoute();
      }
      const count = res.congested_count ?? res.stats?.congested_edges ?? res.congested_edges_count;
      const msg = res.message || (count !== undefined ? `Traffic updated on ${count} edges` : 'Dynamic traffic simulated');
      showToast(msg, 'warning', 'Traffic Updated');
    } catch (err) {
      showToast(`Simulate traffic failed: ${err.message}`, 'error');
    }
  }

  async function resetTrafficConditions() {
    try {
      await API.resetTraffic();
      await refreshGraphData();
      if (state.selectedTarget) {
        await computeRoute();
      }
      showToast('All traffic multipliers reset back to 1.0x (Clear Flow)', 'success');
    } catch (err) {
      showToast(`Reset traffic failed: ${err.message}`, 'error');
    }
  }

  function openEdgeModal(edge, u, v) {
    state.selectedEdgeForEdit = edge;

    document.getElementById('edge-modal-title').textContent = edge.road_name || 'Corridor';
    document.getElementById('edge-modal-corridor').textContent = `${u.name} ↔ ${v.name}`;
    document.getElementById('edge-modal-from').textContent = u.name;
    document.getElementById('edge-modal-to').textContent = v.name;
    document.getElementById('edge-modal-base-dist').textContent = `${edge.base_distance_km} km`;

    const multEl = document.getElementById('edge-modal-current-mult');
    multEl.textContent = edge.is_blocked ? 'BLOCKED' : `${(edge.traffic_multiplier || 1.0)}x`;
    multEl.className = edge.is_blocked ? 'font-mono text-rose' : 'font-mono text-amber';

    const blockBtn = document.getElementById('btn-toggle-edge-block');
    if (blockBtn) {
      blockBtn.innerHTML = edge.is_blocked
        ? '<i class="fa-solid fa-lock-open"></i> Unblock Road'
        : '<i class="fa-solid fa-ban"></i> Block Road (Closure)';
    }

    openModal('modal-edge-edit');
  }

  async function updateEdgeTrafficLevel(mult, isBlocked) {
    if (!state.selectedEdgeForEdit) return;
    const edge = state.selectedEdgeForEdit;

    const payload = {
      source: edge.source,
      target: edge.target,
      bidirectional: true
    };

    if (mult !== null && mult !== undefined) payload.traffic_multiplier = mult;
    if (isBlocked !== null && isBlocked !== undefined) payload.is_blocked = isBlocked;

    try {
      await API.updateEdgeTraffic(payload);
      closeModal('modal-edge-edit');
      await refreshGraphData();
      if (state.selectedTarget) {
        await computeRoute();
      }
      showToast(`Corridor '${edge.road_name}' updated successfully`, 'success');
    } catch (err) {
      showToast(`Failed to update corridor: ${err.message}`, 'error');
    }
  }

  async function deleteCurrentEdge() {
    if (!state.selectedEdgeForEdit) return;
    const edge = state.selectedEdgeForEdit;

    try {
      await API.deleteEdge(edge.source, edge.target);
      closeModal('modal-edge-edit');
      await refreshGraphData();
      if (state.selectedTarget) {
        await computeRoute();
      }
      showToast(`Removed road between ${edge.source} and ${edge.target}`, 'info');
    } catch (err) {
      showToast(`Delete edge failed: ${err.message}`, 'error');
    }
  }

  // =========================================================================
  // 16. GRAPH EDITOR FORMS (ADD NODE & ADD EDGE)
  // =========================================================================
  async function handleAddNode(e) {
    e.preventDefault();
    const name = document.getElementById('new-node-name').value.trim();
    const lat = parseFloat(document.getElementById('new-node-lat').value);
    const lng = parseFloat(document.getElementById('new-node-lng').value);
    const category = document.getElementById('new-node-category').value;
    const description = document.getElementById('new-node-desc').value.trim();

    if (!name || isNaN(lat) || isNaN(lng)) {
      showToast('Please provide valid name and coordinates', 'warning');
      return;
    }

    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');

    const payload = { id, name, lat, lng, category, description };

    try {
      await API.addNode(payload);
      closeToolsDrawer();
      e.target.reset();
      await refreshGraphData();
      showToast(`Added vertex '${name}' to graph`, 'success');
    } catch (err) {
      showToast(`Failed to add node: ${err.message}`, 'error');
    }
  }

  async function handleAddEdge(e) {
    e.preventDefault();
    const source = document.getElementById('edge-source').value;
    const target = document.getElementById('edge-target').value;
    const road_name = document.getElementById('edge-road-name').value.trim();
    const distInput = document.getElementById('edge-distance').value;
    const traffic_multiplier = parseFloat(document.getElementById('edge-traffic').value);
    const bidirectional = document.getElementById('edge-bidirectional').checked;

    if (!source || !target || source === target) {
      showToast('Select two distinct vertices to connect', 'warning');
      return;
    }

    const payload = {
      source,
      target,
      road_name: road_name || 'Corridor',
      traffic_multiplier: traffic_multiplier || 1.0,
      bidirectional
    };

    if (distInput) {
      payload.base_distance_km = parseFloat(distInput);
    }

    try {
      await API.addEdge(payload);
      closeToolsDrawer();
      e.target.reset();
      await refreshGraphData();
      showToast(`Connected '${road_name || 'Corridor'}'`, 'success');
    } catch (err) {
      showToast(`Failed to connect edge: ${err.message}`, 'error');
    }
  }

  // =========================================================================
  // 17. WAYPOINTS
  // =========================================================================
  function addWaypoint(nodeId = '') {
    if (state.waypoints.length >= 5) {
      showToast('Maximum 5 intermediate stops supported', 'warning');
      return;
    }
    state.waypoints.push(nodeId);
    renderWaypointsList();
  }

  function removeWaypoint(idx) {
    state.waypoints.splice(idx, 1);
    renderWaypointsList();
    if (state.selectedTarget) computeRoute();
  }

  function updateWaypoint(idx, nodeId) {
    state.waypoints[idx] = nodeId;
    renderWaypointsList();
    if (state.selectedTarget) computeRoute();
  }

  function renderWaypointsList() {
    const container = document.getElementById('waypoints-container');
    if (!container) return;
    container.innerHTML = '';

    state.waypoints.forEach((wpId, idx) => {
      const row = document.createElement('div');
      row.className = 'form-row mt-2';

      const select = document.createElement('select');
      select.className = 'form-select text-xs flex-1';
      select.innerHTML = '<option value="">-- Choose Stop --</option>';

      (state.graph.nodes || []).forEach(n => {
        const opt = document.createElement('option');
        opt.value = n.id;
        opt.textContent = n.name;
        if (n.id === wpId) opt.selected = true;
        select.appendChild(opt);
      });

      select.addEventListener('change', (e) => updateWaypoint(idx, e.target.value));

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'btn-circle-icon btn-xs';
      delBtn.innerHTML = '<i class="fa-solid fa-xmark text-rose"></i>';
      delBtn.addEventListener('click', () => removeWaypoint(idx));

      row.appendChild(select);
      row.appendChild(delBtn);
      container.appendChild(row);
    });
  }

  // =========================================================================
  // 18. GRAPH JSON MODAL
  // =========================================================================
  function openGraphJsonModal(viewType = 'view-adj') {
    renderGraphJsonContent(viewType);
    openModal('modal-graph-json');
  }

  function renderGraphJsonContent(viewType) {
    const codeBlock = document.getElementById('graph-json-code');
    let content = '';

    if (viewType === 'view-adj') {
      content = JSON.stringify(state.graph.adjacency_list || {}, null, 2);
    } else if (viewType === 'view-nodes') {
      content = JSON.stringify(state.graph.nodes || [], null, 2);
    } else if (viewType === 'view-edges') {
      content = JSON.stringify(state.graph.edges || [], null, 2);
    } else {
      content = JSON.stringify(state.graph, null, 2);
    }

    codeBlock.textContent = content;

    document.querySelectorAll('.json-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.jsonView === viewType);
    });
  }

  function copyGraphJson() {
    const codeBlock = document.getElementById('graph-json-code');
    if (!codeBlock) return;
    navigator.clipboard.writeText(codeBlock.textContent).then(() => {
      showToast('Copied graph JSON to clipboard', 'success');
    }).catch(() => {
      showToast('Failed to copy to clipboard', 'error');
    });
  }

  // =========================================================================
  // 19. DRAWER & MODAL MANAGEMENT
  // =========================================================================
  function openPlayerDrawer() {
    closeToolsDrawer();
    document.getElementById('dsa-player-drawer')?.classList.add('open');
    updatePlayerUI();
  }

  function closePlayerDrawer() {
    document.getElementById('dsa-player-drawer')?.classList.remove('open');
    state.layers.stepExploration.clearLayers();
    state.layers.stepCurrentMarker.clearLayers();
  }

  function openToolsDrawer() {
    closePlayerDrawer();
    document.getElementById('tools-drawer')?.classList.add('open');
  }

  function closeToolsDrawer() {
    document.getElementById('tools-drawer')?.classList.remove('open');
  }

  function openModal(modalId) {
    document.getElementById(modalId)?.classList.add('open');
  }

  function closeModal(modalId) {
    document.getElementById(modalId)?.classList.remove('open');
  }

  // =========================================================================
  // 20. HEALTH CHECK
  // =========================================================================
  async function performHealthCheck() {
    const badge = document.getElementById('api-status-indicator');
    const textEl = document.getElementById('api-status-text');
    if (!badge || !textEl) return;

    try {
      const res = await API.healthCheck();
      badge.className = 'api-status-pill online';
      textEl.textContent = 'API Online';
    } catch (_) {
      badge.className = 'api-status-pill offline';
      textEl.textContent = 'API Offline';
    }
  }

  // =========================================================================
  // 21. UTILITIES & GEOMETRY
  // =========================================================================
  function haversineDistanceKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // =========================================================================
  // 22. DOM EVENT BINDINGS
  // =========================================================================
  function setupEventListeners() {
    // 1. Sidebar Top Bar
    document.getElementById('btn-sidebar-info')?.addEventListener('click', () => {
      openModal('modal-info');
    });

    // 2. Search Real-time Filter & Clear
    const searchInput = document.getElementById('search-locations-input');
    const clearSearchBtn = document.getElementById('btn-clear-search');

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value || '';
        if (clearSearchBtn) {
          clearSearchBtn.classList.toggle('hidden', state.searchQuery.trim().length === 0);
        }
        renderSidebarLocationList();
        renderGraphOnMap();
      });

      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const query = (state.searchQuery || '').trim().toLowerCase();
          if (query) {
            const firstMatch = (state.graph.nodes || []).find(n =>
              (n.name || '').toLowerCase().includes(query) ||
              (n.category || '').toLowerCase().includes(query) ||
              (n.id || '').toLowerCase().includes(query) ||
              (n.description || '').toLowerCase().includes(query)
            );
            if (firstMatch) {
              if (firstMatch.id === state.selectedSource) {
                showToast(`${firstMatch.name} is currently your Origin.`, 'info');
              } else {
                setDestination(firstMatch.id, true);
              }
              if (state.map) {
                state.map.flyTo([firstMatch.lat, firstMatch.lng], 16, { duration: 0.6 });
              }
            } else {
              showToast(`No locations found matching "${query}"`, 'warning');
            }
          }
        }
      });
    }

    if (clearSearchBtn) {
      clearSearchBtn.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        state.searchQuery = '';
        clearSearchBtn.classList.add('hidden');
        renderSidebarLocationList();
        renderGraphOnMap();
        if (searchInput) searchInput.focus();
      });
    }

    // 3. Theme Switcher & Selectors
    const themeContainer = document.getElementById('theme-picker-container');
    if (themeContainer) {
      themeContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('.theme-dot');
        if (!btn) return;
        const chosenTheme = btn.dataset.theme;
        if (chosenTheme) {
          applyTheme(chosenTheme, true);
          const t = THEMES[chosenTheme];
          showToast(`Theme switched to ${t ? t.name : chosenTheme}`, 'info');
        }
      });
    }

    // 4. Preset & Algorithm Selectors
    document.getElementById('preset-select')?.addEventListener('change', async (e) => {
      await loadPreset(e.target.value);
      fitGraphBounds();
    });

    document.getElementById('algo-select')?.addEventListener('change', (e) => {
      state.selectedAlgorithm = e.target.value;
      if (state.selectedTarget) computeRoute();
    });

    document.getElementById('btn-open-tools-drawer')?.addEventListener('click', () => {
      openToolsDrawer();
    });

    // 4. Origin Selector & Swap
    document.getElementById('select-origin-node')?.addEventListener('change', (e) => {
      setOrigin(e.target.value);
    });

    document.getElementById('btn-swap-origin-dest')?.addEventListener('click', () => {
      const temp = state.selectedSource;
      state.selectedSource = state.selectedTarget;
      state.selectedTarget = temp;
      const select = document.getElementById('select-origin-node');
      if (select) select.value = state.selectedSource;
      renderGraphOnMap();
      renderSidebarLocationList();
      if (state.selectedTarget) computeRoute();
    });

    // 5. Floating Detail Card Actions
    document.getElementById('btn-close-detail-card')?.addEventListener('click', () => {
      document.getElementById('floating-detail-card')?.classList.add('hidden');
    });

    document.getElementById('btn-card-open-player')?.addEventListener('click', () => {
      openPlayerDrawer();
    });

    document.getElementById('btn-card-set-origin')?.addEventListener('click', () => {
      if (state.selectedTarget) {
        setOrigin(state.selectedTarget);
      }
    });

    document.getElementById('btn-card-replay-route')?.addEventListener('click', () => {
      if (state.selectedTarget) {
        computeRoute().then(() => {
          openPlayerDrawer();
          playStepPlayer();
        });
      }
    });

    document.getElementById('btn-card-compare')?.addEventListener('click', () => {
      compareAlgorithms();
    });

    // 6. Map Floating Bar Controls
    document.getElementById('btn-floating-player')?.addEventListener('click', () => {
      const drawer = document.getElementById('dsa-player-drawer');
      if (drawer?.classList.contains('open')) closePlayerDrawer();
      else openPlayerDrawer();
    });

    document.getElementById('btn-floating-compare')?.addEventListener('click', compareAlgorithms);
    document.getElementById('btn-floating-traffic')?.addEventListener('click', simulateLiveTraffic);
    document.getElementById('btn-floating-reset-traffic')?.addEventListener('click', resetTrafficConditions);
    document.getElementById('btn-floating-editor')?.addEventListener('click', () => {
      const drawer = document.getElementById('tools-drawer');
      if (drawer?.classList.contains('open')) closeToolsDrawer();
      else openToolsDrawer();
    });

    document.getElementById('btn-floating-toggle-edges')?.addEventListener('click', (e) => {
      state.showEdgesProminent = !state.showEdgesProminent;
      e.currentTarget.classList.toggle('active', state.showEdgesProminent);
      renderGraphOnMap();
    });

    document.getElementById('btn-floating-fit')?.addEventListener('click', fitGraphBounds);

    // 7. Drawer Close Buttons
    document.getElementById('btn-close-player-drawer')?.addEventListener('click', closePlayerDrawer);
    document.getElementById('btn-close-tools-drawer')?.addEventListener('click', closeToolsDrawer);

    // 8. Traversal Player Controls
    document.getElementById('btn-player-play')?.addEventListener('click', () => {
      if (state.stepPlayer.isPlaying) pauseStepPlayer();
      else playStepPlayer();
    });
    document.getElementById('btn-player-next')?.addEventListener('click', stepNext);
    document.getElementById('btn-player-prev')?.addEventListener('click', stepPrev);
    document.getElementById('btn-player-reset')?.addEventListener('click', stepReset);
    document.getElementById('btn-player-end')?.addEventListener('click', stepEnd);

    const progressTrack = document.querySelector('.step-progress-track');
    if (progressTrack) {
      progressTrack.addEventListener('click', (e) => {
        if (!state.stepPlayer.steps || state.stepPlayer.steps.length === 0) return;
        const rect = progressTrack.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const targetIdx = Math.round(ratio * (state.stepPlayer.steps.length - 1));
        pauseStepPlayer();
        state.stepPlayer.currentIndex = targetIdx;
        updatePlayerUI();
      });
    }

    const speedSlider = document.getElementById('step-speed-slider');
    if (speedSlider) {
      speedSlider.addEventListener('input', (e) => {
        state.stepPlayer.speedMs = parseInt(e.target.value, 10);
        document.getElementById('step-speed-val').textContent = `${state.stepPlayer.speedMs}ms`;
        if (state.stepPlayer.isPlaying) {
          playStepPlayer();
        }
      });
    }

    // 9. Cost Metric Toggle
    document.querySelectorAll('.weight-mode-toggle .toggle-option').forEach(opt => {
      opt.addEventListener('click', () => {
        document.querySelectorAll('.weight-mode-toggle .toggle-option').forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        state.weightMode = opt.dataset.weight || 'effective';
        if (state.selectedTarget) computeRoute();
      });
    });

    // 10. Waypoint button
    document.getElementById('btn-add-waypoint')?.addEventListener('click', () => addWaypoint(''));

    // 11. Graph Editor Forms
    document.getElementById('form-add-node')?.addEventListener('submit', handleAddNode);
    document.getElementById('form-add-edge')?.addEventListener('submit', handleAddEdge);
    document.getElementById('btn-pick-node-coords')?.addEventListener('click', () => {
      closeToolsDrawer();
      startPickingMode('map-add-node');
    });
    document.getElementById('btn-reload-preset')?.addEventListener('click', () => loadPreset(state.activePreset));

    // 12. Modal Close Buttons & Backdrops
    document.querySelectorAll('.modal-close').forEach(btn => {
      btn.addEventListener('click', () => {
        const modalId = btn.dataset.modal;
        if (modalId) closeModal(modalId);
      });
    });

    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.classList.remove('open');
      });
    });

    // 13. Graph JSON Modal Triggers
    document.querySelectorAll('.json-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => renderGraphJsonContent(btn.dataset.jsonView));
    });
    document.getElementById('btn-copy-graph-json')?.addEventListener('click', copyGraphJson);
    document.getElementById('btn-info-view-graph')?.addEventListener('click', () => {
      closeModal('modal-info');
      openGraphJsonModal('view-adj');
    });

    // 14. Edge Traffic Quick Buttons
    document.querySelectorAll('.traffic-set-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const mult = parseFloat(btn.dataset.mult);
        updateEdgeTrafficLevel(mult, false);
      });
    });

    document.getElementById('btn-toggle-edge-block')?.addEventListener('click', () => {
      if (state.selectedEdgeForEdit) {
        updateEdgeTrafficLevel(null, !state.selectedEdgeForEdit.is_blocked);
      }
    });

    document.getElementById('btn-delete-edge-modal')?.addEventListener('click', deleteCurrentEdge);

    // Cancel map pick
    document.getElementById('btn-cancel-map-pick')?.addEventListener('click', exitPickingMode);
  }

  // =========================================================================
  // 23. BOOTSTRAP INITIALIZATION
  // =========================================================================
  async function initializeApp() {
    // 1. Initialize Theme (Warm Amber default or user's saved choice)
    let initialTheme = 'amber';
    try {
      initialTheme = localStorage.getItem('navgraph_theme') || 'amber';
    } catch (_) {}
    applyTheme(initialTheme, false);

    initMap();
    setupEventListeners();

    // Health check initial and interval
    await performHealthCheck();
    setInterval(performHealthCheck, 15000);

    // Load default preset ('campus_navigator')
    try {
      await loadPreset(CONFIG.DEFAULT_PRESET);
    } catch (err) {
      console.warn('Initial preset load warning:', err);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
  } else {
    initializeApp();
  }

})();
