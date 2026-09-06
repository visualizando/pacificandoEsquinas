"""Behavioral checks runnable without GIS dependencies: python -m unittest discover -s tests -p test_tunnels.py"""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tunnels import permitted, route, meters, intersects, ROOT

def node(i,x,y=0,**tags):
    return {'type':'node','id':i,'lon':x,'lat':y,'tags':tags}

def way(i,ids,**tags):
    return {'type':'way','id':i,'nodes':ids,'tags':{'highway':'residential',**tags}}

class TunnelTests(unittest.TestCase):
    def test_metric_distance(self):
        self.assertAlmostEqual(meters([0,0],[0,.001]),111.195,places=2)

    def test_access_precedence_and_steps(self):
        self.assertTrue(permitted({'highway':'footway','access':'private','foot':'yes'},'walk'))
        self.assertFalse(permitted({'highway':'steps'},'step_free'))
        self.assertFalse(permitted({'highway':'footway','wheelchair':'no'},'step_free'))
        self.assertFalse(permitted({'highway':'secondary','foot':'no'},'walk'))
        self.assertFalse(permitted({'highway':'residential','sidewalk':'separate'},'walk'))

    def test_oneway_is_motor_only(self):
        es=[node(1,0),node(2,.001),way(1,[1,2],oneway='yes')]
        self.assertEqual(route(es,[.001,0],[0,0],'car')['status'],'no_path')
        self.assertEqual(route(es,[.001,0],[0,0],'walk')['status'],'ok')

    def test_step_free_uses_longer_alternative(self):
        es=[node(1,0),node(2,.001),node(3,.0005,.001),
            way(1,[1,2],highway='steps'),way(2,[1,3,2],highway='footway')]
        walk=route(es,[0,0],[.001,0],'walk'); free=route(es,[0,0],[.001,0],'step_free')
        self.assertGreater(free['distance_m'],walk['distance_m'])
        self.assertEqual(free['step_way_count'],0)
        self.assertEqual(walk['step_way_count'],1)

    def test_no_path_is_not_zero(self):
        es=[node(1,0),node(2,.0001),node(3,.001),node(4,.0011),way(1,[1,2]),way(2,[3,4])]
        r=route(es,[0,0],[.001,0],'walk')
        self.assertEqual(r['status'],'no_path'); self.assertNotIn('distance_m',r)

    def test_remote_snap_is_rejected(self):
        self.assertEqual(route([node(1,0),node(2,.001),way(1,[1,2])],[1,1],[0,0],'walk')['status'],'snap_too_far')

    def test_barrier_blocks_car(self):
        es=[node(1,0),node(2,.001,barrier='bollard'),node(3,.002),way(1,[1,2,3])]
        self.assertNotEqual(route(es,[0,0],[.002,0],'car')['status'],'ok')

    def test_no_turn_restriction(self):
        es=[node(1,0),node(2,.001),node(3,.001,.001),way(10,[1,2]),way(11,[2,3])]
        es.append({'type':'relation','id':1,'tags':{'type':'restriction','restriction':'no_left_turn'},'members':[
            {'role':'from','type':'way','ref':10},{'role':'to','type':'way','ref':11},{'role':'via','type':'node','ref':2}]})
        self.assertEqual(route(es,[0,0],[.001,.001],'car')['status'],'no_path')
        self.assertEqual(route(es,[0,0],[.001,.001],'walk')['status'],'ok')

    def test_no_uturn_does_not_block_straight(self):
        es=[node(1,0),node(2,.001),node(3,.002),way(10,[1,2,3])]
        es.append({'type':'relation','id':1,'tags':{'type':'restriction','restriction':'no_u_turn'},'members':[
            {'role':'from','type':'way','ref':10},{'role':'to','type':'way','ref':10},{'role':'via','type':'node','ref':2}]})
        self.assertEqual(route(es,[0,0],[.002,0],'car')['status'],'ok')

    def test_geometric_crossing(self):
        self.assertTrue(intersects([0,0],[2,2],[0,2],[2,0]))
        self.assertFalse(intersects([0,0],[1,1],[2,0],[2,3]))

    def test_delivered_snapshot_invariants(self):
        data=json.loads((ROOT/'data/processed/tunnels.json').read_text(encoding='utf8'))
        self.assertEqual(len(data['cases']),3)
        for c in data['cases']:
            for d in c['directions'].values():
                self.assertTrue(d['valid_tunnel_crossing'],c['id'])
                for mode,r in d['routes'].items():
                    self.assertEqual(r['status'],'ok',(c['id'],mode))
                    self.assertGreater(r['distance_m'],0)
                    self.assertLessEqual(max(r['snap_m']),45)
                    self.assertGreaterEqual(len(r['geometry']['coordinates']),2)
                self.assertEqual(d['routes']['step_free']['step_way_count'],0)
                self.assertGreaterEqual(d['routes']['step_free']['distance_m'],d['routes']['walk']['distance_m'])

if __name__=='__main__': unittest.main()
