/* Personal SQL fleet workflows. Every API request independently checks the current owner. */
import {api} from './api.js';
import {$, element, link, button, status, count, dateLabel, vehicleName, profileURL, emptyState, pagination, recordURL} from './ui.js';

let actor = null, generation = 0, bound = false, busy = false, ready = false, uncertain = false;
let fleetInfo = null, orderInfo = null, selectedModel = null, scopeVehicle = null, selectedMatch = null, confirmation = null;
let refreshGeneration = 0, searchGeneration = 0;
const tickets = {}, pages = {};
const view = () => $('fleet-page')?.dataset.view;
const resourceId = () => location.pathname.split('/').pop();
const fleetPath = () => '/api/fleets/' + resourceId();
const abort = () => Object.assign(new Error('Workspace changed'), {name: 'AbortError'});

function lockControls() {
  const locked = !actor || !ready || busy || uncertain;
  for (const node of document.querySelectorAll('.fleet-mutation input,.fleet-mutation textarea,.fleet-mutation select,.fleet-mutation button,[data-fleet-write]')) node.disabled = locked;
  if ($('fleet-add-submit')) $('fleet-add-submit').disabled = locked || !selectedModel;
  for (const id of ['fleet-refresh', 'fleet-review-records']) if ($(id)) $(id).disabled = busy;
}

export function clearFleets() {
  if (!$('fleet-page')) return;
  generation++; refreshGeneration++; searchGeneration++;
  actor = null; busy = false; ready = false; uncertain = false; fleetInfo = null; orderInfo = null;
  selectedModel = null; scopeVehicle = null; selectedMatch = null; confirmation = null;
  for (const key of Object.keys(tickets)) tickets[key]++;
  for (const key of Object.keys(pages)) pages[key] = 1;
  $('fleet-workspace').hidden = true; $('fleet-refresh').hidden = true; $('fleet-uncertain').hidden = true;
  $('fleet-page-title').textContent = 'My fleets'; $('fleet-page-subtitle').textContent = 'Personal recall tracking';
  for (const id of ['fleet-list', 'fleet-vehicles', 'fleet-matches', 'fleet-orders', 'fleet-search-results', 'order-facts', 'order-links']) $(id)?.replaceChildren();
  for (const id of ['fleet-vehicle-count', 'fleet-order-count', 'fleet-scope-label', 'fleet-order-description', 'fleet-confirm-description', 'fleet-selected-model', 'fleet-list-status', 'fleet-vehicles-status', 'fleet-matches-status', 'fleet-orders-status', 'fleet-search-status']) if ($(id)) $(id).textContent = '';
  for (const form of document.querySelectorAll('#fleet-page form')) form.reset();
  for (const node of document.querySelectorAll('#fleet-workspace .pagination')) { node.replaceChildren(); node.hidden = true; }
  $('fleet-confirm-dialog').close(); $('fleet-order-dialog')?.close();
  $('fleet-gate').hidden = false; $('fleet-gate').replaceChildren(element('p', '', 'Checking your account…')); status('fleet-message'); lockControls();
}

function signIn(message) {
  clearFleets();
  $('fleet-gate').replaceChildren(emptyState('Sign in to manage your fleets', message, 'Sign in', '/login?' + new URLSearchParams({next: location.pathname + location.search})));
}
async function read(path) {
  const active = generation; const result = await api(path);
  if (!actor || active !== generation) throw abort();
  return result;
}
function readFailure(error, id = 'fleet-message') {
  if (error.name === 'AbortError' || !actor) return;
  if (error.status === 401) { signIn('Your sign-in has expired. Sign in again to reopen your fleet records.'); return; }
  ready = false; lockControls(); status(id, error.message, 'error');
}
function unavailable(error) {
  if (error.name === 'AbortError' || !actor) return;
  if (error.status === 401) { signIn('Sign in again to reopen your fleet records.'); return; }
  ready = false; $('fleet-workspace').hidden = true; $('fleet-gate').hidden = false;
  $('fleet-page-title').textContent = error.status === 404 ? 'Record not found' : 'Fleet records unavailable';
  $('fleet-page-subtitle').textContent = 'Only records belonging to your account are available here.';
  $('fleet-gate').replaceChildren(element('p', '', error.message), button('Refresh records', () => refreshWorkspace(true)), link('All my fleets →', '/fleets', 'text-link')); lockControls();
}

