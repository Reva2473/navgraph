"""
Preset Map Datasets and Spatial Topologies for Smart Route Optimization.

Provides pre-configured, realistic graphs:
1. 'india_highways': 18 Major National Cities connected by Interstate High-Speed Corridors.
2. 'campus_navigator': 14 NSUT Dwarka Campus Landmarks connected by Walkways and Internal Roads.
"""

from typing import Any, Dict, List

from backend.dsa.graph import Node, WeightedGraph

PRESETS_METADATA: Dict[str, Dict[str, Any]] = {
    "india_highways": {
        "id": "india_highways",
        "name": "India National Highway Network (18 Major Cities)",
        "category": "National Highway Network",
        "description": "Golden Quadrilateral and Interstate Freight Corridors connecting 18 major metropolitan and economic centers.",
        "node_count": 18,
        "default_source": "delhi",
        "default_target": "bengaluru",
        "map_center": [21.5, 79.5],
        "default_zoom": 5,
        "default_weight_mode": "effective",
    },
    "campus_navigator": {
        "id": "campus_navigator",
        "name": "NSUT Dwarka Campus (14 Landmarks)",
        "category": "NSUT Smart Campus Walkways",
        "description": "Netaji Subhas University of Technology (NSUT), Sector 3, Dwarka, New Delhi — Academic Blocks, Hostels, Moksha Ground & Gates.",
        "node_count": 14,
        "default_source": "main_gate",
        "default_target": "cs_dept",
        "map_center": [28.6103, 77.0375],
        "default_zoom": 16,
        "default_weight_mode": "effective",
    },
}


def _build_india_highways_graph() -> WeightedGraph:
    """Construct and populate the 18-city India Highway Network graph."""
    g = WeightedGraph()

    # 18 Major Cities
    cities: List[Node] = [
        Node("delhi", "New Delhi", 28.6139, 77.2090, "metro", "National Capital Region & Northern Transit Super-Hub"),
        Node("chandigarh", "Chandigarh", 30.7333, 76.7794, "capital", "Planned City & Gateway to Northern Himalayan Corridors"),
        Node("jaipur", "Jaipur", 26.9124, 75.7873, "capital", "Pink City & Western Freight Corridor Junction"),
        Node("lucknow", "Lucknow", 26.8467, 80.9462, "capital", "Heart of Central Gangetic Expressway Grid"),
        Node("ahmedabad", "Ahmedabad", 23.0225, 72.5714, "metro", "Western Commercial Hub & Golden Quadrilateral Node"),
        Node("bhopal", "Bhopal", 23.2599, 77.4126, "capital", "Central India Strategic Rail & Highway Crossroads"),
        Node("patna", "Patna", 25.5941, 85.1376, "capital", "Eastern Gangetic Plain Transport & River Corridor"),
        Node("guwahati", "Guwahati", 26.1445, 91.7362, "hub", "Northeast Frontier Gateway Corridor"),
        Node("kolkata", "Kolkata", 22.5726, 88.3639, "metro", "Eastern Port Megacity & Golden Quadrilateral Anchor"),
        Node("mumbai", "Mumbai", 19.0760, 72.8777, "metro", "Financial Capital & Western Seaboard Super-Hub"),
        Node("pune", "Pune", 18.5204, 73.8567, "hub", "Automotive & Technology Expressway Corridor"),
        Node("nagpur", "Nagpur", 21.1458, 79.0882, "hub", "Zero Mile Center of India - National Crossway"),
        Node("bhubaneswar", "Bhubaneswar", 20.2961, 85.8245, "capital", "East Coast NH16 Industrial Corridor"),
        Node("hyderabad", "Hyderabad", 17.3850, 78.4867, "metro", "Deccan Plateau Cyber & Logistics Megacity"),
        Node("visakhapatnam", "Visakhapatnam", 17.6868, 83.2185, "hub", "Deep-Water Port & Coastal Economic Corridor"),
        Node("bengaluru", "Bengaluru", 12.9716, 77.5946, "metro", "Silicon Valley of India & Southern Tech Hub"),
        Node("chennai", "Chennai", 13.0827, 80.2707, "metro", "Automobile Capital & Southern Maritime Gateway"),
        Node("kochi", "Kochi", 9.9312, 76.2673, "hub", "Queen of Arabian Sea & Southernmost Commercial Port"),
    ]

    for city in cities:
        g.add_node(city)

    # Highway Interconnections
    highways = [
        # North
        ("delhi", "chandigarh", 245.0, "NH44", 1.0, 90.0),
        ("delhi", "jaipur", 280.0, "NH48", 1.0, 80.0),
        ("delhi", "lucknow", 550.0, "Yamuna / Agra Expy", 1.0, 100.0),
        ("delhi", "bhopal", 780.0, "NH44", 1.0, 85.0),

        # Central & Gangetic
        ("jaipur", "ahmedabad", 660.0, "NH48", 1.0, 85.0),
        ("jaipur", "bhopal", 600.0, "NH52", 1.0, 80.0),
        ("lucknow", "patna", 535.0, "Purvanchal Expy / NH19", 1.0, 85.0),
        ("lucknow", "nagpur", 770.0, "NH44", 1.0, 80.0),
        ("bhopal", "nagpur", 350.0, "NH46", 1.0, 80.0),

        # East & Northeast
        ("patna", "kolkata", 580.0, "NH19", 1.0, 80.0),
        ("kolkata", "guwahati", 990.0, "NH27", 1.0, 70.0),
        ("kolkata", "bhubaneswar", 440.0, "NH16", 1.0, 85.0),
        ("bhubaneswar", "visakhapatnam", 440.0, "NH16", 1.0, 85.0),

        # West & Central
        ("ahmedabad", "mumbai", 525.0, "NH48 / NE1", 1.0, 90.0),
        ("mumbai", "pune", 150.0, "Mumbai-Pune Expressway", 1.0, 90.0),
        ("mumbai", "nagpur", 700.0, "Samruddhi Mahamarg", 1.0, 110.0),
        ("pune", "nagpur", 710.0, "Samruddhi Mahamarg", 1.0, 110.0),
        ("pune", "bengaluru", 840.0, "NH48", 1.0, 85.0),

        # South & Deccan
        ("nagpur", "hyderabad", 500.0, "NH44", 1.0, 85.0),
        ("hyderabad", "visakhapatnam", 620.0, "NH65 / NH16", 1.0, 80.0),
        ("hyderabad", "bengaluru", 570.0, "NH44", 1.0, 90.0),
        ("hyderabad", "chennai", 630.0, "NH65 / NH16", 1.0, 80.0),
        ("visakhapatnam", "chennai", 800.0, "NH16", 1.0, 85.0),
        ("bengaluru", "chennai", 350.0, "NH48", 1.0, 80.0),
        ("bengaluru", "kochi", 550.0, "NH544", 1.0, 75.0),
        ("chennai", "kochi", 690.0, "NH544 / NH44", 1.0, 75.0),
    ]

    for src, dst, dist, road, traffic, speed in highways:
        g.add_edge(
            source=src,
            target=dst,
            base_distance_km=dist,
            road_name=road,
            traffic_multiplier=traffic,
            speed_limit_kmh=speed,
            bidirectional=True,
        )

    return g


