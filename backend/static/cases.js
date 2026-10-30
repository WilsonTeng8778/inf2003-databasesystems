/* Internal workspace. Authority and ownership remain in the case APIs. */
import {api} from './api.js';
import {$, element, link, button, status, count, dateLabel, vehicleName, profileURL, emptyState, pagination, recordURL} from './ui.js';

let actor = null, generation = 0, bound = false, busy = false, command = null, pending = false, loadingDetail = false;
let selectedVehicle = null, caseData = null, confirmation = null, listPage = 1, operationPage = 1, complaintPage = 1;
let vehicleSearchGeneration = 0, complaintSearchGeneration = 0;
let detailAvailable = false, detailGeneration = 0, listGeneration = 0, operationGeneration = 0, historyGeneration = 0;
const caseView = () => $('case-page')?.dataset.view;
const caseId = () => Number(location.pathname.split('/').pop());
const casePath = () => `/api/analysis-cases/${caseId()}`;
const authorized = user => ['ANALYST', 'ADMIN'].includes(user?.role);
const aborted = () => Object.assign(new Error('Workspace access changed'), {name: 'AbortError'});

function lockControls() {
  const locked = !actor || busy || !!command || pending || loadingDetail || (caseView() === 'detail' && !detailAvailable);
  for (const node of document.querySelectorAll('.case-mutation input,.case-mutation textarea,.case-mutation select,.case-mutation button,[data-case-write]')) {
    node.disabled = locked || node.dataset.alreadyLinked === 'true';
  }
  if ($('case-create-submit')) $('case-create-submit').disabled = locked || !selectedVehicle;
  if ($('case-command-retry')) $('case-command-retry').disabled = busy;
  for (const node of document.querySelectorAll('[data-operation-retry]')) node.disabled = busy || !!command || !actor;
}

export function clearCases() {
  if (!$('case-page')) return;
  generation++; actor = null; command = null; busy = false; pending = false; loadingDetail = false;
  selectedVehicle = null; caseData = null; confirmation = null;
  detailAvailable = false; detailGeneration++; listGeneration++; operationGeneration++; historyGeneration++;
  vehicleSearchGeneration++; complaintSearchGeneration++;
  $('case-workspace').hidden = true; $('case-new-link').hidden = true; $('case-command-recovery').hidden = true;
  $('case-command-description').textContent = ''; $('case-command-reference').textContent = '';
  $('case-page-title').textContent = 'Analyst workspace'; $('case-page-subtitle').textContent = 'Internal research cases';
  for (const id of ['case-list', 'case-operations', 'case-vehicle-results', 'case-linked-complaints', 'case-complaint-results', 'case-notes-list', 'case-findings-list', 'case-history', 'case-pending-operation']) $(id)?.replaceChildren();
  for (const form of document.querySelectorAll('#case-workspace form')) form.reset();
  for (const node of document.querySelectorAll('#case-workspace .pagination')) { node.replaceChildren(); node.hidden = true; }
  for (const id of ['case-metadata', 'case-closed-at', 'case-sync-label', 'case-linked-count', 'case-notes-count', 'case-findings-count', 'case-list-status', 'case-operations-status', 'case-history-status', 'case-complaint-status', 'case-vehicle-status', 'case-confirm-description']) if ($(id)) $(id).textContent = '';
  $('case-confirm-dialog')?.close();
  $('case-gate').replaceChildren(element('p', '', 'Checking your workspace access…')); $('case-gate').hidden = false;
  status('case-message'); lockControls();
}

function deny(message, signIn = false) {
  clearCases();
  for (const node of document.querySelectorAll('[data-case-nav]')) node.hidden = true;
  $('case-gate').replaceChildren(emptyState(signIn ? 'Sign in to open the workspace' : 'Analyst access required', message,
    signIn ? 'Sign in' : 'Return to vehicle search', signIn ? '/login?' + new URLSearchParams({next: location.pathname + location.search}) : '/vehicles'));
}

async function read(path) {
  const active = generation;
  const result = await api(path);
  if (active !== generation || !actor) throw aborted();
  return result;
}
function readFailure(error, id) {
  if (error.name === 'AbortError' || !actor) return;
  if ([401, 403].includes(error.status)) { deny('Your session or role no longer allows analyst access. Sign in again or ask the project administrator.', error.status === 401); return; }
  status(id, error.message, 'error');
}