async function mutate(path, method, body, after) {
  if (!actor || !ready || busy || uncertain) return;
  const active = generation; busy = true; lockControls(); status('fleet-message', 'Saving your change…');
  let result;
  try { result = await api(path, {method, body}); }
  catch (error) {
    if (active !== generation || !actor) return;
    if (error.status === 401) { signIn('Your sign-in expired. Sign in again to continue.'); return; }
    status('fleet-message', error.message, 'error');
    if (!error.status || error.status < 400 || error.status >= 500) { uncertain = true; $('fleet-uncertain').hidden = false; $('fleet-order-dialog')?.close(); }
    else if (error.status === 409) { $('fleet-order-dialog')?.close(); busy = false; await refreshWorkspace(false, true); }
    return;
  } finally { if (active === generation) { busy = false; lockControls(); } }
  if (active !== generation || !actor) return;
  status('fleet-message', 'Change saved.', 'success');
  await after(result);
}

function confirmRemoval(title, description, action) {
  if (!actor || !ready || busy || uncertain) return;
  confirmation = action; $('fleet-confirm-title').textContent = title; $('fleet-confirm-description').textContent = description; $('fleet-confirm-dialog').showModal();
}

async function paged(prefix, path, query, page, render, emptyMessage, load) {
  const requestId = tickets[prefix] = (tickets[prefix] || 0) + 1;
  pages[prefix] = page; const root = $(prefix); root.replaceChildren(); root.setAttribute('aria-busy', 'true'); $(prefix + '-pagination').hidden = true;
  status(prefix + '-status', 'Loading records…');
  try {
    const result = await read(path + '?' + new URLSearchParams({...query, page, pageSize: 10}));
    if (requestId !== tickets[prefix]) return false;
    for (const item of result.items) root.append(render(item));
    if (!result.items.length) root.append(element('p', 'field-hint', emptyMessage));
    status(prefix + '-status', `${count(result.pagination.total)} ${prefix === 'fleet-list' ? 'fleets' : prefix === 'fleet-vehicles' ? 'fleet vehicles' : prefix === 'fleet-matches' ? 'vehicle–recall matches' : 'work orders'} found.`);
    pagination(prefix + '-pagination', result.pagination, number => reloadSlice(() => load(number)));
    if (!result.items.length && page > 1) root.append(button('Return to first page', () => reloadSlice(() => load(1))));
    return true;
  } catch (error) { if (requestId === tickets[prefix]) readFailure(error, prefix + '-status'); return false; }
  finally { if (requestId === tickets[prefix]) root.setAttribute('aria-busy', 'false'); lockControls(); }
}
async function reloadSlice(load) {
  if (busy || !actor) return;
  const active = generation; ready = false; lockControls();
  const ok = await load(); if (active === generation && actor && ok) ready = true; lockControls();
}

function fleetCard(item) {
  const card = element('article', 'fleet-card'); card.dataset.fleetId = item.fleetId;
  card.append(element('p', 'eyebrow', `FLEET #${item.fleetId}`), link(item.name, `/fleets/${item.fleetId}`, 'case-title-link'),
    element('p', 'fleet-card-counts', `${count(item.vehicleCount)} vehicles · ${count(item.workOrderCount)} work orders`), element('p', 'field-hint', `Created ${dateLabel(item.createdAt)}`));
  return card;
}
function loadFleets(page = 1) { return paged('fleet-list', '/api/fleets', {}, page, fleetCard, 'No fleets on this page. Create a fleet to start tracking your vehicles.', loadFleets); }

function vehicleCard(item) {
  const card = element('article', 'fleet-vehicle-card'); card.dataset.vehicleId = item.fleetVehicleId;
  const head = element('div', 'section-heading'); head.append(element('h3', '', item.label), link('Safety profile →', profileURL(item.vehicle), 'text-link'));
  card.append(head, element('p', 'muted', vehicleName(item.vehicle)));
  const form = element('form', 'fleet-label-form fleet-mutation'); form.method = 'post';
  const label = element('label', '', 'Vehicle label'), input = element('input'); input.id = `fleet-label-${item.fleetVehicleId}`; label.htmlFor = input.id; input.value = item.label; input.maxLength = 100; input.required = true;
  const save = element('button', 'button button-quiet button-small', 'Rename vehicle'); save.type = 'submit'; form.append(label, input, save);
  form.addEventListener('submit', event => { event.preventDefault(); mutate(`/api/fleet-vehicles/${item.fleetVehicleId}`, 'PATCH', {label: input.value}, () => refreshWorkspace()); });
  const actions = element('div', 'saved-card-actions');
  actions.append(link('Show recalls & orders →', `/fleets/${item.fleetId}?vehicle=${item.fleetVehicleId}#fleet-recalls-section`, 'text-link'));
  const remove = button('Remove vehicle', () => confirmRemoval('Remove this fleet vehicle?', `Remove ${item.label} and all of its work orders? Other vehicles and imported safety records remain.`, () => mutate(`/api/fleet-vehicles/${item.fleetVehicleId}`, 'DELETE', undefined, () => scopeVehicle?.fleetVehicleId === item.fleetVehicleId ? location.assign(`/fleets/${item.fleetId}`) : refreshWorkspace())), 'remove-link');
  remove.dataset.fleetWrite = ''; actions.append(remove); card.append(form, actions); return card;
}
function loadVehicles(page = 1) { return paged('fleet-vehicles', fleetPath() + '/vehicles', {}, page, vehicleCard, 'No vehicles on this page. Expand the form below to add one.', loadVehicles); }

