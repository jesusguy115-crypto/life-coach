"""Run: python -m unittest discover -s tests -v (Pillow enables PNG checks)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render_card import validate
from render_png import find_font, render_png


def sample():
    return dict(title='过去总这样，不代表只能这样', situation='写几句就回头修改',
                basis='按第6章习惯改变方法改编', method='第6章，观察习惯并尝试新做法',
                experience='演示数据，测试用', primary='habit', quote_id='habit-past',
                advice=['先观察何时回头，再尝试写完一个意思后检查。'],
                sources=[dict(label='来源', url='https://example.org/book')], example=True)


class ValidationTests(unittest.TestCase):
    def test_missing_and_malformed_fields(self):
        for value in [None, [], 'x', {}, dict(sample(), advice=[]), dict(sample(), title=123), dict(sample(), example='yes')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(value)

    def test_quote_identity_and_domain(self):
        for edit in [dict(quote_id='invented'), dict(primary='observe'), dict(quote='编造金句'), dict(original='fake'), dict(locator='假页码')]:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                validate(dict(sample(), **edit))
        actual = validate(sample())
        self.assertEqual(actual['quote_id'], 'habit-past')
        self.assertIn('自译', actual['translation'])

    def test_every_available_quote_renders_and_gaps_are_explicit(self):
        library = json.loads((ROOT/'references/quotes.json').read_text())
        for quote in library['quotes']:
            for domain in quote['domains']:
                with self.subTest(quote=quote['id'], domain=domain):
                    result = validate(dict(sample(), primary=domain, quote_id=quote['id']))
                    self.assertEqual(result['original'], quote['original'])
                    self.assertFalse(quote['formal_edition_verified'])
        self.assertEqual(set(library['coverage']), {'observe','learning','habit','attention','motives','competition','future'})
        self.assertTrue(any(not ids for ids in library['coverage'].values()))

    def test_unsafe_urls(self):
        for url in ['javascript:alert(1)', 'file:///tmp/a', 'https://u:p@example.org', 'https://example.org/ a', '//example.org', 'https://']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate(dict(sample(), sources=[dict(label='source', url=url)]))

    def test_font_error_is_actionable(self):
        with self.assertRaisesRegex(ValueError, '--font'):
            find_font('/nonexistent/font.ttf')

    def test_missing_pillow_is_actionable(self):
        with mock.patch.dict(sys.modules, {'PIL': None}):
            with self.assertRaisesRegex(ValueError, 'pip install Pillow'):
                render_png(validate(sample()), '/unused.png')

    def test_cli_escaping_and_malformed_json(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            raw = sample()
            raw['title'] = '<script>alert(1)</script>'
            raw['sources'][0]['label'] = '<b>unsafe</b>'
            (p / 'input.json').write_text(json.dumps(raw), encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/render_card.py'), str(p/'input.json'), '--out', str(p/'out')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = json.loads(result.stdout)
            page = Path(paths['html']).read_text()
            self.assertNotIn('<script>alert(1)</script>', page)
            self.assertIn('&lt;script&gt;', page)
            self.assertIn('\\u003cscript', page)
            self.assertEqual(json.loads(Path(paths['json']).read_text())['title'], raw['title'])
            (p/'input.json').write_text('{bad')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/render_card.py'), str(p/'input.json'), '--out', str(p/'out')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('无法生成建议卡', result.stderr)

    def test_png_failure_preserves_html_and_reports_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p/'input.json').write_text(json.dumps(sample()))
            result = subprocess.run([sys.executable, str(ROOT/'scripts/render_card.py'), str(p/'input.json'), '--out', str(p/'out'), '--png', '--font', '/missing/font.ttf'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            paths = json.loads(result.stdout)
            self.assertIn('png_error', paths)
            self.assertNotIn('png', paths)
            self.assertTrue(Path(paths['html']).is_file())
            self.assertTrue(Path(paths['json']).is_file())

    def test_png_signature_dimensions_and_long_content(self):
        try:
            from PIL import Image
            cjk_font = find_font()
        except (ImportError, ValueError) as error:
            self.skipTest(str(error))
        with tempfile.TemporaryDirectory() as folder:
            short = Path(folder)/'short.png'
            long = Path(folder)/'long.png'
            render_png(validate(sample()), short, cjk_font)
            raw = sample()
            raw.update(title='长标题测试' * 12, situation='中文场景' * 50,
                       advice=['观察细节并记录实际发生的事情。' * 12] * 3,
                       sources=[dict(label='长来源', url='https://example.org/' + 'x'*1500)])
            render_png(validate(raw), long, cjk_font)
            self.assertEqual(long.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
            with Image.open(short) as a, Image.open(long) as b:
                self.assertEqual(b.width, 1080)
                self.assertGreater(b.height, a.height + 500)
                self.assertLess(b.height, 15000)
                # All ink stays inside the horizontal safety margin.
                self.assertEqual(b.getpixel((0, b.height//2)), (252, 249, 241))
            (Path(folder)/'input.json').write_text(json.dumps(sample()))
            result = subprocess.run([sys.executable, str(ROOT/'scripts/render_card.py'), str(Path(folder)/'input.json'), '--out', folder, '--png', '--font', str(cjk_font)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(Path(json.loads(result.stdout)['png']).is_file())


if __name__ == '__main__':
    unittest.main()