def _build_campus_navigator_graph() -> WeightedGraph:
    """Construct and populate the 14-landmark NSUT Dwarka Campus graph."""
    g = WeightedGraph()

    # 14 NSUT Dwarka Campus Landmarks
    landmarks: List[Node] = [
        Node("main_gate", "NSUT Main Gate (Azad Hind Fauj Marg)", 28.608484, 77.035251, "gate", "Primary Campus Entrance on Azad Hind Fauj Marg, Sector 3 Dwarka"),
        Node("security_hub", "Nescii Lawns & Netaji Statue", 28.609615, 77.036107, "cultural", "Iconic Central Green Lawns & Netaji Subhas Chandra Bose Statue"),
        Node("admin_block", "Administrative Block (VC Office)", 28.609847, 77.037082, "admin", "Vice-Chancellor Office, Registrar & Central Administration"),
        Node("central_library", "Central Library & SAC", 28.610370, 77.039165, "academic", "Library Block, Student Activity Centre (SAC) & Computer Centre"),
        Node("cs_dept", "Block 5 (CSE & IT Dept)", 28.609719, 77.038585, "academic", "Department of Computer Science & Information Technology (Block V)"),
        Node("ece_dept", "Block 4 (ECE & Biotech Dept)", 28.609465, 77.037668, "academic", "Electronics & Communication Engineering and Bio-Tech (Block IV)"),
        Node("innovation_hub", "Block 6 & Connecting Block (ICE/MPAE)", 28.610526, 77.037807, "research", "Instrumentation, Mechanical & Connecting Block 8A Labs"),
        Node("auditorium", "APJ Abdul Kalam Lecture Complex", 28.611974, 77.037063, "academic", "Dr. A.P.J. Abdul Kalam Multi-Story Lecture Theatre Complex"),
        Node("cafeteria", "Students' Centre (Amul & Canteen)", 28.611663, 77.036911, "amenity", "Students' Centre Canteen, Amul Parlour & Mother Dairy Hub"),
        Node("hostel_north", "Boys Hostels (Ramanujan & Aryabhata)", 28.612997, 77.034706, "residence", "Ramanujan (BH-4), Raman (BH-3), Aryabhata (BH-1) & Bhaskara Hostels"),
        Node("hostel_south", "Girls Hostels (Sarasvati & Alaknanda)", 28.607497, 77.039652, "residence", "Sarasvati (GH-1), Alaknanda Hostel & Training/Placement Cell"),
        Node("sports_arena", "NSUT Sports Complex & Track", 28.610394, 77.041365, "sports", "Main Cricket/Football Ground, Running Track & Kabaddi Court"),
        Node("medical_center", "Moksha Ground & Medical Centre", 28.610845, 77.036582, "health", "Historic Moksha Fest Ground & NSUT Campus Health Centre"),
        Node("metro_gate", "NSUT North Gate (Dwarka Mor Gate)", 28.613175, 77.033627, "gate", "Secondary Exit Gate on Azad Hind Fauj Marg towards Dwarka Mor Metro"),
    ]

    for lm in landmarks:
        g.add_node(lm)

    # Campus Walkways & Internal Roads
    pathways = [
        ("main_gate", "security_hub", 0.16, "Netaji Subhas Marg", 1.0, 20.0),
        ("main_gate", "medical_center", 0.29, "West Campus Ring Road", 1.0, 20.0),
        ("security_hub", "admin_block", 0.11, "Admin Quad Walk", 1.0, 15.0),
        ("security_hub", "medical_center", 0.15, "Moksha Lawn Path", 1.0, 15.0),
        ("medical_center", "cafeteria", 0.12, "Amul Canteen Lane", 1.0, 15.0),
        ("admin_block", "ece_dept", 0.08, "Block IV Connector", 1.0, 15.0),
        ("admin_block", "innovation_hub", 0.11, "Central Fountain Walk", 1.0, 15.0),
        ("admin_block", "cafeteria", 0.21, "APJ Avenue", 1.0, 15.0),
        ("ece_dept", "cs_dept", 0.10, "Connecting Block 8A Corridor", 1.0, 15.0),
        ("ece_dept", "hostel_south", 0.30, "South T&P Road", 1.0, 20.0),
        ("cs_dept", "central_library", 0.09, "Library Walkway", 1.0, 15.0),
        ("cs_dept", "innovation_hub", 0.12, "Academic Quad Path", 1.0, 15.0),
        ("cs_dept", "hostel_south", 0.27, "Sarasvati Hostel Road", 1.0, 20.0),
        ("innovation_hub", "central_library", 0.14, "SAC Concourse", 1.0, 15.0),
        ("innovation_hub", "auditorium", 0.18, "Lecture Complex Link", 1.0, 20.0),
        ("cafeteria", "auditorium", 0.05, "APJ Plaza Walk", 1.0, 15.0),
        ("auditorium", "hostel_north", 0.26, "Boys Hostel Road", 1.0, 20.0),
        ("central_library", "sports_arena", 0.22, "Sports Complex Avenue", 1.0, 20.0),
        ("hostel_north", "metro_gate", 0.11, "North Gate Exit Road", 1.0, 20.0),
        ("hostel_north", "medical_center", 0.30, "Hostel Ring Road", 1.0, 20.0),
    ]

    for src, dst, dist, name, traffic, speed in pathways:
        g.add_edge(
            source=src,
            target=dst,
            base_distance_km=dist,
            road_name=name,
            traffic_multiplier=traffic,
            speed_limit_kmh=speed,
            bidirectional=True,
        )

    return g


def load_preset_graph(preset_id: str) -> WeightedGraph:
    """
    Factory function to instantiate and return a loaded WeightedGraph preset.

    Args:
        preset_id: Identifier of the preset ('india_highways' or 'campus_navigator').

    Returns:
        Populated WeightedGraph instance.

    Raises:
        ValueError: If preset_id is unrecognized.
    """
    preset_key = preset_id.lower().strip()
    if preset_key == "india_highways":
        return _build_india_highways_graph()
    elif preset_key == "campus_navigator":
        return _build_campus_navigator_graph()
    else:
        valid_presets = list(PRESETS_METADATA.keys())
        raise ValueError(f"Unknown preset '{preset_id}'. Valid presets are: {valid_presets}")
