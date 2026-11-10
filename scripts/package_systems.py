"""Package the original Oat site and the complete offline PHP collection."""
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'.php', '.sql', '.css', '.js', '.json', '.md', '.txt', '.tpl'}
ARCHIVE_ROOT = 'oat.ink-dist/'
DOWNLOAD = 'downloads/oat.ink-dist.zip'


def package(source):
    source = source.resolve()
    menu = json.loads((source / 'tests/fixtures/deploy_menu.json').read_text(encoding='utf-8'))
    assert len(menu) == 44 and len({item['folder'] for item in menu}) == 44
    output = ROOT / 'dist'
    assert output.parent == ROOT and output.name == 'dist'
    if output.exists(): shutil.rmtree(output)
    shutil.copytree(ROOT / 'site/upstream', output)
    for folder in ('downloads', 'licenses'):
        (output / folder).mkdir()
    shutil.copy2(ROOT / 'site/download.css', output / 'download.css')
    shutil.copy2(ROOT / 'site/Oat-MIT.txt', output / 'licenses/Oat-MIT.txt')
    link = '<a class="button small systems-download" href="/' + DOWNLOAD + '" download="oat.ink-dist.zip" aria-label="Download all 44 PHP systems (ZIP)">Download</a>'
    for page in output.rglob('*.html'):
        html = page.read_text(encoding='utf-8')
        if page.name == '404.html': continue
        assert html.count('<div class="col-8 justify-end hstack">') == 1, page
        html = html.replace('<div class="col-8 justify-end hstack">', '<div class="col-8 justify-end hstack">' + link, 1)
        mobile = link.replace('systems-download', 'systems-download systems-mobile-download')
        position = html.index('</nav>')
        end = html.rfind('</div>', 0, position)
        html = html[:end] + mobile + html[end:]
        html = html.replace('</head>', '<link href="/download.css" rel="stylesheet"></head>', 1)
        html = html.replace('https://oat.ink/', 'https://oatink-dist.vercel.app/')
        page.write_text(html, encoding='utf-8')
    for name in ('robots.txt', 'sitemap.xml'):
        path = output / name
        path.write_text(path.read_text(encoding='utf-8').replace('https://oat.ink', 'https://oatink-dist.vercel.app'), encoding='utf-8')
    runtime, catalog = [], []
    for item in menu:
        directory = source / item['folder']
        assert directory.is_dir() and directory.parent == source
        files = sorted(file for file in directory.rglob('*') if file.is_file())
        assert files
        for file in files:
            assert file.suffix.lower() in ALLOWED, 'Unexpected runtime file: ' + str(file)
            assert not any(part.startswith('.') for part in file.relative_to(directory).parts)
        runtime.extend(files)
        catalog.append({**item, 'files': len(files)})
    root_files = [source / name for name in ('index.php', 'deploy_exam.bat', 'deploy_exam.ps1')]
    root_files.extend(file for file in (source / 'assets').rglob('*') if file.is_file())
    assert all(file.exists() for file in root_files)
    readme = """# PHP systems

43 PHP/MySQL systems and the SystemMorpher generator, with local assets and SQL files.

1. Extract the complete oat.ink-dist folder.
2. Start Apache and MySQL in XAMPP.
3. Double-click deploy_exam.bat. Choose a system and enter a new folder name.
4. Open the local URL printed by the launcher.

Option 42 opens SystemMorpher. Set the project folder and database name in the browser.
You can also copy one complete system folder into C:/xampp/htdocs and open its local URL.
Set local MySQL credentials in the chosen system's connector if necessary. Use a unique database
name for separate data: renaming the project folder does not rename its database. Empty installations
import sample tables and records automatically. Deleting a master can also delete its linked records.

These PHP systems run locally with PHP and MySQL. Vercel hosts only the download website.
See each project's included guide for its fields, calculations and local-use limitations.
Oat UI is included under its MIT license; see OAT-LICENSE.txt.
"""
    archive = output / DOWNLOAD
    with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=9) as bundle:
        for file in sorted(runtime + root_files):
            bundle.write(file, ARCHIVE_ROOT + file.relative_to(source).as_posix())
        bundle.writestr(ARCHIVE_ROOT + 'README.md', readme)
        bundle.writestr(ARCHIVE_ROOT + 'OAT-LICENSE.txt', (ROOT / 'site/Oat-MIT.txt').read_bytes())
    with ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len({name.split('/')[1] for name in bundle.namelist() if name.endswith('/index.php') and name.count('/') == 2}) == 44
    metadata = {'projects': catalog, 'download': {'file': DOWNLOAD, 'bytes': archive.stat().st_size,
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}}
    (output / 'collection.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(f'Packaged {len(catalog)} projects; {len(runtime)} runtime files; {archive.stat().st_size:,} bytes; original Oat site with Download.')
    return metadata


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'oat.ink-dist')
    package(parser.parse_args().source)
