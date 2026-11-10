"""Refresh the static catalog and complete PHP collection ZIP. Standard library only."""
from argparse import ArgumentParser
from collections import Counter
from html import escape
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    'RENTALS and BOOKINGS': 'Rentals & bookings',
    'CLINICAL and HEALTHCARE SERVICES': 'Healthcare',
    'RETAIL, POS and FOOD': 'Retail & food',
    'SERVICE, REPAIR and FITNESS': 'Services & repair',
    'ACADEMIC, CAMPUS and INSTITUTIONAL': 'Campus & organizations',
    'COMMUNITY, UTILITIES, LOGISTICS and COMMERCIAL': 'Community & utilities',
    'UNIVERSAL GENERATORS and TEMPLATES': 'Builders & templates',
    'PRACTICE TEMPLATES': 'Record templates',
}
NAMES = {'IctCongress': 'ICT Congress', 'UcIntramuralsSystem': 'UC Intramurals',
         'BasicCrudSystem': 'Basic Records', 'CompleteCrudSystem': 'Record Manager',
         'SystemMorpher': 'System Builder', 'UniversalTemplate': 'Universal Template'}
ALLOWED = {'.php', '.sql', '.css', '.js', '.json', '.md', '.txt', '.tpl'}


def label(value):
    return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', value.replace('_', ' ')).strip().title()


