import {api} from './api.js';
import {$, count, element, link, button, status, dateLabel, vehicleName, profileURL, emptyState, pagination, addTextSection, recordURL} from './ui.js';
import {initComplaints, initRecord} from './research.js';
import {initCases, clearCases} from './cases.js';
import {initFleets, clearFleets} from './fleets.js';
import {initAdministration, clearAdministration} from './admin.js';
import {initAnalytics} from './analytics.js';

const page = document.body.dataset.page;
const auth = {user: null, error: null};
let profileVehicle = null;
export function safeNext(value) {
  try {
    const target = new URL(value || '/saved-vehicles', location.origin);
    const knownPage = ['/vehicles', '/vehicles/profile', '/saved-vehicles', '/complaints', '/', '/cases', '/cases/new', '/fleets', '/admin', '/admin/users', '/admin/imports', '/analytics'].includes(target.pathname)
      || /^\/(?:complaints\/[0-9]{1,20}|(?:recalls|investigations)\/[A-Za-z0-9]{1,20}|(?:cases|fleets|work-orders)\/[0-9]{1,16})$/.test(target.pathname);
    if (target.origin === location.origin && knownPage) {
      return target.pathname + target.search;
    }
  } catch { /* Fall back to a local application page. */ }
  return '/saved-vehicles';
}
function signInURL(next = location.pathname + location.search) { return '/login?' + new URLSearchParams({next: safeNext(next)}); }
function renderAccount() {
  const root = $('account-nav'); root.replaceChildren();
  if (auth.user) {
    const email = element('span', 'account-email', auth.user.email); email.title = auth.user.email;
    const logout = button('Sign out', async () => {
      logout.disabled = true;
      try { await api('/api/auth/logout', {method: 'POST', body: {}}); auth.user = null; clearCases(); clearFleets(); clearAdministration(); location.assign('/vehicles'); }
      catch (error) { logout.disabled = false; globalMessage(error.message); }
    }, 'button button-quiet');
    logout.id = 'log-out'; root.append(email, logout);
  } else {
    root.append(link('Sign in', signInURL(), 'button button-quiet'));
  }
  for (const node of document.querySelectorAll('[data-signin-link]')) node.href = signInURL();
  for (const node of document.querySelectorAll('[data-case-nav]')) node.hidden = !['ANALYST', 'ADMIN'].includes(auth.user?.role);
  for (const node of document.querySelectorAll('[data-admin-nav]')) node.hidden = auth.user?.role !== 'ADMIN';
}
function globalMessage(message) {
  $('global-message').hidden = !message; $('global-message').textContent = message; $('global-message').className = 'notice notice-error';
}
async function refreshAccount() {
  try { auth.user = (await api('/api/auth/me')).user; auth.error = null; }
  catch (error) { auth.user = null; auth.error = error.status === 401 ? null : error.message; }
  renderAccount(); updateSaveButton();
}
function updateSaveButton() {
  if (page !== 'profile' || !profileVehicle) return;
  const save = $('save-vehicle');
  if (save.dataset.saved === 'true' && auth.user) { save.textContent = '✓ Saved to my vehicles'; save.disabled = true; return; }
  save.disabled = false; save.textContent = auth.user ? 'Save vehicle' : 'Sign in to save';
}
document.addEventListener('sessionexpired', () => {
  auth.user = null; auth.error = null; renderAccount();
  if (page === 'saved') savedSignIn();
  if (page === 'profile') { $('save-vehicle').dataset.saved = ''; $('saved-shortcut').hidden = true; updateSaveButton(); }
});
for (const node of document.querySelectorAll('[data-close-dialog]')) {
  node.addEventListener('click', () => $(node.dataset.closeDialog).close());
}
const authReady = refreshAccount();

