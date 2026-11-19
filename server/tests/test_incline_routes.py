"""Directional sustained-incline validation for the cached OSM road graph.

Run synthetic tests (no network): python tests/test_incline_routes.py
Run real Kingsport probes:       python tests/test_incline_routes.py --live

Run from the project root; requires core/road_network.py, core/data_fetcher.py,
and utils/geo_utils.py. Live mode queries OSM and Open-Elevation if not cached.
"""
from __future__ import annotations

import os
import argparse
import json
import math
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

from core.local_elevation import LocalElevationConnector

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import networkx as nx
from core.incline_analyzer import (InclineSpec, evaluate_profile, evaluate_route,
    profile_from_path, distance_m, bearing, angle_difference, position, nearest_node, M_PER_MILE)

M_PER_MILE = 1609.344
START = (36.488446, -82.527629)


def trace_direction(graph, start_node, initial_bearing, spec, road_name=None,
                    max_distance_miles=5.0):
    """Greedy, nonbranching traversal; prefer named road then directional continuity.

    Not a global path search. At intersections it picks the most directionally
    consistent connected edge. This is intentionally a diagnostic probe.
    """
    path = [start_node]
    visited = {start_node}
    current = start_node
    heading = initial_bearing
    traveled = 0.0
    while traveled < max_distance_miles * M_PER_MILE:
        options = []
        for nxt, attrs in graph[current].items():
            if nxt in visited:
                continue
            step = float(attrs.get('length_m', distance_m(position(graph, current), position(graph, nxt))))
            if step <= 0:
                continue
            new_heading = bearing(position(graph, current), position(graph, nxt))
            turn = angle_difference(heading, new_heading)
            if turn > spec.max_turn_deg:
                continue
            name = str(attrs.get('name') or '').casefold()
            name_penalty = 0 if not road_name or road_name.casefold() in name else 80
            options.append((turn + name_penalty, turn, nxt, step, new_heading))
        if not options:
            break
        _, _, nxt, step, heading = min(options, key=lambda x: (x[0], x[1]))
        path.append(nxt)
        visited.add(nxt)
        traveled += step
        current = nxt
    return path


def make_synthetic(grades, lengths):
    profile = [(0.0, 300.0)]
    for grade, length in zip(grades, lengths):
        d,z = profile[-1]
        profile.append((d+length,z+grade*length/100))
    return profile


class InclineTests(unittest.TestCase):
    def setUp(self):
        self.spec = InclineSpec(min_distance_miles=1.0)
        self.distance = M_PER_MILE

    def test_uniform_gentle_climb_passes(self):
        ok,_ = evaluate_profile(make_synthetic([1.5]*40,[self.distance/40]*40), self.spec)
        self.assertTrue(ok)

    def test_short_steep_section_allowed(self):
        # 50 m at 3.5%; remaining grade adjusted to stay in target mean.
        n = 39
        remaining = self.distance-50
        grade = (1.5*self.distance-3.5*50)/remaining
        ok,info = evaluate_profile(make_synthetic([grade]*n+[3.5],[remaining/n]*n+[50]), self.spec)
        self.assertTrue(ok,info)

    def test_sustained_steep_climb_fails(self):
        ok,_ = evaluate_profile(make_synthetic([5.0]*40,[self.distance/40]*40),self.spec)
        self.assertFalse(ok)

    def test_long_steep_excursion_fails(self):
        ok,_ = evaluate_profile(make_synthetic([1.5]*25+[3.5]*10+[1.5]*5,[self.distance/40]*40),self.spec)
        self.assertFalse(ok)

    def test_short_route_fails(self):
        ok,info = evaluate_profile(make_synthetic([1.5],[400]),self.spec)
        self.assertFalse(ok)
        self.assertEqual(info['reason'],'insufficient_distance')

    def test_rolling_downhill_fails(self):
        ok,_ = evaluate_profile(make_synthetic([2.0]*20+[-1.0]*10+[2.0]*10,[self.distance/40]*40),self.spec)
        self.assertFalse(ok)



