import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from school_streets import levels, similarity


class SchoolStreetsTest(unittest.TestCase):
    def test_address_normalization(self):
        self.assertEqual(similarity('Quintana, Manuel, Pres. 31', 'QUINTANA, MANUEL, PRES.'), 1)
        self.assertEqual(similarity('Santa Fe Av. 1510', 'SANTA FE AV.'), 1)
        self.assertEqual(similarity('Miralla 3838', 'AYACUCHO'), 0)

    def test_multiple_levels(self):
        self.assertEqual(levels('Nivel inicial común | Nivel primario común'), ['inicial', 'primaria'])
        self.assertEqual(levels('Servicios complementarios/alternativos'), ['otros'])

    def test_artifact_integrity(self):
        data = json.loads((ROOT / 'data/processed/school-streets.json').read_text(encoding='utf-8'))
        features = data['features']
        self.assertEqual(len(features), len({f['properties']['id'] for f in features}))
        self.assertEqual(len(features), data['metadata']['school_blocks'])
        used = set()
        for f in features:
            p = f['properties']
            self.assertGreater(p['length_m'], 0)
            self.assertFalse(used.intersection(p['source_segments']))
            used.update(p['source_segments'])
            ids = [s['id'] for s in p['schools']]
            self.assertEqual(len(ids), len(set(ids)))
            for link in p['schools']:
                self.assertIn(link['id'], data['schools'])
                self.assertLessEqual(link['distance_m'], 150)
            coords = f['geometry']['coordinates']
            if f['geometry']['type'] == 'MultiLineString':
                coords = [c for line in coords for c in line]
            for lon, lat in coords:
                self.assertTrue(-59 < lon < -58 and -35 < lat < -34)


if __name__ == '__main__':
    unittest.main()