function matchCard(item) {
  const card = element('article', 'fleet-card'); card.dataset.vehicleId = item.fleetVehicleId; card.dataset.recallId = item.recallId;
  card.append(element('p', 'eyebrow', item.label), link(`Recall ${item.campaignNumber} →`, recordURL('recalls', item.campaignNumber), 'case-title-link'), element('p', 'muted', vehicleName(item.vehicle)));
  if (item.workOrderId) card.append(element('p', 'field-hint', `Tracking status: ${item.workOrderStatus}`), link(`Open work order #${item.workOrderId} →`, `/work-orders/${item.workOrderId}`, 'text-link'));
  else {
    card.append(element('p', 'field-hint', 'No work order for this vehicle–recall pair.'));
    const create = button('Create work order', () => {
      if (busy || uncertain || !ready) return;
      selectedMatch = item; $('fleet-order-notes').value = ''; $('fleet-order-description').textContent = `${item.label} · ${item.campaignNumber}`; $('fleet-order-dialog').showModal();
    }); create.dataset.fleetWrite = ''; card.append(create);
  }
  return card;
}
function loadMatches(page = 1) {
  const query = {}; if (scopeVehicle) query.fleetVehicleId = scopeVehicle.fleetVehicleId;
  if ($('fleet-tracked-filter').value) query.tracked = $('fleet-tracked-filter').value;
  return paged('fleet-matches', fleetPath() + '/recall-matches', query, page, matchCard, 'No recall matches for these filters in the imported snapshot.', loadMatches);
}
function orderCard(item) {
  const card = element('article', 'fleet-card'); card.dataset.orderId = item.workOrderId;
  card.append(element('span', 'case-badge', item.status), link(`Work order #${item.workOrderId}`, `/work-orders/${item.workOrderId}`, 'case-title-link'),
    element('p', 'muted', `${item.label} · ${item.campaignNumber}`), element('p', 'field-hint', item.notes || 'No notes added.'),
    element('p', 'field-hint', item.completedAt ? `Marked completed ${dateLabel(item.completedAt)}` : `Created ${dateLabel(item.createdAt)}`)); return card;
}
function loadOrders(page = 1) {
  const query = {fleetId: resourceId()}; if (scopeVehicle) query.fleetVehicleId = scopeVehicle.fleetVehicleId;
  if ($('fleet-order-status-filter').value) query.status = $('fleet-order-status-filter').value;
  return paged('fleet-orders', '/api/work-orders', query, page, orderCard, 'No work orders for these filters. Create one from a recall match above.', loadOrders);
}

