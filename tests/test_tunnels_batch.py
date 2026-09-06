import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'data/processed/tunnels-all.json').read_text(encoding='utf-8'))
        cls.inventory=json.loads((ROOT/'data/processed/tunnel-inventory.json').read_text(encoding='utf-8'))

    def test_inventory_coverage(self):
        cases=self.data['cases']
        self.assertEqual(len(cases),len(self.inventory['sites']))
        self.assertEqual(len({c['id'] for c in cases}),len(cases))
        for site in self.inventory['sites']:
            self.assertTrue(any(set(c['tunnel_way_ids'])&set(site['way_ids']) for c in cases))

    def test_results_and_provenance(self):
        for c in self.data['cases']:
            raw=(ROOT/f"data/tunnels/{c['id']}.osm.json").read_bytes()
            self.assertEqual(c['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(set(c['directions']),{'outbound','return'})
            for d in c['directions'].values():
                self.assertEqual(set(d['routes']),{'car','walk','step_free'})
                for mode,r in d['routes'].items():
                    if r['status']=='ok':
                        self.assertGreater(r['distance_m'],0,(c['name'],mode))
                        self.assertLessEqual(max(r['snap_m']),45)
                        self.assertGreaterEqual(len(r['geometry']['coordinates']),2)
                        if mode=='step_free':self.assertEqual(r['step_way_count'],0)
                    else:self.assertNotIn('distance_m',r)
                if d['valid_tunnel_crossing']:
                    self.assertTrue(set(d['routes']['car']['osm_way_ids'])&set(c['tunnel_way_ids']))
                if d['step_free_penalty']:
                    self.assertTrue(d['pedestrian_endpoints_comparable'])
                    self.assertGreaterEqual(d['step_free_penalty']['extra_m'],0)

    def test_original_endpoints_preserved(self):
        original=json.loads((ROOT/'data/tunnels/cases.json').read_text(encoding='utf-8'))['cases']
        for old in original:
            new=next(c for c in self.data['cases'] if c['id']==old['id'])
            for key in ('origin','destination','tunnel_way_ids'):self.assertEqual(old[key],new[key])

    def test_download_dates_not_older_than_inventory(self):
        network=json.loads((ROOT/'data/tunnels/city-network.osm.json').read_text(encoding='utf-8'))
        dates=network['osm3s'].get('block_timestamps',[network['osm3s']['timestamp_osm_base']])
        for date in dates:
            self.assertGreaterEqual(date[:10],self.inventory['snapshot_at'][:10])

if __name__=='__main__':unittest.main()
