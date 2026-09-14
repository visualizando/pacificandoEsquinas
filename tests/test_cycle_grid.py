"""Checks for topology and infrastructure classification of the baseline."""
import unittest
from src.cycle_grid import infrastructure, shortest_path, extensions
from shapely.geometry import LineString
from collections import defaultdict


class CycleGridTests(unittest.TestCase):
    def test_only_extend_existing_and_avoid_parallel(self):
        xy = {0: (0, 0), 1: (200, 0), 2: (400, 0), 3: (600, 0),
              4: (200, 200), 5: (400, 200), 6: (200, 100), 7: (600, 100)}
        def run(pairs):
            graph, edges = defaultdict(list), []
            for a, b, existing in pairs:
                line = LineString([xy[a], xy[b]])
                i = len(edges)
                edges.append(dict(a=a, b=b, existing=existing, geometry=line,
                                  length=line.length, street='Test'))
                graph[a].append((b, i)); graph[b].append((a, i))
            return extensions(graph, edges, xy)
        # A disconnected candidate and a right-angle branch must not be proposed.
        pairs = [(0, 1, True), (1, 2, False), (2, 3, False),
                 (1, 4, False), (4, 5, False)]
        chosen, corridors = run(pairs)
        self.assertEqual(set(chosen), {1, 2})
        self.assertEqual(corridors[0]['start_node'], 1)
        # A nearby parallel existing corridor prevents duplicate provision.
        chosen, _ = run(pairs+[(6, 7, True)])
        self.assertFalse(chosen)

    def test_real_infrastructure_only(self):
        for tags in [{'highway': 'cycleway'}, {'cycleway:left': 'track'},
                     {'cycleway:both': 'lane'}, {'highway': 'path', 'bicycle': 'designated'}]:
            self.assertTrue(infrastructure(tags))
        for tags in [{'cycleway': 'no'}, {'cycleway': 'separate'},
                     {'cycleway': 'shared_lane'}, {'bicycle': 'yes'},
                     {'highway': 'construction', 'cycleway': 'track'}]:
            self.assertFalse(infrastructure(tags))

    def test_connected_path_and_cost(self):
        graph = {0: [(1, 0), (2, 2)], 1: [(0, 0), (2, 1)],
                 2: [(0, 2), (1, 1)], 3: []}
        self.assertEqual(shortest_path(graph, 0, 2, lambda i: [1, 1, 5][i]), [0, 1])
        self.assertEqual(shortest_path(graph, 0, 3, lambda i: 1), [])
        self.assertEqual(shortest_path(graph, 0, 0, lambda i: 1), [])


if __name__ == '__main__':
    unittest.main()