function showUnconfirmed(error) {
  $('case-command-recovery').hidden = false;
  $('case-command-description').textContent = `${command.description}: ${error.message}`;
  $('case-command-reference').textContent = command.key;
  status('case-message', 'We could not confirm this change. Retry the same change below before making another edit.', 'error');
}

async function executeCommand() {
  if (!command || busy || !actor) return;
  const active = generation, original = command;
  busy = true; lockControls(); status('case-message', 'Saving the case change…');
  let result;
  try {
    result = await api(original.path, {method: original.method, body: original.body, idempotencyKey: original.key});
    if (!result?.operation || !['APPLIED', 'PENDING'].includes(result.operation.state)) throw new Error('The service did not confirm a saved update receipt.');
  } catch (error) {
    if (active !== generation || !actor) return;
    if ([401, 403].includes(error.status)) { deny('Your session or role no longer allows analyst access. Sign in again or ask the project administrator.', error.status === 401); return; }
    if (!error.status || error.status < 400 || error.status >= 500) showUnconfirmed(error);
    else {
      command = null; $('case-command-recovery').hidden = true; status('case-message', error.message, 'error');
      if (error.status === 409 && caseView() === 'detail') await loadDetail();
    }
    return;
  } finally { if (active === generation) { busy = false; lockControls(); } }
  if (active !== generation || !actor) return;
  command = null; $('case-command-recovery').hidden = true; $('case-command-reference').textContent = '';
  status('case-message', result.operation.state === 'PENDING' ? 'The update instruction is saved and awaiting completion. Retry the saved update to finish it.' : 'Case change saved.', result.operation.state === 'PENDING' ? '' : 'success');
  lockControls();
  await original.after(result.operation);
}

function change(path, method, body, description, after = refreshDetail) {
  if (!actor || busy || command || pending || loadingDetail) return;
  command = {path, method, body: body === undefined ? undefined : structuredClone(body), description, key: crypto.randomUUID(), after};
  executeCommand();
}

async function retryOperation(operationId, refresh) {
  if (!actor || busy || command) return;
  const active = generation; busy = true; lockControls(); status('case-message', 'Retrying the saved update…');
  try {
    const result = await api(`/api/analysis-cases/operations/${encodeURIComponent(operationId)}/retry`, {method: 'POST', body: {}});
    if (active !== generation || !actor) return;
    status('case-message', result.operation.state === 'APPLIED' ? 'Saved update completed.' : 'The update is still awaiting completion. You can retry this saved update again.', result.operation.state === 'APPLIED' ? 'success' : '');
    await refresh();
  } catch (error) { if (active === generation) readFailure(error, 'case-message'); }
  finally { if (active === generation) { busy = false; lockControls(); } }
}

function operationCard(item, refresh) {
  const row = element('article', 'operation-card'); row.dataset.operationId = item.operationId;
  const heading = element('div', 'operation-card-heading');
  heading.append(item.action === 'DELETE' ? element('strong', '', `Deleted case #${item.caseId}`) : link(`Case #${item.caseId}`, `/cases/${item.caseId}`, 'text-link'),
    element('span', 'case-badge', item.state === 'APPLIED' ? 'Completed' : 'Awaiting completion'));
  row.append(heading, element('p', 'field-hint', `${item.action === 'DELETE' ? 'Remove case content' : 'Save case content'} · Revision ${item.revision} · ${dateLabel(item.createdAt)}`));
  if (item.state === 'PENDING') {
    row.append(element('p', 'field-hint', 'The instruction is saved. Another edit must wait until this update completes.'));
    const retry = button('Retry saved update', () => retryOperation(item.operationId, refresh)); retry.dataset.operationRetry = item.operationId; row.append(retry);
  }
  const reference = element('details', 'operation-reference'); reference.append(element('summary', '', 'Update reference'), element('p', '', item.operationId)); row.append(reference);
  return row;
}