function initSearch() {
  const form = $('search-form'), root = $('search-results');
  let controller;
  const initial = root.cloneNode(true);
  const params = new URLSearchParams(location.search);
  for (const key of ['make', 'model', 'year']) if (params.has(key)) $(key).value = params.get(key);
  async function search(pageNumber = 1) {
    controller?.abort(); controller = new AbortController();
    const active = controller;
    const query = new URLSearchParams({page: pageNumber, pageSize: 20});
    for (const key of ['make', 'model', 'year']) if ($(key).value.trim()) query.set(key, $(key).value.trim());
    const address = new URLSearchParams(query); address.delete('pageSize');
    history.replaceState(null, '', '/vehicles?' + address);
    status('search-status', 'Searching the vehicle catalogue…');
    $('search-submit').disabled = true; $('search-results-section').setAttribute('aria-busy', 'true');
    $('search-pagination').hidden = true; root.replaceChildren();
    try {
      const result = await api('/api/vehicles/search?' + query, {signal: active.signal});
      if (controller !== active) return;
      $('results-heading').textContent = 'Matching vehicles'; $('result-count').textContent = `${count(result.pagination.total)} found`;
      if (!result.items.length) root.append(emptyState('No matching vehicles', 'Try an exact make or model name, or leave a field blank to broaden your search.'));
      for (const item of result.items) {
        const card = element('article', 'vehicle-card');
        card.append(element('span', 'year-label', String(item.year)), element('h3', '', item.make), element('p', 'model-label', item.model));
        const open = link('View safety profile', profileURL(item)); open.append(element('span', '', '→')); card.append(open); root.append(card);
      }
      const first = result.pagination.total ? (pageNumber-1)*20 + 1 : 0;
      status('search-status', `Showing ${count(first)}–${count(Math.min(pageNumber*20, result.pagination.total))} of ${count(result.pagination.total)} vehicles.`);
      pagination('search-pagination', result.pagination, search);
    } catch (error) {
      if (error.name !== 'AbortError' && controller === active) {
        status('search-status', error.message, 'error');
        root.append(emptyState('Search is temporarily unavailable', 'Please try searching again.'));
      }
    } finally {
      if (controller === active) { $('search-submit').disabled = false; $('search-results-section').setAttribute('aria-busy', 'false'); }
    }
  }
  form.addEventListener('submit', event => { event.preventDefault(); search(); });
  $('example-search').addEventListener('click', () => { $('make').value = 'HONDA'; $('model').value = 'CIVIC'; $('year').value = 2022; search(); });
  $('reset-search').addEventListener('click', () => {
    controller?.abort(); controller = null; form.reset(); root.replaceChildren(...Array.from(initial.cloneNode(true).childNodes));
    $('search-submit').disabled = false; $('search-results-section').setAttribute('aria-busy', 'false');
    $('search-pagination').hidden = true; $('results-heading').textContent = 'Find your starting point';
    $('result-count').textContent = 'Search to explore'; status('search-status'); history.replaceState(null, '', '/vehicles');
  });
  if (['make', 'model', 'year'].some(key => params.has(key)) || params.has('page')) {
    const requested = Number(params.get('page') || 1);
    search(Number.isInteger(requested) && requested > 0 && requested <= 10000 ? requested : 1);
  }
}

function initAuth() {
  const registering = page === 'register', form = $('auth-form');
  const destination = safeNext(new URLSearchParams(location.search).get('next'));
  $('auth-alternate-link').href = (registering ? '/login?' : '/register?') + new URLSearchParams({next: destination});
  $('show-password').addEventListener('change', () => {
    for (const input of [$('password'), $('confirm-password')].filter(Boolean)) input.type = $('show-password').checked ? 'text' : 'password';
  });
  for (const input of [$('password'), $('confirm-password')].filter(Boolean)) input.addEventListener('input', () => $('confirm-password')?.setCustomValidity(''));
  form.addEventListener('submit', async event => {
    event.preventDefault(); status('auth-status');
    if (registering && $('password').value !== $('confirm-password').value) {
      $('confirm-password').setCustomValidity('The passwords do not match.'); $('confirm-password').reportValidity(); return;
    }
    const submit = $('auth-submit'); submit.disabled = true;
    try {
      await api(registering ? '/api/auth/register' : '/api/auth/login', {method: 'POST',
        body: {email: $('email').value.trim(), password: $('password').value}});
      form.reset(); location.assign(destination);
    } catch (error) { status('auth-status', error.message, 'error'); submit.disabled = false; }
  });
}