def package(source):
    source = source.resolve()
    menu = json.loads((source / 'tests/fixtures/deploy_menu.json').read_text(encoding='utf-8'))
    assert len(menu) == 44 and len({item['folder'] for item in menu}) == 44
    output = ROOT / 'dist'
    for folder in ('assets', 'downloads', 'licenses'):
        (output / folder).mkdir(parents=True, exist_ok=True)
    catalog, runtime = [], []
    for number, item in enumerate(menu, 1):
        directory = source / item['folder']
        assert directory.is_dir() and directory.parent == source
        files = sorted(file for file in directory.rglob('*') if file.is_file())
        assert files
        for file in files:
            assert file.suffix.lower() in ALLOWED, 'Unexpected runtime file: ' + str(file)
            assert not any(part.startswith('.') for part in file.relative_to(directory).parts)
        runtime.extend(files)
        sql = (directory / 'database.sql').read_text(encoding='utf-8') if (directory / 'database.sql').exists() else ''
        tables = re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([A-Za-z_][A-Za-z0-9_]*)', sql, re.I)
        modules = [label(table) for table in dict.fromkeys(tables)]
        if item['folder'] == 'SystemMorpher': modules = ['Tables', 'Fields', 'Links', 'Monitoring']
        assert modules, item['folder']
        category = GROUPS[item['group']]
        catalog.append({'number': number, 'folder': item['folder'],
                        'title': NAMES.get(item['folder'], label(item['folder'].removesuffix('System'))),
                        'category': category, 'category_id': re.sub('[^a-z]+', '-', category.lower()).strip('-'),
                        'modules': modules, 'files': len(files)})
    archive = output / 'downloads/deskset-systems.zip'
    root_files = [source / name for name in ('index.php', 'deploy_exam.bat', 'deploy_exam.ps1')]
    root_files.extend(file for file in (source / 'assets').rglob('*') if file.is_file())
    assert all(file.exists() for file in root_files)
    readme = """# Deskset collection

43 PHP/MySQL systems and the SystemMorpher generator, with local assets and SQL files.

1. Extract the complete Deskset folder.
2. Start Apache and MySQL in XAMPP.
3. Double-click deploy_exam.bat. Choose a system and enter a new folder name.
4. Open the local URL printed by the launcher.

Option 42 opens SystemMorpher. Its project folder and database name are entered in the browser.
You can also copy one complete system folder into C:/xampp/htdocs and open http://localhost/YourFolder/.
Set local MySQL credentials in the chosen system's connector if necessary. Use a unique database name
for separate data: renaming the project folder does not rename the database. Empty installations import
sample tables and records automatically. Deleting a master record can also delete its linked records.

The PHP systems run on your computer with PHP and MySQL. The download website only distributes them.
Check each project's included guide for its particular fields, calculations and local-use limitations.
Oat UI is included under its MIT license; see OAT-LICENSE.txt.
"""
    with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=9) as bundle:
        for file in sorted(runtime + root_files):
            bundle.write(file, 'Deskset/' + file.relative_to(source).as_posix())
        bundle.writestr('Deskset/README.md', readme)
        bundle.writestr('Deskset/OAT-LICENSE.txt', (ROOT / 'site/Oat-MIT.txt').read_bytes())
    assert archive.stat().st_size > 0
    with ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len({name.split('/')[1] for name in bundle.namelist() if name.endswith('/index.php') and name.count('/') == 2}) == 44
        assert not any('/.work/' in name or '/tests/' in name or '..' in Path(name).parts for name in bundle.namelist())
    size = f'{archive.stat().st_size / (1024 * 1024):.2f} MB'
    counts = Counter(item['category'] for item in catalog)
    categories = {item['category']: item['category_id'] for item in catalog}
    buttons, options, systems = [], [], []
    for category, slug in categories.items():
        buttons.append(f'<button type="button" class="category-button" data-category="{slug}" aria-pressed="false">{escape(category)}<span>{counts[category]}</span></button>')
        options.append(f'<option value="{slug}">{escape(category)}</option>')
    for item in catalog:
        text = ' '.join([item['title'], item['folder'], *item['modules']]).lower()
        modules = ' \u00b7 '.join(item['modules'])
        systems.append(f"""<details class="system-entry" data-category="{item['category_id']}" data-search="{escape(text, quote=True)}">
  <summary><span class="project-number">{item['number']:02d}</span><span class="system-heading"><span class="system-title">{escape(item['title'])}</span><span class="system-modules">{escape(modules)}</span></span></summary>
  <div class="system-detail"><p>Folder: <code>{escape(item['folder'])}/</code></p><p>{item['files']} files, including PHP pages and local UI assets. {escape('Tables: ' + ', '.join(item['modules']) + '.' if item['folder'] != 'SystemMorpher' else 'Configurable PHP project generator with 18 starting templates.')}</p><p>Included in the complete collection ZIP.</p></div>
</details>""")
    html = (ROOT / 'site/index.template.html').read_text(encoding='utf-8')
    for marker, content in {'<!-- CATEGORIES -->': '\n'.join(buttons), '<!-- CATEGORY_OPTIONS -->': ''.join(options), '<!-- SYSTEMS -->': '\n'.join(systems), '<!-- ZIP_SIZE -->': size}.items():
        assert marker in html
        html = html.replace(marker, content)
    (output / 'index.html').write_text(html, encoding='utf-8')
    for name in ('site.css', 'site.js', 'favicon.svg'):
        shutil.copy2(ROOT / 'site' / name, output / 'assets' / name)
    for name, folder in (('oat.min.css', 'css'), ('oat.min.js', 'js')):
        shutil.copy2(source / 'assets' / folder / name, output / 'assets' / name)
    preview = source / '.work/design-preview/coffee-customers-desktop.png'
    assert preview.is_file(), 'Supply the Coffee Shop preview image before refreshing the site.'
    shutil.copy2(preview, output / 'assets/coffee-preview.png')
    shutil.copy2(ROOT / 'site/Oat-MIT.txt', output / 'licenses/Oat-MIT.txt')
    metadata = {'projects': catalog, 'download': {'file': 'downloads/deskset-systems.zip', 'bytes': archive.stat().st_size,
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}}
    (output / 'collection.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Packaged {len(catalog)} projects; {len(runtime)} runtime files; {size} ZIP.')
    return metadata


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'oat.ink-dist')
    package(parser.parse_args().source)