async function loadList(page = 1) {
  const requestId = ++listGeneration;
  listPage = page; const root = $('case-list'); root.replaceChildren(); $('case-list-pagination').hidden = true;
  status('case-list-status', 'Loading visible case files…');
  try {
    const result = await read('/api/analysis-cases?' + new URLSearchParams({page, pageSize: 10}));
    if (requestId !== listGeneration) return;
    if (!result.items.length) root.append(emptyState('No case files on this page', 'Create an internal case for a vehicle to begin your analysis.', 'New case', '/cases/new'));
    for (const item of result.items) {
      const card = element('article', 'case-file'), head = element('div', 'case-file-head');
      head.append(element('span', 'eyebrow', `CASE #${item.caseId}`), element('span', 'case-badge', item.syncState === 'PENDING' ? 'Awaiting completion' : item.status));
      card.append(head, link(item.title, `/cases/${item.caseId}`, 'case-title-link'), element('p', 'muted', vehicleName(item.vehicle)),
        element('p', 'field-hint', `${item.priority} priority · Created ${dateLabel(item.createdAt)} · Creator #${item.createdBy}`));
      root.append(card);
    }
    status('case-list-status', `${count(result.pagination.total)} visible case files.`); pagination('case-list-pagination', result.pagination, loadList);
    if (!result.items.length && page > 1) root.append(button('Return to first page', () => loadList(1)));
  } catch (error) { if (requestId === listGeneration) readFailure(error, 'case-list-status'); }
}

async function loadOperations(page = 1) {
  const requestId = ++operationGeneration;
  operationPage = page; const root = $('case-operations'); root.replaceChildren(); $('case-operations-pagination').hidden = true;
  status('case-operations-status', 'Loading saved update receipts…');
  try {
    const result = await read('/api/analysis-cases/operations?' + new URLSearchParams({state: $('case-operation-state').value, page, pageSize: 10}));
    if (requestId !== operationGeneration) return;
    if (!result.items.length) root.append(element('p', 'field-hint', 'No saved updates in this category on this page.'));
    for (const item of result.items) root.append(operationCard(item, () => Promise.all([loadOperations(operationPage), loadList(listPage)])));
    status('case-operations-status', `${count(result.pagination.total)} saved updates in this category.`); pagination('case-operations-pagination', result.pagination, loadOperations); lockControls();
    if (!result.items.length && page > 1) root.append(button('Return to first page', () => loadOperations(1)));
  } catch (error) { if (requestId === operationGeneration) readFailure(error, 'case-operations-status'); }
}

async function searchVehicles(page = 1) {
  const searchId = ++vehicleSearchGeneration, root = $('case-vehicle-results'); root.replaceChildren(); $('case-vehicle-pagination').hidden = true;
  selectedVehicle = null; $('case-selected-vehicle').textContent = 'Choose a vehicle below.'; lockControls();
  const query = new URLSearchParams({page, pageSize: 10});
  for (const field of ['make', 'model', 'year']) if ($('case-' + field).value.trim()) query.set(field, $('case-' + field).value.trim());
  status('case-vehicle-status', 'Searching the vehicle catalogue…');
  try {
    const result = await read('/api/vehicles/search?' + query); if (searchId !== vehicleSearchGeneration) return;
    for (const item of result.items) {
      const row = element('div', 'case-vehicle-option'); row.append(element('p', '', vehicleName(item)));
      const choose = button('Select vehicle', () => {
        if (busy || command) return;
        selectedVehicle = item; $('case-selected-vehicle').textContent = vehicleName(item);
        for (const option of root.querySelectorAll('button')) { option.textContent = 'Select vehicle'; option.setAttribute('aria-pressed', 'false'); }
        choose.textContent = 'Selected'; choose.setAttribute('aria-pressed', 'true'); lockControls();
      });
      choose.dataset.caseWrite = ''; choose.setAttribute('aria-pressed', 'false'); row.append(choose); root.append(row);
    }
    status('case-vehicle-status', result.items.length ? `${count(result.pagination.total)} vehicle identities found. Select one to continue.` : 'No matching vehicles. Try exact names or leave the year blank.');
    pagination('case-vehicle-pagination', result.pagination, searchVehicles); lockControls();
  } catch (error) { if (searchId === vehicleSearchGeneration) readFailure(error, 'case-vehicle-status'); }
}

function confirmRemoval(title, message, action) {
  if (busy || command || pending || loadingDetail || !actor) return;
  confirmation = action; $('case-confirm-title').textContent = title; $('case-confirm-description').textContent = message; $('case-confirm-dialog').showModal();
}