function renderRecord(item, type) {
  const card = element('article', 'record-item'), meta = element('div', 'record-meta');
  const identifier = type === 'recalls' ? item.campaignNumber : type === 'complaints' ? item.odiNumber : item.investigationNumber;
  meta.append(element('span', '', type === 'complaints' ? `ODI ${identifier}` : identifier),
    element('span', '', dateLabel(type === 'recalls' ? item.reportDate : type === 'complaints' ? item.receivedDate : item.openedDate)));
  if (type === 'investigations') meta.append(element('span', '', `${item.status} · Snapshot status`));
  card.append(meta);
  if (type === 'investigations' && item.subject) card.append(element('h3', '', item.subject));
  if (type === 'complaints') card.append(element('h3', '', item.components.join(' · ') || 'Consumer report'));
  card.append(element('p', 'record-preview', item.summaryPreview ?? item.narrativePreview ?? 'No summary was supplied.'));
  const details = element('details'), summary = element('summary', '', 'Read full record'), full = element('div', 'record-full');
  details.append(summary, full); card.append(details, link(type === 'complaints' ? 'Open complaint page →' : 'Related vehicles & record details →', recordURL(type, identifier), 'record-page-link'));
  details.addEventListener('toggle', async () => {
    if (!details.open || details.dataset.loaded || details.dataset.loading) return;
    details.dataset.loading = 'true'; full.replaceChildren(element('p', '', 'Loading the full record…'));
    try {
      const result = await api(`/api/${type}/${encodeURIComponent(identifier)}`);
      full.replaceChildren();
      if (type === 'recalls') {
        const record = result.recall;
        addTextSection(full, 'Summary', record.summary); addTextSection(full, 'Consequence', record.consequence); addTextSection(full, 'Remedy', record.remedy);
        addTextSection(full, 'Reporting manufacturer', record.manufacturer);
        addTextSection(full, 'Potentially affected units', record.potentiallyAffected === null ? null : count(record.potentiallyAffected));
      } else if (type === 'complaints') {
        const record = result.complaint, incident = record.incident;
        addTextSection(full, 'Consumer narrative', record.narrative);
        const flag = value => value === null ? 'Unknown' : value ? 'Yes' : 'No';
        addTextSection(full, 'Reported incident', `Crash: ${flag(incident.crash)} · Fire: ${flag(incident.fire)} · Injuries: ${incident.injuries ?? 'Unknown'} · Fatalities: ${incident.fatalities ?? 'Unknown'}`);
        addTextSection(full, 'Incident date', dateLabel(record.incidentDate));
      } else {
        const record = result.investigation;
        addTextSection(full, 'Official summary', record.summary); addTextSection(full, 'Manufacturers', record.manufacturers.join(', '));
        addTextSection(full, 'Components', record.components.join(', ')); addTextSection(full, 'Closed date', dateLabel(record.closedDate));
      }
      details.dataset.loaded = 'true';
    } catch (error) {
      full.replaceChildren(element('p', '', error.message), element('p', '', 'Close and reopen this record to try again.'));
    } finally { delete details.dataset.loading; }
  });
  return card;
}