def summarize_path(graph, path, elevations, spec):
    """Explain the complete traced path, including failed portions by road."""
    if not path:
        return {'error': 'empty path'}
    edges = []
    cumulative = 0.0
    for a, b in zip(path, path[1:]):
        attrs = graph[a][b]
        length = float(attrs.get('length_m', distance_m(position(graph, a), position(graph, b))))
        if length <= 0:
            continue
        grade = 100 * (float(elevations[b]) - float(elevations[a])) / length
        name = str(attrs.get('name') or '').strip() or '(unnamed road/path)'
        edges.append({'road': name, 'way_id': attrs.get('osm_way_id'),
                      'start_m': cumulative, 'end_m': cumulative + length,
                      'length_m': length, 'grade_pct': grade,
                      'in_target': spec.target_min_grade_pct <= grade <= spec.target_max_grade_pct,
                      'start_coordinate': position(graph, a), 'end_coordinate': position(graph, b)})
        cumulative += length

    total = cumulative
    if not edges:
        return {'starting_coordinates': position(graph, path[0]), 'total_miles': 0.0,
                'reason': 'no traversable edges', 'road_sections': [], 'failed_sections': []}
    grades = [e['grade_pct'] for e in edges]
    net = 100 * (float(elevations[path[-1]]) - float(elevations[path[0]])) / total
    # Group contiguous edges on the same named road. Every transition is reported.
    sections = []
    for e in edges:
        if sections and sections[-1]['road'] == e['road']:
            section = sections[-1]
            section['end_m'] = e['end_m']
            section['end_coordinate'] = e['end_coordinate']
            section['gain_m'] += e['grade_pct'] * e['length_m'] / 100
        else:
            sections.append({'road': e['road'], 'start_m': e['start_m'],
                             'end_m': e['end_m'], 'start_coordinate': e['start_coordinate'],
                             'end_coordinate': e['end_coordinate'],
                             'gain_m': e['grade_pct'] * e['length_m'] / 100})
    for section in sections:
        section['length_miles'] = round((section['end_m'] - section['start_m']) / M_PER_MILE, 3)
        section['overall_grade_pct'] = round(100 * section.pop('gain_m') / (section['end_m'] - section['start_m']), 3)
        section['start_mile'] = round(section.pop('start_m') / M_PER_MILE, 3)
        section['end_mile'] = round(section.pop('end_m') / M_PER_MILE, 3)

    turns = [{'at_mile': section['start_mile'], 'coordinate': section['start_coordinate'],
              'from_road': sections[i-1]['road'], 'to_road': section['road']}
             for i, section in enumerate(sections) if i > 0]

    # Consecutive outside-target edges form excursions, split at road-name changes
    # so failures can be located on the ground. Also report aggregate failed distance.
    failed = []
    for e in edges:
        if e['in_target']:
            continue
        if failed and failed[-1]['road'] == e['road'] and abs(failed[-1]['end_m'] - e['start_m']) < 0.01:
            f = failed[-1]
            f['end_m'] = e['end_m']
            f['end_coordinate'] = e['end_coordinate']
            f['gain_m'] += e['grade_pct'] * e['length_m'] / 100
            f['max_grade_pct'] = max(f['max_grade_pct'], e['grade_pct'])
            f['min_grade_pct'] = min(f['min_grade_pct'], e['grade_pct'])
        else:
            failed.append({'road': e['road'], 'start_m': e['start_m'], 'end_m': e['end_m'],
                           'start_coordinate': e['start_coordinate'], 'end_coordinate': e['end_coordinate'],
                           'gain_m': e['grade_pct'] * e['length_m'] / 100,
                           'max_grade_pct': e['grade_pct'], 'min_grade_pct': e['grade_pct']})
    for f in failed:
        length = f['end_m'] - f['start_m']
        f['length_m'] = round(length, 1)
        f['length_miles'] = round(length / M_PER_MILE, 3)
        f['overall_grade_pct'] = round(100 * f.pop('gain_m') / length, 3)
        f['max_grade_pct'] = round(f['max_grade_pct'], 3)
        f['min_grade_pct'] = round(f['min_grade_pct'], 3)
        f['start_mile'] = round(f.pop('start_m') / M_PER_MILE, 3)
        f['end_mile'] = round(f.pop('end_m') / M_PER_MILE, 3)
    qualifying_m = sum(e['length_m'] for e in edges if e['in_target'])
    return {'starting_coordinates': position(graph, path[0]),
            'ending_coordinates': position(graph, path[-1]),
            'starting_road': edges[0]['road'],
            'total_miles': round(total / M_PER_MILE, 3),
            'overall_grade_pct': round(net, 3),
            'max_grade_pct': round(max(grades), 3),
            'min_grade_pct': round(min(grades), 3),
            'qualifying_target_miles': round(qualifying_m / M_PER_MILE, 3),
            'qualifying_target_fraction': round(qualifying_m / total, 4),
            'out_of_target_miles': round((total - qualifying_m) / M_PER_MILE, 3),
            'road_sections': sections, 'road_changes': turns, 'failed_sections': failed}


