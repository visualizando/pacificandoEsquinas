import sys
import unittest
from pathlib import Path
from shapely.geometry import LineString, box
from shapely.ops import unary_union
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from school_surface import width_at, integrate

class SurfaceTest(unittest.TestCase):
    def test_known_width_and_end_exclusion(self):
        line = LineString([(0,0),(100,0)])
        sides = unary_union([box(-1,5,101,9),box(-1,-9,101,-5)])
        self.assertAlmostEqual(width_at(line,50,sides),10)
        self.assertEqual(integrate(line,sides),(800,80))

    def test_missing_side_is_not_extrapolated(self):
        line = LineString([(0,0),(100,0)])
        self.assertEqual(integrate(line,box(-1,5,101,9)),(0,0))
        partial = unary_union([box(-1,5,50,9),box(-1,-9,101,-5)])
        self.assertEqual(integrate(line,partial),(400,40))

    def test_sidewalk_over_axis_rejected(self):
        self.assertIsNone(width_at(LineString([(0,0),(100,0)]),50,box(0,-1,100,1)))