function renderEntries(kind, entries) {
  const root = $('case-' + kind + '-list'); root.replaceChildren(); $('case-' + kind + '-count').textContent = `${entries.length} / 100`;
  if (!entries.length) root.append(element('p', 'field-hint', `No ${kind} recorded yet.`));
  const isNote = kind === 'notes', label = isNote ? 'note' : 'finding', field = isNote ? 'text' : 'observation';
  for (const entry of entries) {
    const entryId = entry[isNote ? 'noteId' : 'findingId'], row = element('article', 'case-entry'); row.dataset.entryId = entryId;
    row.append(element('p', 'record-meta', `Author #${entry.authorId} · ${dateLabel(entry.createdAt)}`), element('p', 'case-entry-text', entry[field]));
    const editor = element('details'), summary = element('summary', '', `Edit ${label}`), form = element('form', 'case-form case-mutation'); form.method = 'post';
    const textarea = element('textarea'); textarea.id = `edit-${entryId}`; textarea.value = entry[field]; textarea.required = true; textarea.maxLength = 4000; textarea.rows = 4;
    const inputLabel = element('label', '', isNote ? 'Note text' : 'Finding observation'); inputLabel.htmlFor = textarea.id;
    const save = element('button', 'button button-quiet button-small', 'Save changes'); save.type = 'submit';
    form.append(inputLabel, textarea, save); form.addEventListener('submit', event => { event.preventDefault(); change(`${casePath()}/${kind}/${entryId}`, 'PATCH', {[field]: textarea.value}, `Edit ${label}`); });
    editor.append(summary, form); row.append(editor);
    const remove = button(`Remove ${label}`, () => confirmRemoval(`Remove this ${label}?`, 'This removes the internal entry. Imported safety records remain available.', () => change(`${casePath()}/${kind}/${entryId}`, 'DELETE', undefined, `Remove ${label}`)), 'remove-link');
    remove.dataset.caseWrite = ''; row.append(remove); root.append(row);
  }
}

function renderContent(content) {
  $('case-tags').value = content.tags.join('\n'); $('case-components').value = content.suspectedComponents.join('\n');
  const root = $('case-linked-complaints'); root.replaceChildren(); $('case-linked-count').textContent = `${content.linkedComplaints.length} / 200`;
  if (!content.linkedComplaints.length) root.append(element('p', 'field-hint', 'No complaints linked. Find matching reports below to build your evidence set.'));
  for (const odi of content.linkedComplaints) {
    const row = element('div', 'case-linked-row'); row.append(link(`ODI ${odi} →`, recordURL('complaints', odi), 'text-link'));
    const remove = button('Unlink', () => confirmRemoval('Unlink this complaint?', `Remove ODI ${odi} from this case? The imported complaint will remain available.`, () => change(`${casePath()}/complaints/${encodeURIComponent(odi)}`, 'DELETE', undefined, 'Unlink complaint')), 'remove-link');
    remove.dataset.caseWrite = ''; row.append(remove); root.append(row);
  }
  renderEntries('notes', content.notes); renderEntries('findings', content.findings);
}

async function loadHistory(page = 1) {
  const requestId = ++historyGeneration;
  $('case-history').replaceChildren(); $('case-history-pagination').hidden = true; status('case-history-status', 'Loading history…');
  try {
    const result = await read(casePath() + '/history?' + new URLSearchParams({page, pageSize: 10}));
    if (requestId !== historyGeneration) return;
    for (const item of result.items) {
      const row = element('li'); row.append(element('strong', '', `${item.oldStatus} → ${item.newStatus}`), element('span', '', dateLabel(item.changedAt))); $('case-history').append(row);
    }
    status('case-history-status', result.items.length ? `${count(result.pagination.total)} status changes.` : 'No status changes recorded.'); pagination('case-history-pagination', result.pagination, loadHistory);
  } catch (error) { if (requestId === historyGeneration) readFailure(error, 'case-history-status'); }
}

