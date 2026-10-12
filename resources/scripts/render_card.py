#!/usr/bin/env python3
"""Render a portable advice card with static content and optional PNG export."""
import argparse
import datetime as dt
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import uuid


def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError('输入必须为对象')
    data = {}
    library = json.loads((Path(__file__).resolve().parent.parent / 'references/quotes.json').read_text(encoding='utf-8'))
    primary = raw.get('primary')
    quote_id = raw.get('quote_id')
    if not isinstance(primary, str) or primary not in library['coverage']:
        raise ValueError('primary 必须为已登记的能力域')
    match = next((q for q in library['quotes'] if q['id'] == quote_id), None)
    if match is None:
        raise ValueError('quote_id 未核验；请从 quotes.json 选择，不可临时编写金句')
    if primary not in match['domains']:
        raise ValueError('金句与主方法不匹配；没有匹配金句时先交文字建议')
    for key in ('quote', 'original', 'locator', 'translation'):
        if key in raw and raw[key] != match[key]:
            raise ValueError('不得覆盖已核验金句或出处：' + key)
        data[key] = match[key]
    data.update(primary=primary, quote_id=quote_id, quote_kind=match['quote_kind'],
                source_id=match['source_id'], verification=match['verification'])
    data['closing'] = ''  # Legacy field, never displayed.
    for key, limit in dict(title=60, situation=200, basis=300, method=120).items():
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f'{key} 需要 1–{limit} 字符的文本')
        data[key] = value.strip()
    experience = raw.get('experience', '')
    if not isinstance(experience, str) or len(experience) > 220:
        raise ValueError('experience 需要最多220字符的文本，可省略或留空')
    data['experience'] = experience.strip()
    advice = raw.get('advice')
    if not isinstance(advice, list) or not 1 <= len(advice) <= 3:
        raise ValueError('advice 需要 1–3 条建议')
    if any(not isinstance(s, str) or not s.strip() or len(s) > 220 for s in advice):
        raise ValueError('每条建议需要 1–220 字符')
    data['advice'] = [s.strip() for s in advice]
    sources = raw.get('sources', [])
    if not isinstance(sources, list) or len(sources) > 4:
        raise ValueError('来源最多四项')
    data['sources'] = []
    for s in sources:
        if not isinstance(s, dict) or not isinstance(s.get('label'), str) or not 1 <= len(s['label'].strip()) <= 100:
            raise ValueError('来源标签无效')
        url = s.get('url')
        if not isinstance(url, str) or len(url) > 2000 or any(c.isspace() for c in url):
            raise ValueError('来源链接无效')
        parts = urlsplit(url)
        if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username:
            raise ValueError('仅允许 HTTP(S) 来源')
        data['sources'].append({'label': s['label'].strip(), 'url': url})
    if not isinstance(raw.get('example', False), bool):
        raise ValueError('example 必须为布尔值')
    data.update(example=raw.get('example', False), id=str(uuid.uuid4()), version=4,
                created=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat())
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--png', action='store_true', help='同时使用 Pillow 导出无需浏览器的 PNG')
    parser.add_argument('--font', type=Path, help='PNG 使用的中文 TTF/OTF/TTC 字体')
    args = parser.parse_args()
    try:
        data = validate(json.loads(args.input.read_text(encoding='utf-8')))
        template = (Path(__file__).resolve().parent.parent / 'assets/advice-card.html').read_text(encoding='utf-8')
        esc = html.escape
        encoded = json.dumps(data, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
        values = {k.upper(): esc(data[k]) for k in ('title','situation','closing','basis','method','experience','quote','original','locator','translation')}
        values.update(DATE=data['created'][:10].replace('-', '.'),
                      EXAMPLE='<span>演示情境</span>' if data['example'] else '',
                      ADVICE=''.join('<p>' + esc(s) + '</p>' for s in data['advice']),
                      SOURCES=''.join('<li><a target="_blank" rel="noopener noreferrer" href="' + esc(s['url'], quote=True) + '">' + esc(s['label']) + '</a></li>' for s in data['sources']),
                      EXPERIENCEBLOCK=('<p>相关经历 · ' + esc(data['experience']) + '</p>') if data['experience'] else '',
                      DATA=encoded)
        result = re.sub(r'__([A-Z]+)__', lambda m: values[m[1]], template)
        args.out.mkdir(parents=True, exist_ok=True)
        stem = 'advice-' + data['created'][:10] + '-' + data['id'][:8]
        paths = {ext: (args.out / (stem + '.' + ext)).resolve() for ext in ('html', 'json')}
        with paths['html'].open('x', encoding='utf-8') as f:
            f.write(result)
        with paths['json'].open('x', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if args.png:
            from render_png import render_png
            png_path = (args.out / (stem + '.png')).resolve()
            try:
                render_png(data, png_path, args.font)
            except (ValueError, OSError) as error:
                print(json.dumps({**{k: str(v) for k, v in paths.items()}, 'png_error': str(error)}, ensure_ascii=False))
                parser.exit(2, f'HTML/JSON 已生成；PNG 未生成：{error}\n')
            paths['png'] = png_path
        print(json.dumps({k: str(v) for k, v in paths.items()}, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'无法生成建议卡：{error}\n')


if __name__ == '__main__':
    main()
