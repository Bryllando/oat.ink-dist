"""Check the distributable website and real download without extra packages."""
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.assets, self.ids, self.projects = [], [], [], []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('id'): self.ids.append(values['id'])
        if tag == 'a': self.links.append(values)
        if tag in ('script', 'img') and values.get('src'): self.assets.append(values['src'])
        if tag == 'link' and values.get('href'): self.assets.append(values['href'])
        if tag == 'details' and 'system-entry' in values.get('class', '').split(): self.projects.append(values)

html = (DIST / 'index.html').read_text(encoding='utf-8')
page = Page()
page.feed(html)
assert len(page.projects) == 44
assert len(page.ids) == len(set(page.ids)), 'Duplicate IDs'
for asset in page.assets:
    assert not asset.startswith(('http:', 'https:', '//')), asset
    assert (DIST / asset).is_file(), asset
for link in page.links:
    href = link.get('href', '')
    if href.startswith('#'): assert href[1:] in page.ids, href
    elif not href.startswith(('http:', 'https:')): assert (DIST / href).is_file(), href
links = [link for link in page.links if 'download' in link]
assert len(links) == 3 and all(link['href'] == 'downloads/deskset-systems.zip' for link in links)
metadata = json.loads((DIST / 'collection.json').read_text(encoding='utf-8'))
assert len(metadata['projects']) == 44
archive = DIST / metadata['download']['file']
assert archive.stat().st_size == metadata['download']['bytes']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == metadata['download']['sha256']
with ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    names = bundle.namelist()
    assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in names)
    assert not any('/.work/' in name or '/tests/' in name or '/.git/' in name for name in names)
    for project in metadata['projects']:
        assert 'Deskset/' + project['folder'] + '/index.php' in names
    assert 'Deskset/SystemMorpher/builder.php' in names
    assert 'System Setup' in bundle.read('Deskset/SystemMorpher/builder.php').decode('utf-8')
    assert b'Copyright (c) 2026 Kailash Nadh' in bundle.read('Deskset/OAT-LICENSE.txt')
    for file in ('deploy_exam.bat', 'deploy_exam.ps1', 'README.md', 'assets/css/oat.min.css'):
        assert 'Deskset/' + file in names
configuration = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
assert configuration['outputDirectory'] == 'dist' and configuration['buildCommand'] == ''
assert configuration['headers'][0]['headers'][0]['value'] == 'attachment; filename="deskset-systems.zip"'
assert not re.search(r'@import|url\([\s\"\x27]*https?://', (DIST / 'assets/site.css').read_text(), re.I)
checked = subprocess.run(['node', '--check', str(DIST / 'assets/site.js')], capture_output=True, text=True)
assert checked.returncode == 0, checked.stdout + checked.stderr
print('PASS: 44 catalog entries; complete ZIP, checksum and licenses; working local links; standalone assets; JavaScript syntax; Vercel configuration.')
