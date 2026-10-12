"""Check distributable capability/link integrity, not coaching effectiveness."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SkillResourceTests(unittest.TestCase):
    def test_capability_sections_and_relative_links(self):
        cards = list((ROOT/'references/capabilities').glob('*.md'))
        self.assertEqual(len(cards), 7)
        for card in cards:
            text = card.read_text(encoding='utf-8')
            for section in ['R', 'I', 'A1', 'A2', 'E', 'B']:
                with self.subTest(card=card.name, section=section):
                    self.assertRegex(text, r'(?m)^## '+section+r'\s')
        for file in ROOT.rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf-8')):
                if '://' in link or link.startswith('#'):
                    continue
                target = link.split('#', 1)[0]
                if target:
                    with self.subTest(file=file.name, link=link):
                        self.assertTrue((file.parent/target).exists())

    def test_quotes_have_traceable_source_and_honest_status(self):
        lib = json.loads((ROOT/'resources/references/quotes.json').read_text())
        ids = {q['id'] for q in lib['quotes']}
        self.assertEqual(len(ids), len(lib['quotes']))
        self.assertRegex(lib['source']['sha256'], r'^[0-9a-f]{64}$')
        for q in lib['quotes']:
            with self.subTest(id=q['id']):
                self.assertEqual(q['source_id'], lib['source']['id'])
                self.assertTrue(1 <= q['pdf_page'] <= 87)
                self.assertTrue(1 <= q['chapter'] <= 10)
                self.assertTrue(q['use_when'] and q['avoid'])
                self.assertIn('自译', q['translation'])
                for domain in q['domains']:
                    self.assertIn(q['id'], lib['coverage'][domain])
                    self.assertTrue((ROOT/'references/capabilities'/f'{domain}.md').is_file())
