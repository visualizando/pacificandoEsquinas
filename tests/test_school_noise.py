import unittest
from shapely.geometry import box, LineString
from shapely import STRtree
from src.school_noise import sample

class NoiseTest(unittest.TestCase):
    def test_half_high(self):
        tree = STRtree([box(0,-1,50,1),box(50,-1,100,1)])
        self.assertEqual(sample(LineString([(0,0),(100,0)]),tree,[60,65]),
                         {'coverage_pct':100.0,'high_pct':50.0})

    def test_missing_not_quiet(self):
        tree = STRtree([box(0,-1,50,1)])
        self.assertEqual(sample(LineString([(0,0),(100,0)]),tree,[70]),
                         {'coverage_pct':50.0,'high_pct':100.0})
        self.assertIsNone(sample(LineString([(200,0),(250,0)]),tree,[70])['high_pct'])

if __name__ == '__main__':
    unittest.main()
