"""Reusable directional incline qualification for routes in a NetworkX road graph.

This module does not select roads or search for routes. Pass an ordered connected
node path and elevations keyed by node ID, or pass a distance/elevation profile.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

M_PER_MILE = 1609.344

@dataclass(frozen=True)
class InclineSpec:
    min_distance_miles: float = 2.0
    target_min_grade_pct: float = 1.0
    target_max_grade_pct: float = 2.0
    max_short_grade_pct: float = 4.0
    max_excursion_m: float = 150.0
    max_excursion_fraction: float = 0.15
    min_uphill_fraction: float = 0.75
    rolling_window_m: float = 200.0
    max_rolling_grade_pct: float = 3.0
    max_turn_deg: float = 65.0
    max_start_distance_m: float = 125.0


def distance_m(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon / 2)**2
    return 2*6371008.8*math.asin(min(1, math.sqrt(h)))


def bearing(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    x = math.sin(dlon)*math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def angle_difference(a, b):
    return abs((a-b+180) % 360-180)


def position(graph, node):
    p = graph.nodes[node]
    return (float(p['lat']), float(p['lon']))


def nearest_node(graph, latlon):
    if not graph.nodes:
        raise ValueError('Road graph is empty')
    return min(graph.nodes, key=lambda n: distance_m(latlon, position(graph, n)))


def profile_from_path(graph, path, elevations):
    """Return distance/elevation pairs; elevation keyed by graph node ID."""
    profile = [(0.0, float(elevations[path[0]]))]
    for a, b in zip(path, path[1:]):
        edge = graph[a][b]
        step = float(edge.get('length_m', distance_m(position(graph, a), position(graph, b))))
        profile.append((profile[-1][0] + step, float(elevations[b])))
    return profile


def interpolate_elevation(profile, distance):
    if distance <= profile[0][0]:
        return profile[0][1]
    for (d0, z0), (d1, z1) in zip(profile, profile[1:]):
        if distance <= d1:
            return z0 + (z1-z0)*(distance-d0)/(d1-d0) if d1 > d0 else z1
    return profile[-1][1]


def evaluate_profile(profile, spec=InclineSpec()):
    """Return (passes: bool, diagnostics: dict).

    Evaluate the first min_distance_miles from the start; grade excursions
    are contiguous distances outside the target band, including flatter and
    downhill sections. Shorter than minimum always fails.
    """
    required = spec.min_distance_miles*M_PER_MILE
    if len(profile) < 2 or profile[-1][0] < required - 0.01:
        return False, {'reason': 'insufficient_distance', 'available_m': round(profile[-1][0] if profile else 0, 1),
                       'required_m': round(required, 1)}
    clipped = [(d,z) for d,z in profile if d < required]
    clipped.append((required, interpolate_elevation(profile, required)))
    net_grade = 100*(clipped[-1][1]-clipped[0][1])/required
    excursion_total = excursion_run = longest_excursion = uphill_m = 0.0
    worst_segment_grade = -math.inf
    for (d0,z0),(d1,z1) in zip(clipped,clipped[1:]):
        dx = d1-d0
        if dx <= 0: continue
        grade = 100*(z1-z0)/dx
        worst_segment_grade = max(worst_segment_grade, grade)
        if grade > 0: uphill_m += dx
        if not (spec.target_min_grade_pct <= grade <= spec.target_max_grade_pct):
            excursion_total += dx
            excursion_run += dx
            longest_excursion = max(longest_excursion, excursion_run)
        else:
            excursion_run = 0.0
    rolling_max = -math.inf
    # Evaluate rolling window at original samples and at the last valid start.
    window = min(spec.rolling_window_m, required)
    starts = sorted(set([0.0, required-window] + [d for d,_ in clipped if d <= required-window]))
    for d in starts:
        g = 100*(interpolate_elevation(clipped,d+window)-interpolate_elevation(clipped,d))/window
        rolling_max = max(rolling_max,g)
    checks = {
        'net_grade': spec.target_min_grade_pct <= net_grade <= spec.target_max_grade_pct,
        'max_segment_grade': worst_segment_grade <= spec.max_short_grade_pct,
        'longest_excursion': longest_excursion <= spec.max_excursion_m,
        'excursion_fraction': excursion_total/required <= spec.max_excursion_fraction,
        'uphill_fraction': uphill_m/required >= spec.min_uphill_fraction,
        'rolling_grade': rolling_max <= spec.max_rolling_grade_pct,
    }
    diagnostics = {
        'reason': 'pass' if all(checks.values()) else 'failed_checks',
        'distance_m': round(required,1), 'net_grade_pct': round(net_grade,3),
        'max_segment_grade_pct': round(worst_segment_grade,3),
        'max_rolling_grade_pct': round(rolling_max,3),
        'longest_excursion_m': round(longest_excursion,1),
        'excursion_fraction': round(excursion_total/required,3),
        'uphill_fraction': round(uphill_m/required,3), 'checks': checks,
    }
    return all(checks.values()), diagnostics




def evaluate_route(graph, path, elevations, spec=None):
    """Return (bool, diagnostics) for an ordered route of connected graph nodes.

    Elevations are meters keyed by node ID. Edge lengths use length_m when
    available, otherwise geodesic node distance. No road discovery is performed.
    """
    if spec is None:
        spec = InclineSpec()
    if not path:
        return False, {"reason": "empty_route"}
    if any(node not in elevations for node in path):
        return False, {"reason": "missing_elevation"}
    if any(not graph.has_edge(a, b) for a, b in zip(path, path[1:])):
        return False, {"reason": "disconnected_route"}
    return evaluate_profile(profile_from_path(graph, path, elevations), spec)
