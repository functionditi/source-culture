import { e } from '../ui.js';

export function browseHeader(title, action = null) {
  return `<header class="browse-heading"><h1>${e(title)}</h1>${action ? `<a href="${e(action.href)}">${e(action.label)}</a>` : ''}</header>`;
}

export function filterSelect(id, name, label, value, options) {
  return `<div class="browse-filter"><label for="${e(id)}">${e(label)}</label><select id="${e(id)}" name="${e(name)}">${options.map(([key, text]) => `<option value="${e(key)}" ${key === value ? 'selected' : ''}>${e(text)}</option>`).join('')}</select></div>`;
}

export function browseSearch({ id, inputId, query, placeholder, filters = '', controls = '', active = false, hidden = '' }) {
  return `<form class="browse-search" id="${e(id)}" role="search">
    <div class="browse-search-row"><input id="${e(inputId)}" name="q" type="search" value="${e(query)}" placeholder="${e(placeholder)}" aria-label="${e(placeholder)}"><button type="submit" class="plain-button">Search</button></div>
    ${controls}
    ${filters ? `<details class="browse-filters" ${active ? 'open' : ''}><summary>Filters</summary><div class="browse-filter-fields">${filters}</div></details>` : ''}
    ${hidden}
  </form>`;
}

export function bindBrowseSearch(root, id, path, navigate) {
  const form = root.querySelector('#' + id);
  let focusId = null;
  form.addEventListener('submit', event => {
    event.preventDefault();
    const params = new URLSearchParams(new FormData(form));
    for (const [key, value] of [...params]) if (!value.trim()) params.delete(key);
    navigate(path + (params.size ? '?' + params : ''), { scroll: false, focus: focusId ? '#' + CSS.escape(focusId) : null });
  });
  form.addEventListener('change', event => {
    if (event.target.tagName === 'SELECT' || event.target.type === 'radio') {
      focusId = event.target.id || null;
      form.requestSubmit();
    }
  });
}