async function searchComplaints(page = 1) {
  if (!caseData || pending) return;
  complaintPage = page; const searchId = ++complaintSearchGeneration, root = $('case-complaint-results'); root.replaceChildren(); $('case-complaint-pagination').hidden = true;
  const query = new URLSearchParams({modelYearId: caseData.analysisCase.modelYearId, page, pageSize: 5});
  for (const field of ['component', 'q']) if ($('case-complaint-' + field).value.trim()) query.set(field, $('case-complaint-' + field).value.trim());
  status('case-complaint-status', 'Finding reports for this case vehicle…');
  try {
    const result = await read('/api/complaints?' + query); if (searchId !== complaintSearchGeneration) return;
    for (const item of result.items) {
      const row = element('article', 'case-candidate'); row.dataset.odi = item.odiNumber;
      row.append(link(`ODI ${item.odiNumber} →`, recordURL('complaints', item.odiNumber), 'text-link'), element('p', 'record-meta', `${item.components.join(' · ')} · Received ${dateLabel(item.receivedDate)}`), element('p', 'record-preview', item.narrativePreview));
      const linked = caseData.content.linkedComplaints.includes(item.odiNumber);
      const add = button(linked ? 'Already linked' : 'Link to this case', () => change(casePath() + '/complaints', 'POST', {odiNumber: item.odiNumber}, 'Link complaint'));
      add.dataset.caseWrite = ''; add.dataset.alreadyLinked = String(linked); row.append(add); root.append(row);
    }
    status('case-complaint-status', `${count(result.pagination.total)} matching complaints for this case vehicle.`); pagination('case-complaint-pagination', result.pagination, searchComplaints); lockControls();
  } catch (error) { if (searchId === complaintSearchGeneration) readFailure(error, 'case-complaint-status'); }
}

async function loadDetail() {
  const requestId = ++detailGeneration;
  complaintSearchGeneration++;
  detailAvailable = false;
  loadingDetail = true; lockControls();
  try {
    const result = await read(casePath()); if (requestId !== detailGeneration) return;
    caseData = result; pending = result.sync.state === 'PENDING'; detailAvailable = true;
    const item = result.analysisCase;
    $('case-page-title').textContent = item.title; $('case-page-subtitle').textContent = `Case #${item.caseId} · ${vehicleName(item.vehicle)}`;
    $('case-profile-link').href = profileURL(item.vehicle); $('case-title').value = item.title; $('case-priority').value = item.priority; $('case-status').value = item.status;
    $('case-metadata').textContent = `Created ${dateLabel(item.createdAt)} · Creator #${item.createdBy} · Assignee #${item.assignedTo} · Revision ${item.contentRevision}`;
    $('case-closed-at').textContent = item.closedAt ? `Closed ${dateLabel(item.closedAt)}` : 'This case is open for analysis.';
    $('case-sync-label').textContent = pending ? 'Awaiting completion' : 'Content saved'; $('case-pending').hidden = !pending;
    $('case-pending-operation').replaceChildren(); $('case-flexible-content').hidden = pending;
    if (pending) {
      for (const id of ['case-linked-complaints', 'case-notes-list', 'case-findings-list', 'case-complaint-results']) $(id).replaceChildren();
      $('case-tags').value = ''; $('case-components').value = '';
      $('case-pending-operation').append(operationCard(result.sync, loadDetail));
    } else { renderContent(result.content); if ($('case-complaint-picker').open) searchComplaints(complaintPage); }
    loadHistory();
  } catch (error) {
    if (requestId !== detailGeneration || error.name === 'AbortError' || !actor) return;
    if ([404, 503].includes(error.status)) {
      $('case-workspace').hidden = true; $('case-page-title').textContent = error.status === 404 ? 'Case not found' : 'Case content unavailable';
      $('case-page-subtitle').textContent = 'Return to the case list or retry loading this case.';
      $('case-gate').hidden = false; $('case-gate').replaceChildren(element('p', '', error.message), button('Retry loading', () => { $('case-workspace').hidden = false; $('case-gate').hidden = true; loadDetail(); }), link('All cases →', '/cases', 'text-link'));
    } else readFailure(error, 'case-message');
  } finally { if (requestId === detailGeneration) { loadingDetail = false; lockControls(); } }
}
async function refreshDetail() { await loadDetail(); }