async function initProfile() {
  const params = new URLSearchParams(location.search), query = new URLSearchParams();
  for (const key of ['make', 'model', 'year']) if (params.has(key)) query.set(key, params.get(key));
  try {
    const result = await api('/api/vehicles/safety-profile?' + query);
    profileVehicle = result;
    $('explore-complaints').href = '/complaints?' + new URLSearchParams({year: result.year, make: result.make, model: result.model});
    $('start-analysis-case').href = '/cases/new?' + new URLSearchParams({year: result.year, make: result.make, model: result.model});
    $('profile-analytics-link').href = '/analytics?' + new URLSearchParams({year: result.year, make: result.make, model: result.model});
    $('profile-title').textContent = vehicleName(result); $('profile-subtitle').textContent = 'A snapshot of the safety records for this make, model and year.';
    $('recall-count').textContent = count(result.officialRecallCampaigns); $('complaint-count').textContent = count(result.consumerComplaints);
    $('investigation-count').textContent = count(result.officialInvestigations); $('profile-content').hidden = false;
    $('save-dialog-vehicle').textContent = vehicleName(result);
    const components = $('component-list'), maximum = Math.max(...result.topComplaintComponents.map(item => item.count), 1);
    for (const item of result.topComplaintComponents) {
      const row = element('div', 'component-item'), title = element('div', 'component-title');
      title.append(element('span', '', item._id), element('strong', '', count(item.count)));
      const bar = element('div', 'component-bar'), fill = element('span', 'component-fill');
      fill.style.width = `${item.count / maximum * 100}%`; bar.append(fill); row.append(title, bar); components.append(row);
    }
    if (!result.topComplaintComponents.length) components.append(element('p', 'status-line', 'No complaint components are available for this vehicle.'));
    updateSaveButton();
  } catch (error) {
    $('profile-title').textContent = 'Vehicle profile unavailable'; $('profile-subtitle').textContent = 'Choose a vehicle from search or try again later.';
    status('profile-status', error.message, 'error'); return;
  }
  let type = 'recalls', controller;
  async function loadRecords(pageNumber = 1) {
    controller?.abort(); controller = new AbortController(); const active = controller, activeType = type;
    $('record-list').replaceChildren(); $('record-list').setAttribute('aria-busy', 'true'); $('record-pagination').hidden = true;
    status('record-status', 'Loading records…');
    try {
      const result = await api(`/api/${activeType}?` + new URLSearchParams({modelYearId: profileVehicle.modelYearId, page: pageNumber, pageSize: 5}), {signal: active.signal});
      if (controller !== active) return;
      const root = $('record-list');
      if (!result.items.length) root.append(emptyState('No records in this category', 'The imported snapshot has no matching records for this vehicle.'));
      for (const item of result.items) root.append(renderRecord(item, activeType));
      status('record-status', `${count(result.pagination.total)} ${activeType === 'investigations' ? 'official investigations' : activeType} in the imported snapshot.`);
      pagination('record-pagination', result.pagination, loadRecords);
    } catch (error) { if (error.name !== 'AbortError' && controller === active) status('record-status', error.message, 'error'); }
    finally { if (controller === active) $('record-list').setAttribute('aria-busy', 'false'); }
  }
  for (const node of document.querySelectorAll('[data-record-type]')) node.addEventListener('click', () => {
    type = node.dataset.recordType;
    for (const sibling of document.querySelectorAll('[data-record-type]')) sibling.setAttribute('aria-pressed', String(sibling === node));
    loadRecords();
  });
  loadRecords();
  $('save-vehicle').addEventListener('click', async () => {
    await authReady;
    if (!auth.user) { location.assign(signInURL()); return; }
    status('save-status'); $('save-nickname').value = ''; $('save-dialog').showModal();
  });
  $('save-form').addEventListener('submit', async event => {
    event.preventDefault(); $('confirm-save').disabled = true; status('save-status', 'Saving…');
    try {
      await api('/api/saved-vehicles', {method: 'POST', body: {modelYearId: profileVehicle.modelYearId, nickname: $('save-nickname').value}});
      savedSuccessfully('Vehicle added to your personal list.');
    } catch (error) {
      if (error.status === 409) savedSuccessfully('This vehicle is already in your personal list.');
      else if (error.status === 401) { $('save-dialog').close(); status('profile-status', 'Your sign-in expired. Sign in again to save this vehicle.', 'error'); }
      else status('save-status', error.message, 'error');
    } finally { $('confirm-save').disabled = false; }
  });
  function savedSuccessfully(message) {
    $('save-dialog').close(); $('save-vehicle').dataset.saved = 'true'; $('saved-shortcut').hidden = false;
    status('profile-status', message, 'success'); updateSaveButton();
  }
}

