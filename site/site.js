const entries = [...document.querySelectorAll('.system-entry')];
const search = document.getElementById('system-search');
const categorySelect = document.getElementById('category-select');
const categoryButtons = [...document.querySelectorAll('[data-category]')];
const resultCount = document.getElementById('result-count');
const noResults = document.getElementById('no-results');
const menuToggle = document.getElementById('menu-toggle');
const themeToggle = document.getElementById('theme-toggle');
let category = 'all';

function filterSystems() {
  const query = search.value.trim().toLocaleLowerCase();
  let count = 0;
  for (const entry of entries) {
    const matches = (category === 'all' || entry.dataset.category === category) && entry.dataset.search.includes(query);
    entry.hidden = !matches;
    if (matches) count++;
  }
  resultCount.textContent = count === entries.length ? `Showing all ${count} projects` : `Showing ${count} of ${entries.length} projects`;
  noResults.hidden = count !== 0;
  categorySelect.value = category;
  for (const button of categoryButtons) {
    const selected = button.dataset.category === category;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  }
}

function activateNavigation(hash) {
  const links = [...document.querySelectorAll('.primary-nav a')];
  const selected = links.find(link => link.hash === hash);
  if (!selected) return;
  for (const link of links) {
    link.classList.toggle('current', link === selected);
    if (link === selected) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  }
  document.querySelector('.breadcrumb').lastChild.textContent = ' ' + selected.firstChild.textContent.trim();
}

function closeMenu() {
  document.body.classList.remove('menu-open');
  menuToggle.setAttribute('aria-expanded', 'false');
}

function resetFilters() {
  category = 'all';
  search.value = '';
  filterSystems();
}

search.addEventListener('input', filterSystems);
categorySelect.addEventListener('change', () => { category = categorySelect.value; filterSystems(); });
for (const button of categoryButtons) button.addEventListener('click', () => {
  category = button.dataset.category;
  filterSystems();
  activateNavigation('#systems');
  closeMenu();
  document.getElementById('systems').scrollIntoView({ behavior: 'auto' });
});
document.getElementById('search-form').addEventListener('submit', event => event.preventDefault());
document.getElementById('search-form').addEventListener('reset', event => { event.preventDefault(); resetFilters(); });
document.getElementById('reset-empty').addEventListener('click', () => { resetFilters(); search.focus(); });
menuToggle.addEventListener('click', () => {
  const opened = document.body.classList.toggle('menu-open');
  menuToggle.setAttribute('aria-expanded', String(opened));
});
for (const link of document.querySelectorAll('a[href^="#"]')) link.addEventListener('click', () => { closeMenu(); activateNavigation(link.hash); });
activateNavigation('#overview');
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });

function setTheme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  themeToggle.textContent = dark ? 'Light theme' : 'Dark theme';
  themeToggle.setAttribute('aria-pressed', String(dark));
}
let savedTheme = 'light';
try { savedTheme = localStorage.getItem('deskset-theme') || 'light'; } catch {}
setTheme(savedTheme === 'dark');
themeToggle.addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme !== 'dark';
  setTheme(dark);
  try { localStorage.setItem('deskset-theme', dark ? 'dark' : 'light'); } catch {}
});
for (const link of document.querySelectorAll('.download-link')) link.addEventListener('click', () => {
  document.getElementById('download-status').textContent = 'Your ZIP download is starting. Extract it, then follow the included setup guide.';
});
