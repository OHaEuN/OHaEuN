"""Convert downloaded Tistory post pages into Jekyll markdown posts.

usage: python3 -I tools/tistory_import.py <download_dir> <repo_dir>

<download_dir> holds post_<id>.html files saved from https://oaeuhn.tistory.com/<id>.
"""
import base64
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup, NavigableString, Tag, Comment

DL, REPO = sys.argv[1], sys.argv[2]
BLOG = 'https://oaeuhn.tistory.com'
POST_IDS = set()

EXT_BY_CT = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/gif': 'gif', 'image/webp': 'webp',
             'image/svg+xml': 'svg', 'video/mp4': 'mp4'}


def fetch(url):
    import time
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': BLOG + '/'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), r.headers.get('Content-Type', '').split(';')[0].strip()
        except Exception as e:
            if attempt == 5:
                raise
            print('  retry', attempt, e)
            time.sleep(2 ** attempt)


class Assets:
    def __init__(self, pid):
        self.pid = pid
        self.n = 0
        self.dir = os.path.join(REPO, 'assets', 'posts', str(pid))
        self.cache = {}

    @staticmethod
    def key(src):
        # Signed CDN URLs differ only in their query string; dedupe on the path.
        return src.split('?')[0] if 'kakaocdn.net' in src else src

    def save(self, src, name_hint=None):
        if self.key(src) in self.cache:
            return self.cache[self.key(src)]
        if src.startswith('data:'):
            head, b64 = src.split(',', 1)
            ct = head[5:].split(';')[0]
            data = base64.b64decode(b64)
        else:
            if src.startswith('//'):
                src_url = 'https:' + src
            else:
                src_url = src
            data, ct = fetch(src_url)
        ext = EXT_BY_CT.get(ct)
        if not ext:
            path = urllib.parse.urlparse(src).path
            ext = os.path.splitext(path)[1].lstrip('.').lower() or 'bin'
        self.n += 1
        if name_hint:
            fname = name_hint
        else:
            fname = f'{self.n:02d}.{ext}'
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, fname), 'wb') as f:
            f.write(data)
        url = f'/assets/posts/{self.pid}/{urllib.parse.quote(fname)}'
        self.cache[self.key(src)] = url
        return url


def fix_link(href):
    if not href:
        return href
    if href.startswith('//'):
        href = 'https:' + href
    m = re.match(r'https?://oaeuhn\.tistory\.com(/m)?/(\d+)(.*)$', href)
    if m and int(m.group(2)) in POST_IDS:
        return f'/{m.group(2)}{m.group(3)}'
    return href


def esc_md(text):
    # Escape characters that would otherwise start markdown syntax inline.
    text = text.replace('\\', '\\\\')
    text = re.sub(r'([*_`\[\]<>|])', r'\\\1', text)
    text = text.replace('{{', '{\\{').replace('{%', '{\\%')
    return text


KEEP_STYLE_PROPS = ('color', 'background-color')


def kept_style(tag):
    style = tag.get('style') or ''
    props = []
    for decl in style.split(';'):
        if ':' not in decl:
            continue
        k, v = decl.split(':', 1)
        k, v = k.strip().lower(), v.strip()
        if k in KEEP_STYLE_PROPS:
            # Default text colors carry no meaning on the new site.
            if k == 'color' and v.lower() in ('#000000', '#333333', '#000', 'rgb(0, 0, 0)', '#212529', '#1f2937'):
                continue
            props.append(f'{k}: {v}')
    return '; '.join(props)


