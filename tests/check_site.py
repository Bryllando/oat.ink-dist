"""Validate every Oat route/asset and the complete PHP download."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
UPSTREAM = ROOT / 'site/upstream'

class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links, self.assets, self.ids = [], [], []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('id'): self.ids.append(values['id'])
        if tag == 'a': self.links.append(values)
        if tag in ('script', 'img') and values.get('src'): self.assets.append(values['src'])
        if tag == 'link' and values.get('href'): self.assets.append(values['href'])

def local_target(url, page):
    path = unquote(urlsplit(url).path)
    target = DIST / path.lstrip('/') if path.startswith('/') else page.parent / path
    target = target.resolve()
    assert target.is_relative_to(DIST.resolve()), url
    if target.is_dir(): target = target / 'index.html'
    return target

pages = list(DIST.rglob('*.html'))
parsed = {file: Page(file.read_text(encoding='utf-8')) for file in pages}
for file in UPSTREAM.rglob('*'):
    if not file.is_file() or file.suffix == '.html' or file.name in ('robots.txt', 'sitemap.xml'): continue
    assert file.read_bytes() == (DIST / file.relative_to(UPSTREAM)).read_bytes(), file
for file in pages:
    html = file.read_text(encoding='utf-8')
    original = (UPSTREAM / file.relative_to(DIST)).read_text(encoding='utf-8')
    if file.name == '404.html':
        assert html == original
        continue
    page = parsed[file]
    assert page.ids == Page(original).ids, file
    links = [link for link in page.links if 'download' in link]
    assert len(links) == 2 and all(link['href'] == '/downloads/oat.ink-dist.zip' for link in links), file
    # Removing only our two links, stylesheet and host metadata restores upstream exactly.
    restored = re.sub(r'<a class="button small systems-download[^>]+>Download</a>', '', html)
    restored = restored.replace('<link href="/download.css" rel="stylesheet">', '').replace('https://oatink-dist.vercel.app/', 'https://oat.ink/')
    assert restored == original, file
    for asset in page.assets:
        assert not urlsplit(asset).scheme and not asset.startswith('//'), (file, asset)
        assert local_target(asset, file).is_file(), (file, asset)
    for link in page.links:
        href = link.get('href', '')
        if not href or urlsplit(href).scheme or href.startswith('//'): continue
        target = local_target(href, file)
        assert target.is_file(), (file, href)
        fragment = unquote(urlsplit(href).fragment)
        if fragment and target.suffix == '.html':
            assert fragment in parsed[target].ids, (file, href)
for css in DIST.rglob('*.css'):
    assert not re.search(r'@import|url\([\s"\x27]*https?://', css.read_text(encoding='utf-8'), re.I), css
for js in DIST.rglob('*.js'):
    result = subprocess.run(['node', '--check', str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
metadata = json.loads((DIST / 'collection.json').read_text(encoding='utf-8'))
assert len(metadata['projects']) == 44
archive = DIST / metadata['download']['file']
assert archive.stat().st_size == metadata['download']['bytes']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == metadata['download']['sha256']
with ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    names = bundle.namelist()
    assert len(names) == len(set(names))
    assert all(name.startswith('oat.ink-dist/') and '..' not in Path(name).parts for name in names)
    assert not any('/.work/' in name or '/tests/' in name or '/.git/' in name for name in names)
    for project in metadata['projects']:
        assert 'oat.ink-dist/' + project['folder'] + '/index.php' in names
    assert 'oat.ink-dist/SystemMorpher/builder.php' in names
    assert b'System Setup' in bundle.read('oat.ink-dist/SystemMorpher/builder.php')
    assert b'Copyright (c) 2026 Kailash Nadh' in bundle.read('oat.ink-dist/OAT-LICENSE.txt')
    for name in ('deploy_exam.bat', 'deploy_exam.ps1', 'README.md', 'assets/css/oat.min.css'):
        assert 'oat.ink-dist/' + name in names
configuration = json.loads((ROOT / 'vercel.json').read_text())
assert configuration['outputDirectory'] == 'dist' and configuration['buildCommand'] == ''
assert configuration['headers'][0]['source'] == '/downloads/oat.ink-dist.zip'
assert configuration['headers'][0]['headers'][0]['value'] == 'attachment; filename="oat.ink-dist.zip"'
print(f'PASS: {len(pages)} original Oat pages, local links/fragments and assets; unchanged SVG/CSS/JS; JavaScript syntax; 44-project ZIP integrity, root folder and SHA-256; license; Vercel configuration.')