async function loadFleet() {
  const result = await read(fleetPath()); fleetInfo = result.fleet;
  const filter = new URLSearchParams(location.search), vehicle = filter.get('vehicle'); scopeVehicle = null;
  if (vehicle !== null) {
    if (!/^[1-9][0-9]{0,15}$/.test(vehicle) || filter.getAll('vehicle').length !== 1) throw Object.assign(new Error('Choose a valid fleet vehicle using its Show recalls & orders link.'), {status: 400});
    const selected = (await read('/api/fleet-vehicles/' + vehicle)).fleetVehicle;
    if (selected.fleetId !== fleetInfo.fleetId) throw Object.assign(new Error('Fleet vehicle not found in this fleet'), {status: 404});
    scopeVehicle = selected;
  }
  $('fleet-page-title').textContent = fleetInfo.name; $('fleet-page-subtitle').textContent = 'Your vehicles, model-year recall matches and follow-up records.';
  $('fleet-name').value = fleetInfo.name; $('fleet-vehicle-count').textContent = count(fleetInfo.vehicleCount); $('fleet-order-count').textContent = count(fleetInfo.workOrderCount);
  $('fleet-vehicle-scope').hidden = !scopeVehicle; $('fleet-scope-label').textContent = scopeVehicle ? `${scopeVehicle.label} · ${vehicleName(scopeVehicle.vehicle)}` : '';
  $('fleet-clear-scope').href = '/fleets/' + fleetInfo.fleetId;
}
function fact(label, value) {
  const row = element('div', 'detail-fact'); row.append(element('dt', '', label), element('dd', '', value)); $('order-facts').append(row);
}
async function loadOrder() {
  const result = await read('/api/work-orders/' + resourceId()); orderInfo = result.workOrder;
  $('fleet-page-title').textContent = `Work order #${orderInfo.workOrderId}`; $('fleet-page-subtitle').textContent = `${orderInfo.label} · ${vehicleName(orderInfo.vehicle)}`;
  $('order-status').value = orderInfo.status; $('order-notes').value = orderInfo.notes; $('order-interpretation').textContent = result.interpretation;
  $('order-facts').replaceChildren(); fact('Recall campaign', orderInfo.campaignNumber); fact('Vehicle label', orderInfo.label); fact('Vehicle identity', vehicleName(orderInfo.vehicle)); fact('Created', dateLabel(orderInfo.createdAt)); fact('Marked completed', orderInfo.completedAt ? dateLabel(orderInfo.completedAt) : 'No current completion timestamp');
  $('order-links').replaceChildren(link('Open fleet →', `/fleets/${orderInfo.fleetId}`, 'text-link'), link('Show this vehicle’s matches →', `/fleets/${orderInfo.fleetId}?vehicle=${orderInfo.fleetVehicleId}`, 'text-link'), link('Official recall details →', recordURL('recalls', orderInfo.campaignNumber), 'text-link'), link('Vehicle safety profile →', profileURL(orderInfo.vehicle), 'text-link'));
}

async function refreshWorkspace(review = false, resetPages = false) {
  if (!actor || busy) return false;
  const active = generation, requestId = ++refreshGeneration;
  ready = false; lockControls(); let ok = true;
  if (review && uncertain && view() === 'detail') { $('fleet-tracked-filter').value = ''; $('fleet-order-status-filter').value = ''; }
  try {
    if (view() === 'list') { $('fleet-page-title').textContent = 'My fleets'; $('fleet-page-subtitle').textContent = 'Keep your vehicles and recall follow-up together.'; ok = await loadFleets(review || resetPages ? 1 : pages['fleet-list'] || 1); }
    else if (view() === 'detail') {
      await loadFleet();
      const results = await Promise.all([loadVehicles(review || resetPages ? 1 : pages['fleet-vehicles'] || 1), loadMatches(review || resetPages ? 1 : pages['fleet-matches'] || 1), loadOrders(review || resetPages ? 1 : pages['fleet-orders'] || 1)]);
      ok = results.every(Boolean);
    } else await loadOrder();
    if (active !== generation || requestId !== refreshGeneration || !actor) return false;
    if (ok) {
      $('fleet-workspace').hidden = false; $('fleet-gate').hidden = true; ready = true;
      if (review && uncertain) { uncertain = false; $('fleet-uncertain').hidden = true; status('fleet-message', 'Records refreshed. Review the current values before making another change.'); }
    }
    return ok;
  } catch (error) { if (active === generation && requestId === refreshGeneration) unavailable(error); return false; }
  finally { if (active === generation && requestId === refreshGeneration) lockControls(); }
}

async function searchModels(page = 1) {
  if (!actor || busy || uncertain) return;
  const requestId = ++searchGeneration, root = $('fleet-search-results'); root.replaceChildren(); $('fleet-search-pagination').hidden = true;
  selectedModel = null; $('fleet-selected-model').textContent = 'Choose a catalogue vehicle below.'; lockControls(); status('fleet-search-status', 'Finding vehicle identities…');
  const query = new URLSearchParams({page, pageSize: 10});
  for (const field of ['make', 'model', 'year']) if ($('fleet-search-' + field).value.trim()) query.set(field, $('fleet-search-' + field).value.trim());
  try {
    const result = await read('/api/vehicles/search?' + query); if (requestId !== searchGeneration) return;
    for (const item of result.items) {
      const row = element('div', 'case-vehicle-option'); row.append(element('p', '', vehicleName(item)));
      const choose = button('Select vehicle', () => {
        if (!actor || busy || uncertain || !ready) return;
        selectedModel = item; $('fleet-selected-model').textContent = vehicleName(item);
        for (const other of root.querySelectorAll('button')) { other.textContent = 'Select vehicle'; other.setAttribute('aria-pressed', 'false'); }
        choose.textContent = 'Selected'; choose.setAttribute('aria-pressed', 'true'); lockControls();
      }); choose.dataset.fleetWrite = ''; choose.setAttribute('aria-pressed', 'false'); row.append(choose); root.append(row);
    }
    status('fleet-search-status', `${count(result.pagination.total)} matching vehicle identities. Select a result before adding it.`); pagination('fleet-search-pagination', result.pagination, searchModels); lockControls();
  } catch (error) { if (requestId === searchGeneration) readFailure(error, 'fleet-search-status'); }
}