function bindEvents() {
  $('case-command-retry').addEventListener('click', executeCommand);
  $('case-list-refresh')?.addEventListener('click', () => loadList(listPage));
  $('case-operations-refresh')?.addEventListener('click', () => loadOperations(operationPage));
  $('case-operation-state')?.addEventListener('change', () => loadOperations(1));
  $('case-vehicle-search')?.addEventListener('submit', event => { event.preventDefault(); if (!busy && !command) searchVehicles(); });
  $('case-create-form')?.addEventListener('submit', event => {
    event.preventDefault(); if (!selectedVehicle) return;
    change('/api/analysis-cases', 'POST', {modelYearId: selectedVehicle.modelYearId, title: $('case-create-title').value, priority: $('case-create-priority').value}, 'Create case', operation => location.assign(`/cases/${operation.caseId}`));
  });
  $('case-detail-refresh')?.addEventListener('click', () => { if (!busy) loadDetail(); });
  $('case-metadata-form')?.addEventListener('submit', event => { event.preventDefault(); change(casePath(), 'PATCH', {title: $('case-title').value, priority: $('case-priority').value, status: $('case-status').value}, 'Update case details'); });
  $('case-content-form')?.addEventListener('submit', event => {
    event.preventDefault(); const body = {};
    for (const [field, id] of [['tags', 'case-tags'], ['suspectedComponents', 'case-components']]) {
      const values = $(id).value.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
      if (values.length > 20 || values.some(value => value.length > 100)) { status('case-message', 'Each label list allows up to 20 entries of 100 characters. Put each entry on its own line.', 'error'); return; }
      body[field] = values;
    }
    change(casePath() + '/content', 'PATCH', body, 'Update case labels');
  });
  $('case-complaint-picker')?.addEventListener('toggle', () => { if ($('case-complaint-picker').open && caseData && !pending && !$('case-complaint-results').children.length) searchComplaints(); });
  $('case-complaint-search')?.addEventListener('submit', event => { event.preventDefault(); searchComplaints(); });
  for (const kind of ['notes', 'findings']) $('case-' + kind + '-form')?.addEventListener('submit', event => {
    event.preventDefault(); const field = kind === 'notes' ? 'text' : 'observation', input = $('case-' + kind + '-text');
    change(`${casePath()}/${kind}`, 'POST', {[field]: input.value}, kind === 'notes' ? 'Add note' : 'Add finding', async () => { input.value = ''; await loadDetail(); });
  });
  $('case-delete')?.addEventListener('click', () => confirmRemoval('Delete this case?', 'This removes the internal case, notes, findings and status history. Imported safety records remain available. A saved deletion update may still need completion.', () => change(casePath(), 'DELETE', undefined, 'Delete case', () => location.assign('/cases'))));
  $('case-confirm-form')?.addEventListener('submit', event => { event.preventDefault(); const action = confirmation; confirmation = null; $('case-confirm-dialog').close(); if (action) action(); });
  window.addEventListener('beforeunload', event => { if (command) { event.preventDefault(); event.returnValue = ''; } });
  document.addEventListener('sessionexpired', () => { if ($('case-page')) deny('Your sign-in has expired. Sign in again to reopen the workspace.', true); });
}

export async function initCases(auth) {
  if (!bound) { bindEvents(); bound = true; }
  clearCases();
  if (!auth.user) { deny(auth.error || 'Use your application account to continue. Reading public safety records does not require sign-in.', true); return; }
  if (!authorized(auth.user)) { deny('Your account is a normal user. Ask the project administrator to assign ANALYST access. Public research and personal vehicles remain available.'); return; }
  actor = auth.user; $('case-gate').hidden = true; $('case-workspace').hidden = false; $('case-new-link').hidden = caseView() === 'new';
  if (caseView() === 'list') {
    $('case-page-title').textContent = 'Analyst cases'; $('case-page-subtitle').textContent = actor.role === 'ADMIN' ? 'Review case work across the team.' : 'Your evidence, notes and findings in one place.';
    $('case-role-note').textContent = actor.role === 'ADMIN' ? 'Admin oversight includes all analyst cases and saved updates. These are internal cases, separate from official NHTSA investigations.' : 'You manage cases you created. These are internal cases, separate from official NHTSA investigations.';
    await Promise.all([loadList(1), loadOperations(1)]);
  } else if (caseView() === 'new') {
    $('case-page-title').textContent = 'New analyst case'; $('case-page-subtitle').textContent = 'Choose one vehicle identity and give the case a clear focus.';
    const params = new URLSearchParams(location.search);
    for (const field of ['year', 'make', 'model']) if (params.has(field)) $('case-' + field).value = params.get(field);
    $('case-selected-vehicle').textContent = 'Choose a vehicle first.';
    if (params.has('make') && params.has('model')) await searchVehicles();
  } else await loadDetail();
  lockControls();
}
