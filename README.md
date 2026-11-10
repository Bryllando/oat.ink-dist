# Oat website with PHP systems download

The original Oat static website, SVGs, demos, and documentation, with a Download button added to each page. Original source: https://github.com/knadh/oat (MIT). The retained upstream revision is in `site/upstream.json`; the license is in `site/Oat-MIT.txt`.

Deploy this repository to Vercel with preset Other, Root Directory `./`, no build command, and Output Directory `dist`. Configuration is included in `vercel.json`. No environment variables or packages are needed.

Download serves `dist/downloads/oat.ink-dist.zip`. Extract it to get `oat.ink-dist/`, containing all 44 PHP projects, SQL, offline assets, launchers, and setup instructions. PHP/MySQL run locally in XAMPP; Vercel serves the static site and ZIP.

To refresh from the PHP source folder:

```powershell
python scripts/package_systems.py --source ../oat.ink-dist
python tests/check_site.py
```

The committed `dist` is ready to deploy. `site/upstream` retains the original website; `site/download.css` styles only the added mobile download link. Existing Oat credits remain in place.

`tests/check_ict_congress.py` verifies quoted names/IDs, CRUD and attendance against an explicitly supplied disposable MySQL instance; its data-directory guard refuses a regular installation. See `preview/systems-checks.json` for the latest collection verification.
