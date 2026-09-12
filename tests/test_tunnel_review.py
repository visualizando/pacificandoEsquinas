import copy
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tunnel_review import audit, apply_overrides
from tunnel_endpoints import one_way_portals


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=json.loads((ROOT/'data/processed/tunnels-all.json').read_text(encoding='utf-8'))['cases']
        # Fixed historical fixture: manual endpoint edits must not change unit-test inputs.
        cls.pilot=json.loads((ROOT/'data/processed/tunnels.json').read_text(encoding='utf-8'))['cases'][0]

    def test_main_difference_is_car_to_step_free(self):
        c=self.pilot
        a=audit(c,c['directions']['outbound'])
        self.assertTrue(a['comparison_usable'])
        self.assertAlmostEqual(a['extra_m'],126.1)

    def test_invalid_reference_has_no_difference(self):
        c=next(c for c in self.cases if c['id']=='osm_440436964')
        for d in c['directions'].values():
            a=audit(c,d)
            self.assertFalse(a['comparison_usable'])
            self.assertIsNone(a['extra_m'])

    def test_negative_difference_is_preserved(self):
        c=copy.deepcopy(self.pilot);d=c['directions']['outbound']
        d['routes']['step_free']['distance_m']=400
        self.assertLess(audit(c,d)['extra_m'],0)

    def test_distant_network_endpoints_are_flagged(self):
        c=copy.deepcopy(self.pilot)
        c['directions']['outbound']['routes']['step_free']['geometry']['coordinates'][0][0]+=.001
        self.assertFalse(audit(c,c['directions']['outbound'])['comparison_usable'])

    def test_saved_manual_endpoints_are_applied_exactly(self):
        path=ROOT/'data/tunnels/endpoint-overrides.json'
        if not path.exists():self.skipTest('No manual revisions imported')
        payload=json.loads(path.read_text(encoding='utf-8'))
        for item in payload['cases']:
            c=next(c for c in self.cases if c['id']==item['id'])
            self.assertEqual(c['endpoint_method'],'manual_map_review')
            for key in ('origin','destination'):self.assertEqual(c[key],item[key])

    def payload(self):
        c=self.cases[0]
        item={k:copy.deepcopy(c[k]) for k in ('id','origin','destination')}
        item['baseline']={k:c[k] for k in ('origin','destination')}
        return {'schema_version':1,'cases':[item]}

    def test_override_preserves_base_and_is_repeatable(self):
        p=self.payload();p['cases'][0]['origin'][0]+=.0001
        before=copy.deepcopy(self.cases)
        updated=apply_overrides(self.cases,p)
        self.assertEqual(before,self.cases)
        self.assertNotEqual(updated[0]['origin'],before[0]['origin'])
        self.assertEqual(updated,apply_overrides(updated,p))

    def test_rejects_bad_stale_duplicate_and_coincident_coordinates(self):
        for kind in ('nan','outside','stale','duplicate','coincident','unknown'):
            p=self.payload();item=p['cases'][0]
            if kind=='nan':item['origin'][0]=float('nan')
            if kind=='outside':item['origin'][0]=0
            if kind=='stale':item['baseline']['origin']=[0,0];item['origin'][0]+=.0001
            if kind=='duplicate':p['cases'].append(copy.deepcopy(item))
            if kind=='coincident':item['destination']=item['origin']
            if kind=='unknown':item['id']='missing'
            with self.subTest(kind=kind),self.assertRaises(ValueError):apply_overrides(self.cases,p)

    def test_saved_audits_match_recomputation(self):
        for c in self.cases:
            for d in c['directions'].values():self.assertEqual(audit(c,d),d['endpoint_audit'])

    def test_oneway_direction_and_opposite_carriageways(self):
        def w(i,ns,ow):return {'type':'way','id':i,'nodes':ns,'tags':{'oneway':ow}}
        self.assertEqual(one_way_portals([w(1,[1,2,3],'yes')],[1]),(1,3))
        self.assertEqual(one_way_portals([w(1,[1,2,3],'-1')],[1]),(3,1))
        self.assertIsNone(one_way_portals([w(1,[1,2],'yes'),w(2,[3,4],'yes')],[1,2]))
        self.assertIsNone(one_way_portals([w(1,[1,2],'no')],[1]))

    def test_every_single_direction_tunnel_primary_route_uses_target(self):
        checked=0
        for c in self.cases:
            if c.get('single_direction_tunnel'):
                checked+=1
                self.assertTrue(c['directions']['outbound']['valid_tunnel_crossing'],c['id'])
        self.assertGreater(checked,10)

    def test_manual_review_cannot_invert_oneway_reference(self):
        c=next(c for c in self.cases if c['id']=='osm_440436964')
        item={'id':c['id'],'origin':c['destination'],'destination':c['origin'],
              'baseline':{k:c[k] for k in ('origin','destination')}}
        with self.assertRaisesRegex(ValueError,'mano del túnel'):
            apply_overrides([c],{'schema_version':1,'cases':[item]})