def print_route_report(report):
    print('\n' + '=' * 76)
    print(f"{report['route']}: {'PASS' if report['passes'] else 'FAIL'}")
    print(f"Start: {report['starting_coordinates']} | Road: {report.get('starting_road', 'unknown')}")
    print(f"Length: {report['total_miles']:.3f} mi | Overall grade: {report['overall_grade_pct']:+.2f}% | "
          f"Max: {report['max_grade_pct']:+.2f}% | Min: {report['min_grade_pct']:+.2f}%")
    print(f"Within {report['target_grade_range_pct']}% target: {report['qualifying_target_miles']:.3f} mi "
          f"({report['qualifying_target_fraction']:.1%}); outside: {report['out_of_target_miles']:.3f} mi")
    print('Qualification reason:', report['qualification'].get('reason'))
    print('Checks:', report['qualification'].get('checks', {}))
    print('Roads traversed:')
    for section in report['road_sections']:
        print(f"  {section['start_mile']:.3f}–{section['end_mile']:.3f} mi: "
              f"{section['road']} ({section['length_miles']:.3f} mi, {section['overall_grade_pct']:+.2f}%)")
    print('Road changes:')
    for turn in report['road_changes']:
        print(f"  At {turn['at_mile']:.3f} mi {turn['coordinate']}: "
              f"{turn['from_road']} -> {turn['to_road']}")
    if not report['road_changes']:
        print('  None detected')
    print('Outside-target sections (including sections beyond qualification distance):')
    for section in report['failed_sections']:
        print(f"  {section['start_mile']:.3f}–{section['end_mile']:.3f} mi "
              f"({section['length_miles']:.3f} mi): {section['road']}; "
              f"avg {section['overall_grade_pct']:+.2f}%, "
              f"min {section['min_grade_pct']:+.2f}%, max {section['max_grade_pct']:+.2f}%")
    if not report['failed_sections']:
        print('  None')
    print('NOTE: Out-of-target sections are diagnostic; short sections may be allowed by tolerance.')



class ReportTests(unittest.TestCase):
    def test_road_sections_turns_and_failed_extents(self):
        graph = nx.Graph()
        for i in range(4):
            graph.add_node(i, lat=36.48 + i * 0.001, lon=-82.52)
        for a, b, road in [(0, 1, 'Rock Springs Road'),
                           (1, 2, 'Rock Springs Road'),
                           (2, 3, 'Moreland Drive')]:
            graph.add_edge(a, b, length_m=100.0, name=road)
        elevations = {0: 300.0, 1: 301.5, 2: 303.0, 3: 308.0}
        report = summarize_path(graph, [0, 1, 2, 3], elevations, InclineSpec())
        self.assertEqual(report['starting_road'], 'Rock Springs Road')
        self.assertEqual(len(report['road_changes']), 1)
        self.assertEqual(report['road_changes'][0]['to_road'], 'Moreland Drive')
        self.assertAlmostEqual(report['qualifying_target_miles'], 200 / M_PER_MILE, places=3)
        self.assertEqual(len(report['failed_sections']), 1)
        self.assertEqual(report['failed_sections'][0]['road'], 'Moreland Drive')
        self.assertEqual(report['failed_sections'][0]['overall_grade_pct'], 5.0)