function bindEvents() {
  $('fleet-refresh').addEventListener('click', () => refreshWorkspace(true)); $('fleet-review-records').addEventListener('click', () => refreshWorkspace(true));
  $('fleet-create-form')?.addEventListener('submit', event => { event.preventDefault(); mutate('/api/fleets', 'POST', {name: $('fleet-create-name').value}, result => location.assign(`/fleets/${result.fleet.fleetId}`)); });
  $('fleet-rename-form')?.addEventListener('submit', event => { event.preventDefault(); mutate(fleetPath(), 'PATCH', {name: $('fleet-name').value}, () => refreshWorkspace()); });
  $('fleet-delete')?.addEventListener('click', () => { if (!fleetInfo) return; confirmRemoval('Delete this fleet?', `Delete ${fleetInfo.name}, its ${fleetInfo.vehicleCount} vehicles and ${fleetInfo.workOrderCount} work orders? Imported records remain available.`, () => mutate(fleetPath(), 'DELETE', undefined, () => location.assign('/fleets'))); });
  $('fleet-vehicle-search')?.addEventListener('submit', event => { event.preventDefault(); searchModels(); });
  $('fleet-add-form')?.addEventListener('submit', event => {
    event.preventDefault(); if (!selectedModel) return;
    mutate(fleetPath() + '/vehicles', 'POST', {modelYearId: selectedModel.modelYearId, label: $('fleet-vehicle-label').value}, async () => {
      selectedModel = null; $('fleet-add-form').reset(); $('fleet-search-results').replaceChildren(); $('fleet-search-pagination').hidden = true; status('fleet-search-status'); $('fleet-selected-model').textContent = 'Select a catalogue vehicle above.';
      await refreshWorkspace(false, true);
    });
  });
  $('fleet-tracked-filter')?.addEventListener('change', () => reloadSlice(() => loadMatches(1)));
  $('fleet-order-status-filter')?.addEventListener('change', () => reloadSlice(() => loadOrders(1)));
  $('fleet-order-create-form')?.addEventListener('submit', event => {
    event.preventDefault(); if (!selectedMatch) return;
    mutate('/api/work-orders', 'POST', {fleetVehicleId: selectedMatch.fleetVehicleId, recallId: selectedMatch.recallId, notes: $('fleet-order-notes').value}, result => { $('fleet-order-dialog').close(); location.assign(`/work-orders/${result.workOrder.workOrderId}`); });
  });
  $('order-edit-form')?.addEventListener('submit', event => { event.preventDefault(); mutate('/api/work-orders/' + resourceId(), 'PATCH', {status: $('order-status').value, notes: $('order-notes').value}, () => refreshWorkspace()); });
  $('order-delete')?.addEventListener('click', () => { if (!orderInfo) return; const fleet = orderInfo.fleetId; confirmRemoval('Delete this work order?', `Remove work order #${orderInfo.workOrderId}? Its vehicle and official recall remain; the match becomes untracked again.`, () => mutate('/api/work-orders/' + resourceId(), 'DELETE', undefined, () => location.assign(`/fleets/${fleet}`))); });
  $('fleet-confirm-form').addEventListener('submit', event => { event.preventDefault(); const action = confirmation; confirmation = null; $('fleet-confirm-dialog').close(); if (action) action(); });
  document.addEventListener('sessionexpired', () => { if ($('fleet-page')) signIn('Your sign-in has expired. Sign in again to manage your own fleets.'); });
}

export async function initFleets(auth) {
  if (!bound) { bindEvents(); bound = true; }
  clearFleets();
  if (!auth.user) { signIn(auth.error || 'Use your existing application account. Normal users, analysts and admins can each manage their own fleets.'); return; }
  actor = auth.user; $('fleet-workspace').hidden = false; $('fleet-gate').hidden = true; $('fleet-refresh').hidden = false;
  await refreshWorkspace(); lockControls();
}
