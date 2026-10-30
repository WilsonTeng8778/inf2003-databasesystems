/* Shared presentation helpers. Record text is always rendered as text nodes. */
export const $ = id => document.getElementById(id);
export const count = value => new Intl.NumberFormat().format(value);
export function element(tag, className = '', content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}
export function link(label, href, className = '') {
  const node = element('a', className, label); node.href = href; return node;
}
export function button(label, action, className = 'button button-quiet button-small') {
  const node = element('button', className, label); node.type = 'button'; node.addEventListener('click', action); return node;
}
export function status(id, message = '', tone = '') {
  const node = $(id); node.textContent = message; node.className = `status-line ${tone}`;
}
export function dateLabel(value) {
  if (!value) return 'Date not reported';
  const parsed = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(parsed.valueOf()) ? 'Date not reported' : new Intl.DateTimeFormat('en', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}).format(parsed);
}
export function vehicleName(vehicle) { return `${vehicle.year} ${vehicle.make} ${vehicle.model}`; }
export function profileURL(vehicle) {
  return '/vehicles/profile?' + new URLSearchParams({year: vehicle.year, make: vehicle.make, model: vehicle.model});
}
export function emptyState(title, message, actionLabel, actionURL) {
  const box = element('div', 'empty-state panel');
  box.append(element('div', 'empty-symbol', '⌕'), element('h3', '', title), element('p', '', message));
  if (actionURL) box.append(link(actionLabel, actionURL, 'button button-primary'));
  return box;
}
export function pagination(id, data, load) {
  const root = $(id); root.replaceChildren(); root.hidden = data.totalPages <= 1;
  if (root.hidden) return;
  root.append(element('span', '', `Page ${data.page} of ${count(data.totalPages)}`));
  const actions = element('div');
  const previous = button('← Previous', () => load(data.page - 1)); previous.disabled = data.page <= 1;
  const next = button('Next →', () => load(data.page + 1)); next.disabled = data.page >= Math.min(data.totalPages, 10000);
  actions.append(previous, next); root.append(actions);
}
export function addTextSection(root, heading, value) {
  root.append(element('h4', '', heading), element('p', '', value || 'Not reported in this record.'));
}
export function recordURL(type, identifier) { return `/${type}/${encodeURIComponent(identifier)}`; }