def live_probes(args):
    from core.road_network import OSMConnector
    from core.data_fetcher import ElevationConnector

    spec = InclineSpec(min_distance_miles=args.min_miles,
                       target_min_grade_pct=args.min_grade,
                       target_max_grade_pct=args.max_grade,
                       max_short_grade_pct=args.max_short_grade,
                       max_excursion_m=args.excursion_m,
                       max_excursion_fraction=args.excursion_fraction,
                       max_rolling_grade_pct=args.max_rolling_grade)
    lat,lon = START
    delta = args.bbox_degrees
    bbox = (lat-delta,lon-delta,lat+delta,lon+delta)
    with OSMConnector(cache_dir=args.cache_dir) as osm:
        graph = osm.get_road_graph(bbox)
    if not graph.number_of_nodes():
        raise RuntimeError('No road graph returned; check Overpass and cache')
    start = nearest_node(graph, START)
    snap_m = distance_m(START, position(graph,start))
    if snap_m > spec.max_start_distance_m:
        raise RuntimeError(f'Nearest road node is {snap_m:.1f} m away; start point cannot be trusted')
    print(f'Start snapped {snap_m:.1f} m to node {start!r}; graph {graph.number_of_nodes()} nodes')
    # Bearings are starting hints, not verified surveyed road headings.
    # Moreland bearing is inferred; inspect the first edge and change if needed.
    probes = [
        ('Rock Springs SW',225,'Rock Springs'),
        ('Rock Springs NE',45,'Rock Springs'),
        ('Moreland Drive (initial heading guess)',300,'Moreland'),
    ]
    routes = []
    for name, heading, road in probes:
        path = trace_direction(graph,start,heading,spec,road_name=road,
                               max_distance_miles=max(5.0,args.min_miles+1))
        routes.append((name,path))
    nodes = list(dict.fromkeys(node for _,path in routes for node in path))
    print(f'Retrieving elevations for {len(nodes)} unique nodes (may consume API quota)')
    lat_long_on_path = [
        {
            'latitude':position(graph,n)[0],
            'longitude':position(graph,n)[1]
        } 
        for n in nodes
    ]
    lec = LocalElevationConnector()
    lat_long_needed = lec.filter_lat_long_return_missing_coords(lat_long_on_path)
    with ElevationConnector(
        batch_size=args.batch_size,
        api_key=os.environ.get("OPEN_ELEVATION_API_KEY")
    ) as ec:
        results = ec.fetch_elevation_for_coords()
    elevations = {n:float(r['elevation']) for n,r in zip(nodes,results)}
    reports = []
    for name,path in routes:
        profile = profile_from_path(graph,path,elevations)
        passes,diagnostics = evaluate_profile(profile,spec)
        details = summarize_path(graph, path, elevations, spec)
        report = {'route': name, 'passes': bool(passes), 'nodes': len(path),
                  'target_grade_range_pct': [spec.target_min_grade_pct, spec.target_max_grade_pct],
                  'qualification': diagnostics, **details}
        reports.append(report)
        print_route_report(report)
    Path(args.report).write_text(json.dumps({'spec':asdict(spec),'reports':reports},indent=2))
    print(f'Report saved to {args.report}')
    print('CAUTION: inspect traced paths before interpreting PASS/FAIL: greedy intersection choices can select the wrong road.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',default=True, help='Query cached OSM graph and live elevation API')
    parser.add_argument('--min-miles',type=float,default=2.0)
    parser.add_argument('--min-grade',type=float,default=1.0)
    parser.add_argument('--max-grade',type=float,default=2.0)
    parser.add_argument('--max-short-grade',type=float,default=4.0)
    parser.add_argument('--max-rolling-grade',type=float,default=3.0)
    parser.add_argument('--excursion-m',type=float,default=150.0)
    parser.add_argument('--excursion-fraction',type=float,default=0.15)
    parser.add_argument('--bbox-degrees',type=float,default=0.065)
    parser.add_argument('--batch-size',type=int,default=250)
    parser.add_argument('--cache-dir',default='cache/osm')
    parser.add_argument('--report',default='incline_route_report.json')
    args = parser.parse_args()
    if args.live:
        live_probes(args)
    else:
        unittest.main(argv=[sys.argv[0]])
