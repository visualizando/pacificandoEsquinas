from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if tag in ('script','link','img','a'):
            value=attrs.get('src',attrs.get('href',''))
            if value:self.links.append(value)

class PageTests(unittest.TestCase):
    def test_tunnel_page_integrity(self):
        page=Page();page.feed((ROOT/'web/tuneles.html').read_text(encoding='utf-8'))
        self.assertEqual(len(page.ids),len(set(page.ids)))
        self.assertTrue({'comparison-body','comparison-search','tunnel-case','inventory-map','tunnel-metrics'}<=set(page.ids))
        self.assertNotIn('comparison-direction',page.ids)
        self.assertNotIn('tunnel-direction',page.ids)
        for link in page.links:
            parsed=urlsplit(link)
            if not parsed.scheme and parsed.path:self.assertTrue((ROOT/'web'/unquote(parsed.path)).exists(),link)
            elif not parsed.path and parsed.fragment:self.assertIn(parsed.fragment,page.ids)

if __name__=='__main__':unittest.main()