def inline(node):
    """Render inline content to markdown (with inline HTML where markdown has no equivalent)."""
    if isinstance(node, Comment):
        return ''
    if isinstance(node, NavigableString):
        t = str(node).replace(' ', ' ').replace('​', '')
        t = re.sub(r'\s+', ' ', t)
        return esc_md(t)
    name = node.name
    inner = ''.join(inline(c) for c in node.children)
    if name == 'br':
        return '<br>'
    if name in ('b', 'strong'):
        return wrap(inner, '**')
    if name in ('i', 'em'):
        return wrap(inner, '*')
    if name == 's':
        return wrap(inner, '~~')
    if name == 'u':
        return f'<u>{inner}</u>' if inner.strip() else inner
    if name == 'code':
        raw = node.get_text().replace(' ', ' ')
        if not raw.strip():
            return raw
        tick = '``' if '`' in raw else '`'
        pad = ' ' if raw.startswith('`') or raw.endswith('`') else ''
        return f'{tick}{pad}{raw}{pad}{tick}'
    if name == 'a':
        href = fix_link(node.get('href'))
        if not href or not inner.strip():
            return inner
        return f'[{inner}]({href.replace(" ", "%20").replace(")", "%29")})'
    if name == 'span':
        style = kept_style(node)
        if style and inner.strip():
            return f'<span style="{style}">{inner}</span>'
        return inner
    if name == 'img':
        return ''
    return inner


def wrap(inner, mark):
    if not inner.strip():
        return inner
    lead = inner[:len(inner) - len(inner.lstrip())]
    trail = inner[len(inner.rstrip()):]
    return f'{lead}{mark}{inner.strip()}{mark}{trail}'


def clean_inline(s):
    s = s.strip()
    s = re.sub(r'(<br>\s*)+$', '', s)
    s = re.sub(r'^(\s*<br>)+', '', s)
    return s.strip()


