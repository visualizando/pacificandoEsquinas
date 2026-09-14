import unittest
from shapely.geometry import Polygon, LineString
from shapely.strtree import STRtree
from src.cycle_coverage import distances


class CoverageTests(unittest.TestCase):
    def test_centre_distance_and_added_network(self):
        block=Polygon([(0,0),(100,0),(100,100),(0,100)])
        current=[LineString([(200,-100),(200,200)])]
        proposed=[LineString([(100,-100),(100,200)])]
        self.assertEqual(distances(block,STRtree(current),STRtree(current+proposed)),(150,50))

    def test_same_network_unchanged(self):
        block=Polygon([(0,0),(100,0),(100,100),(0,100)])
        tree=STRtree([LineString([(50,-100),(50,200)])])
        self.assertEqual(distances(block,tree,tree),(0,0))


if __name__=='__main__':unittest.main()
