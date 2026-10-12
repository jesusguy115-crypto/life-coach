#!/usr/bin/env python3
"""Browser-free, two-section advice-card PNG rendering (optional Pillow)."""
from pathlib import Path
import os


def find_font(explicit=None):
    """Find a known CJK font; explicit font files must contain Chinese glyphs."""
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ValueError(f'字体不存在：{path}；请用 --font 指定中文 TTF/OTF/TTC 字体')
        return path
    candidates = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/Supplemental/Songti.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/msyh.ttc'),
        str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/simhei.ttf'),
    ]
    for item in candidates:
        if Path(item).is_file():
            return Path(item)
    raise ValueError('未找到中文字体；安装 Noto Sans CJK，或用 --font /path/to/chinese-font.ttf 指定中文字体')


def render_png(data, destination, font_path=None):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise ValueError('PNG 导出需要 Pillow；请执行 python -m pip install Pillow 后重试。HTML/JSON 导出无需此依赖。') from error
    path = find_font(font_path)
    fonts = {}
    def font(size):
        if size not in fonts:
            try:
                fonts[size] = ImageFont.truetype(str(path), size)
            except OSError as error:
                raise ValueError(f'无法读取字体 {path}；请用 --font 指定中文 TTF/OTF/TTC 字体') from error
        return fonts[size]
    width, margin = 1080, 90
    measure = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    commands, y = [], 74
    ink, muted, accent = '#263c43', '#5d6b6e', '#99482f'
    def block(text, size=30, color=ink, gap=22):
        nonlocal y
        lines, current = [], ''
        for character in str(text):
            if character == '\n':
                lines.append(current)
                current = ''
            elif current and measure.textlength(current + character, font=font(size)) > width - 2 * margin:
                if character in '，。！？；：、）】》”’' and len(current) > 1:
                    lines.append(current[:-1])
                    current = current[-1] + character
                else:
                    lines.append(current)
                    current = character
            else:
                current += character
        lines.append(current)
        line_height = max(round(size * 1.7), sum(font(size).getmetrics()) + 4)
        for line in lines:
            commands.append(('text', line, size, color, y))
            y += line_height
        y += gap
    def rule():
        nonlocal y
        y += 12
        commands.append(('line', '', 0, '#c8c9be', y))
        y += 30
    block('身心合一的奇迹力量 · 给此刻的你', 26, muted)
    block(data['created'][:10] + (' · 演示情境' if data['example'] else ''), 21, muted, 8)
    rule()
    block('01 · 给你的建议', 24, accent)
    block(data['title'], 46, ink, 30)
    block(data['situation'], 28, muted)
    for advice in data['advice']:
        block(advice, 32)
    block('本次方法 · ' + data['method'], 24, muted)
    rule()
    block('02 · 书中金句', 24, accent)
    block('“' + data['quote'] + '”', 40, accent)
    block('《身心合一的奇迹力量》 · W. Timothy Gallwey', 24, muted)
    block(data['locator'] + ' · ' + data['translation'], 22, muted)
    if data.get('experience'):
        block('相关经历 · ' + data['experience'], 24, muted)
    # Full evidence and source URLs remain in the companion JSON and HTML.
    block('AI 辅助建议', 21, muted, 0)
    canvas = Image.new('RGB', (width, y + 65), '#fcf9f1')
    draw = ImageDraw.Draw(canvas)
    for kind, value, size, color, top in commands:
        if kind == 'line':
            draw.line((margin, top, width - margin, top), fill=color, width=2)
        else:
            draw.text((margin, top), value, font=font(size), fill=color, anchor='lt')
    canvas.save(destination, format='PNG')
    return width, canvas.height