class Converter:
    def __init__(self, pid):
        self.assets = Assets(pid)
        self.pid = pid
        self.first_image = None
        self.main_size = 'size16'

    def img_url(self, img):
        src = img.get('src') or ''
        span = img.find_parent('span', attrs={'data-url': True})
        if span and not src.startswith('data:'):
            src = span['data-url']
        url = self.assets.save(src)
        if self.first_image is None:
            self.first_image = url
        return url

    def blocks(self, node):
        out = []
        for c in node.children:
            out.extend(self.block(c))
        return out

    def block(self, node):
        if isinstance(node, Comment):
            return []
        if isinstance(node, NavigableString):
            t = clean_inline(inline(node))
            return [t] if t else []
        name = node.name
        cls = node.get('class') or []
        if name == 'p':
            figs = node.find_all('figure', recursive=False)
            if figs:
                return self.blocks(node)
            t = clean_inline(inline(node))
            if not t:
                # Tistory uses empty paragraphs as vertical spacing.
                return ['&nbsp;']
            if re.match(r'^(#{1,6} |[-+*] |\d+\. |> |---)', t):
                t = '\\' + t
            size = node.get('data-ke-size')
            if size and size != self.main_size and size != 'size16':
                t += '\n{: data-ke-size="%s"}' % size
            return [t]
        if re.fullmatch(r'h[1-6]', name):
            t = clean_inline(inline(node)).replace('<br>', ' ')
            return [f'{"#" * int(name[1])} {t}'] if t else []
        if name in ('ul', 'ol'):
            return [self.list_md(node, 0)]
        if name == 'pre':
            return [self.code_md(node)]
        if name == 'blockquote':
            inner = self.blocks(node)
            body = '\n>\n'.join('\n'.join('> ' + ln if ln else '>' for ln in b.split('\n')) for b in inner)
            style = node.get('data-ke-style')
            if style:
                body += '\n{: data-ke-style="%s"}' % style
            return [body]
        if name == 'hr':
            style = node.get('data-ke-style') or 'style1'
            return ['<hr contenteditable="false" data-ke-type="horizontalRule" data-ke-style="%s" />' % style]
        if name == 'table':
            return [self.table_md(node)]
        if name == 'figure':
            return [self.figure_md(node)]
        if name == 'div' and node.get('data-ke-type') == 'moreLess':
            content = node.find('div', class_='moreless-content')
            inner = '\n\n'.join(self.blocks(content))
            more = node.get('data-text-more', '더보기')
            less = node.get('data-text-less', '닫기')
            return [f'<div data-ke-type="moreLess" data-text-more="{more}" data-text-less="{less}" markdown="1">\n'
                    f'<a class="btn-toggle-moreless">{more}</a>\n'
                    f'<div class="moreless-content" markdown="1">\n\n{inner}\n\n</div>\n</div>']
        if name == 'div' and node.get('data-node-type') == 'expand':
            inner = '\n\n'.join(self.blocks(node))
            return [inner]
        if name in ('div', 'span', 'section', 'tbody'):
            return self.blocks(node)
        if name == 'img':
            return [f'![]({self.img_url(node)})']
        t = clean_inline(inline(node))
        return [t] if t else []

    def list_md(self, node, depth):
        ordered = node.name == 'ol'
        lines = []
        indent = '   ' * depth if ordered else '  ' * depth
        start = int(node.get('start', 1)) if ordered else 1
        for i, li in enumerate(node.find_all('li', recursive=False)):
            marker = f'{start + i}.' if ordered else '-'
            pad = ' ' * (len(marker) + 1)
            text_parts, sub_blocks = [], []
            for c in li.children:
                if isinstance(c, Tag) and c.name in ('ul', 'ol'):
                    sub_blocks.append(('list', c))
                elif isinstance(c, Tag) and c.name in ('pre', 'figure', 'table', 'blockquote'):
                    sub_blocks.append(('block', c))
                elif isinstance(c, Tag) and c.name == 'p':
                    if text_parts:
                        text_parts.append('<br>')
                    text_parts.append(inline(c))
                else:
                    text_parts.append(inline(c))
            text = clean_inline(''.join(text_parts))
            lines.append(f'{indent}{marker} {text}')
            for kind, c in sub_blocks:
                if kind == 'list':
                    sub = self.list_md(c, 0)
                else:
                    sub = '\n\n'.join(self.block(c))
                lines.append('\n'.join((indent + pad + ln) if ln else '' for ln in sub.split('\n')))
        return '\n'.join(lines)

    def code_md(self, pre):
        lang = pre.get('data-ke-language') or ''
        code_el = pre.find('code')
        if not lang and code_el is not None:
            lang = next((c[9:] for c in (code_el.get('class') or []) if c.startswith('language-')), '')
        if lang in ('plaintext', 'text'):
            lang = ''
        code = pre.find('code') or pre
        text = code.get_text().replace(' ', ' ').rstrip('\n')
        fence = '```'
        while fence in text:
            fence += '`'
        body = f'{fence}{lang}\n{text}\n{fence}'
        if '{{' in text or '{%' in text:
            body = '{% raw %}\n' + body + '\n{% endraw %}'
        return body

    def table_md(self, table):
        rows = table.find_all('tr')
        simple = True
        grid = []
        for tr in rows:
            cells = tr.find_all(['td', 'th'], recursive=False)
            row = []
            for c in cells:
                if c.get('colspan') or c.get('rowspan') or c.find(['ul', 'ol', 'pre', 'table', 'figure', 'img']):
                    simple = False
                parts = []
                for ch in c.children:
                    if isinstance(ch, Tag) and ch.name == 'p':
                        parts.append(clean_inline(inline(ch)))
                    else:
                        parts.append(clean_inline(inline(ch)))
                row.append('<br>'.join(p for p in parts if p).replace('|', '\\|'))
            grid.append(row)
        if simple and grid and len({len(r) for r in grid}) == 1 and len(grid[0]) > 0:
            n = len(grid[0])
            head, body = grid[0], grid[1:]
            lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * n]
            lines += ['| ' + ' | '.join(r) + ' |' for r in body]
            style = table.get('data-ke-style')
            md = '\n'.join(lines)
            md += '\n{: data-ke-align="alignLeft"%s}' % (f' data-ke-style="{style}"' if style else '')
            return md
        return self.raw_html(table)

    def raw_html(self, node):
        node = BeautifulSoup(str(node), 'html.parser')
        for img in node.find_all('img'):
            url = self.img_url(img)
            new = node.new_tag('img', src=url)
            for a in ('width', 'height', 'alt'):
                if img.get(a):
                    new[a] = img[a]
            img.replace_with(new)
        for t in node.find_all(True):
            for a in list(t.attrs):
                if a.startswith('data-prosemirror') or a in ('data-pm-slice', 'data-start', 'data-end', 'id', 'onerror', 'srcset', 'data-phocus', 'data-url'):
                    del t[a]
            if t.get('style'):
                st = '; '.join(d.strip() for d in t['style'].split(';')
                               if d.strip() and not d.strip().lower().startswith('font-family'))
                if st:
                    t['style'] = st
                else:
                    del t['style']
            if t.name == 'a' and t.get('href'):
                t['href'] = fix_link(t['href'])
        s = str(node)
        s = re.sub(r'\n\s*\n', '\n', s)
        return s

    def figure_md(self, fig):
        cls = fig.get('class') or []
        ktype = fig.get('data-ke-type')
        if ktype == 'opengraph':
            href = fig.get('data-og-source-url') or fig.get('data-og-url')
            title = html.escape(fig.get('data-og-title', ''), quote=True)
            desc = html.escape(fig.get('data-og-description', ''), quote=True)
            host = html.escape(fig.get('data-og-host', ''), quote=True)
            img = fig.get('data-og-image') or ''
            bg = ''
            if img:
                try:
                    bg = self.assets.save(img)
                except Exception as e:  # og thumbnails are optional decoration
                    print('  og image failed', img[:80], e)
            return (f'<figure data-ke-type="opengraph" data-ke-align="alignCenter" data-og-type="{fig.get("data-og-type", "")}">'
                    f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">'
                    f'<div class="og-image" style="background-image: url(\'{bg}\');">&nbsp;</div>'
                    f'<div class="og-text"><p class="og-title">{title}</p><p class="og-desc">{desc}</p><p class="og-host">{host}</p></div>'
                    f'</a></figure>')
        if 'fileblock' in cls:
            a = fig.find('a')
            name = fig.select_one('.filename .name').get_text(strip=True)
            size = fig.select_one('.size').get_text(strip=True)
            ext = os.path.splitext(name)[1] or '.bin'
            self.files = getattr(self, 'files', 0) + 1
            url = self.assets.save(a['href'], name_hint=f'attachment-{self.files:02d}{ext}')
            return (f'<figure class="fileblock" data-ke-align="alignCenter"><a href="{url}" download>'
                    f'<div class="image"></div><div class="desc"><div class="filename"><span class="name">{html.escape(name)}</span></div>'
                    f'<div class="size">{html.escape(size)}</div></div></a></figure>')
        if 'imagegridblock' in cls:
            return self.raw_html(fig)
        imgs = fig.find_all('img')
        if not imgs:
            return self.raw_html(fig)
        img = imgs[0]
        url = self.img_url(img)
        cap = fig.find('figcaption')
        caption = clean_inline(inline(cap)) if cap else ''
        align = next((c for c in cls if c.startswith('align')), None) or fig.get('data-ke-align') or 'alignCenter'
        attrs = []
        w = img.get('width')
        if w and fig.get('data-origin-width') and w != fig.get('data-origin-width'):
            attrs.append(f'width="{w}"')
        md = f'![{esc_md(img.get("alt") or "")}]({url})'
        if attrs:
            md += '{: ' + ' '.join(attrs) + '}'
        out = f'<figure class="imageblock {align}" markdown="1">\n{md}\n'
        if caption:
            out += f'<figcaption>{caption}</figcaption>\n'
        return out + '</figure>'


