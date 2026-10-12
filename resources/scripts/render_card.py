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
    for key, limit in dict(title=60, situation=200, closing=100, basis=300,
                           method=120, experience=220, quote=160, original=400, locator=200, translation=100).items():
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f'{key} 需要 1–{limit} 字符的文本')
        data[key] = value.strip()
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
    data.update(example=raw.get('example', False), id=str(uuid.uuid4()), version=3,
                created=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat())
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, required=True)
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
                      DATA=encoded)
        result = re.sub(r'__([A-Z]+)__', lambda m: values[m[1]], template)
        args.out.mkdir(parents=True, exist_ok=True)
        stem = 'advice-' + data['created'][:10] + '-' + data['id'][:8]
        paths = {ext: (args.out / (stem + '.' + ext)).resolve() for ext in ('html', 'json')}
        with paths['html'].open('x', encoding='utf-8') as f:
            f.write(result)
        with paths['json'].open('x', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(json.dumps({k: str(v) for k, v in paths.items()}, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'无法生成建议卡：{error}\n')


if __name__ == '__main__':
    main()