let savedPage = 1, pendingRemoval = null;
function savedSignIn() {
  $('saved-content').replaceChildren(emptyState('Your vehicle list starts here', 'Sign in to see your saved vehicles, or create an account to start your list.', 'Sign in', signInURL('/saved-vehicles')));
  $('saved-content').setAttribute('aria-busy', 'false'); $('saved-pagination').hidden = true;
  status('saved-status');
}
async function loadSaved(pageNumber = 1) {
  savedPage = pageNumber;
  if (!auth.user) {
    if (auth.error) {
      const box = emptyState('Your account is temporarily unavailable', auth.error);
      box.append(button('Try again', async () => { await refreshAccount(); loadSaved(); }));
      $('saved-content').replaceChildren(box); $('saved-content').setAttribute('aria-busy', 'false');
    } else savedSignIn();
    return;
  }
  $('saved-content').setAttribute('aria-busy', 'true'); $('saved-pagination').hidden = true;
  status('saved-status', 'Loading your saved vehicles…');
  try {
    const result = await api('/api/saved-vehicles?' + new URLSearchParams({page: pageNumber, pageSize: 20}));
    if (!result.items.length && pageNumber > 1) { loadSaved(pageNumber - 1); return; }
    const grid = element('div', 'saved-grid');
    for (const item of result.items) grid.append(savedCard(item));
    $('saved-content').replaceChildren(result.items.length ? grid : emptyState('A place for the vehicles you care about', 'Find a vehicle and save it to keep your research close.', 'Find a vehicle', '/vehicles'));
    status('saved-status', `${count(result.pagination.total)} saved ${result.pagination.total === 1 ? 'vehicle' : 'vehicles'}.`);
    pagination('saved-pagination', result.pagination, loadSaved);
  } catch (error) {
    if (error.status !== 401) { $('saved-content').replaceChildren(emptyState('Your list could not be loaded', 'Try refreshing the page.')); status('saved-status', error.message, 'error'); }
  } finally { $('saved-content').setAttribute('aria-busy', 'false'); }
}
function savedCard(item) {
  const card = element('article', 'saved-card panel'); card.dataset.savedVehicleId = item.savedVehicleId;
  const head = element('div', 'saved-card-head'), info = element('div');
  const title = element('h2', '', item.nickname || `${item.vehicle.make} ${item.vehicle.model}`);
  info.append(element('span', 'subtle-chip', String(item.vehicle.year)), title, element('p', 'vehicle-name', vehicleName(item.vehicle)), element('p', 'saved-date', `Saved ${dateLabel(item.savedAt)}`));
  head.append(info); card.append(head);
  const form = element('form', 'nickname-form'), label = element('label', '', 'Nickname'), input = element('input');
  input.id = `nickname-${item.savedVehicleId}`; label.htmlFor = input.id; input.name = 'nickname'; input.maxLength = 100;
  input.value = item.nickname; input.placeholder = 'Add a nickname'; input.setAttribute('aria-label', `Nickname for ${vehicleName(item.vehicle)}`);
  const controls = element('div', 'nickname-controls'), submit = element('button', 'button button-quiet button-small', 'Save nickname');
  submit.type = 'submit'; controls.append(input, submit);
  const message = element('p', 'status-line'); message.setAttribute('role', 'status');
  form.append(label, controls, message); card.append(form);
  form.addEventListener('submit', async event => {
    event.preventDefault(); submit.disabled = true; message.textContent = 'Saving…'; message.className = 'status-line';
    try {
      const result = await api(`/api/saved-vehicles/${item.savedVehicleId}`, {method: 'PATCH', body: {nickname: input.value}});
      item.nickname = result.savedVehicle.nickname; input.value = item.nickname;
      title.textContent = item.nickname || `${item.vehicle.make} ${item.vehicle.model}`; message.textContent = 'Nickname updated.'; message.className = 'status-line success';
    } catch (error) { message.textContent = error.message; message.className = 'status-line error'; }
    finally { submit.disabled = false; }
  });
  const actions = element('div', 'saved-card-actions');
  actions.append(link('Open safety profile →', profileURL(item.vehicle), 'text-link'), button('Remove', () => {
    pendingRemoval = item.savedVehicleId; $('remove-description').textContent = `Remove ${item.nickname || vehicleName(item.vehicle)} from your personal list?`;
    status('remove-status'); $('remove-dialog').showModal();
  }, 'remove-link'));
  card.append(actions); return card;
}
async function initSaved() {
  await authReady; loadSaved();
  $('remove-form').addEventListener('submit', async event => {
    event.preventDefault(); if (!pendingRemoval) return;
    $('confirm-remove').disabled = true; status('remove-status', 'Removing…');
    try {
      await api(`/api/saved-vehicles/${pendingRemoval}`, {method: 'DELETE'});
      pendingRemoval = null; $('remove-dialog').close(); await loadSaved(savedPage);
    } catch (error) {
      if (error.status === 401) { $('remove-dialog').close(); savedSignIn(); }
      else status('remove-status', error.message, 'error');
    } finally { $('confirm-remove').disabled = false; }
  });
}

window.addEventListener('pageshow', async event => {
  if (!event.persisted) return;
  if (page === 'saved') { $('saved-content').replaceChildren(); $('saved-pagination').hidden = true; }
  if (page === 'cases') clearCases();
  if (page === 'fleets') clearFleets();
  if (page === 'admin') clearAdministration();
  await refreshAccount(); if (page === 'saved') loadSaved();
  if (page === 'cases') await initCases(auth);
  if (page === 'fleets') await initFleets(auth);
  if (page === 'admin') await initAdministration(auth, refreshAccount);
});
async function start() {
  if (page === 'search') initSearch();
  if (page === 'login' || page === 'register') initAuth();
  if (page === 'profile') await initProfile();
  if (page === 'saved') await initSaved();
  if (page === 'complaints') initComplaints();
  if (page === 'record') await initRecord();
  if (page === 'analytics') initAnalytics();
  if (page === 'cases') { await authReady; await initCases(auth); }
  if (page === 'fleets') { await authReady; await initFleets(auth); }
  if (page === 'admin') { await authReady; await initAdministration(auth, refreshAccount); }
  await authReady; document.body.dataset.ready = 'true';
}
start().catch(() => globalMessage('This page could not finish loading. Please refresh and try again.'));