def yaml_str(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    pages = {}
    for fn in os.listdir(DL):
        m = re.fullmatch(r'post_(\d+)\.html', fn)
        if not m:
            continue
        s = open(os.path.join(DL, fn), encoding='utf-8').read()
        if 'id="article-view"' not in s:
            continue
        pages[int(m.group(1))] = s
    POST_IDS.update(pages)
    posts_dir = os.path.join(REPO, '_posts')
    os.makedirs(posts_dir, exist_ok=True)
    for pid in sorted(pages):
        s = pages[pid]
        soup = BeautifulSoup(s, 'html.parser')

        def meta(prop):
            t = soup.find('meta', attrs={'property': prop}) or soup.find('meta', attrs={'name': prop})
            return t['content'] if t else ''
        title = meta('og:title')
        published = meta('article:published_time')
        modified = meta('article:modified_time')
        cat_el = soup.select_one('.hgroup .category')
        category = cat_el.get_text(strip=True) if cat_el else ''
        if category == '카테고리 없음':
            category = ''
        tags = [a.get_text(strip=True) for a in soup.select('.tags .items a')]
        content = soup.select_one('#article-view .tt_article_useless_p_margin')
        conv = Converter(pid)
        from collections import Counter
        sizes = Counter(p.get('data-ke-size') for p in content.find_all('p') if p.get('data-ke-size') and p.get_text(strip=True))
        conv.main_size = sizes.most_common(1)[0][0] if sizes else 'size16'
        fonts = Counter()
        for sp in content.find_all('span', style=True):
            m = re.search(r"font-family:\s*([^;]+)", sp['style'])
            if m:
                fonts[m.group(1).split(',')[0].strip().strip("'\"")] += len(sp.get_text(strip=True))
        total = len(content.get_text(strip=True)) or 1
        main_font = fonts.most_common(1)[0][0] if fonts and fonts.most_common(1)[0][1] > total * 0.5 else ''
        blocks = conv.blocks(content)
        # Collapse runs of more than three spacer paragraphs.
        md_blocks = []
        for b in blocks:
            md_blocks.append(b)
        while md_blocks and md_blocks[-1] == '&nbsp;':
            md_blocks.pop()
        while md_blocks and md_blocks[0] == '&nbsp;':
            md_blocks.pop(0)
        body = '\n\n'.join(md_blocks) + '\n'
        excerpt = re.sub(r'\s+', ' ', content.get_text(' ')).replace(' ', ' ').strip()[:300]
        fm = ['---', 'layout: post', f'title: {yaml_str(title)}', f'date: {published[:19].replace("T", " ")} +0900']
        if modified:
            fm.append(f'last_modified_at: {modified[:19].replace("T", " ")} +0900')
        fm.append(f'tistory_id: {pid}')
        fm.append(f'permalink: /{pid}')
        classes = []
        if conv.main_size != 'size16':
            classes.append('ke-' + conv.main_size)
        if main_font:
            classes.append('font-' + re.sub(r'[^a-z0-9]+', '-', main_font.lower()).strip('-'))
        if classes:
            fm.append(f'content_class: {" ".join(classes)}')
        if category:
            fm.append(f'category: {yaml_str(category)}')
        else:
            fm.append('category: ""')
        fm.append('tags: [' + ', '.join(yaml_str(t) for t in tags) + ']')
        og = meta('og:image')
        q = urllib.parse.parse_qs(urllib.parse.urlparse(og).query).get('fname')
        if q and 'tistory_admin' in q[0]:
            q = None  # Tistory's default placeholder; the post has no representative image.
        if q:
            if conv.assets.key(q[0]) in conv.assets.cache:
                conv.first_image = conv.assets.cache[conv.assets.key(q[0])]
            else:
                conv.first_image = conv.assets.save(q[0], name_hint='thumbnail.' + q[0].split('?')[0].rsplit('.', 1)[-1])
        if conv.first_image:
            fm.append(f'thumbnail: {conv.first_image}')
            fm.append(f'image: {conv.first_image}')
        fm.append(f'description: {yaml_str(excerpt)}')
        fm.append('---')
        fname = f'{published[:10]}-{pid}.md'
        with open(os.path.join(posts_dir, fname), 'w', encoding='utf-8') as f:
            f.write('\n'.join(fm) + '\n\n' + body)
        print(pid, fname, title, category, len(tags), 'assets:', conv.assets.n)


if __name__ == '__main__':
    main()
