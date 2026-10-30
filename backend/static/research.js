/* Public research pages use the existing read-only APIs; no database credentials reach the browser. */
import {api} from './api.js';
import {$, count, element, link, button, status, dateLabel, vehicleName, profileURL, emptyState, pagination, addTextSection, recordURL} from './ui.js';

const complaintFields = ['make', 'model', 'year', 'component', 'q', 'receivedFrom', 'receivedTo', 'crash', 'fire', 'hasInjuries', 'hasFatalities'];
const incidentFields = ['receivedFrom', 'receivedTo', 'crash', 'fire', 'hasInjuries', 'hasFatalities'];
const flag = value => value === null || value === undefined ? 'Unknown' : value ? 'Yes' : 'No';
const knownCount = value => value === null || value === undefined ? 'Unknown' : count(value);

function complaintCard(item) {
  const card = element('article', 'panel complaint-card'), meta = element('div', 'record-meta');
  meta.append(element('span', 'record-identifier', `ODI ${item.odiNumber}`), element('span', '', `Received ${dateLabel(item.receivedDate)}`));
  card.append(meta, element('h3', '', vehicleName(item.vehicle)), element('p', 'complaint-components', item.components.join(' · ') || 'Component not reported'),
    element('p', 'record-preview', item.narrativePreview || 'No consumer narrative was supplied.'));
  const foot = element('div', 'complaint-card-foot');
  foot.append(element('p', 'incident-summary', `Crash: ${flag(item.incident.crash)} · Fire: ${flag(item.incident.fire)} · Injuries: ${knownCount(item.incident.injuries)} · Fatalities: ${knownCount(item.incident.fatalities)}`),
    link('Read full complaint →', recordURL('complaints', item.odiNumber), 'text-link'));
  card.append(foot); return card;
}

export function initComplaints() {
  const form = $('complaint-form'), root = $('complaint-results');
  let controller, activeFilters = new URLSearchParams();
  function restore() {
    form.reset();
    $('complaint-receivedTo').setCustomValidity('');
    const params = new URLSearchParams(location.search);
    for (const field of complaintFields) if (params.has(field)) $('complaint-' + field).value = params.get(field);
    $('incident-filters').open = incidentFields.some(field => params.get(field));
    activeFilters = new URLSearchParams();
    // Preserve malformed values from pasted URLs for the API to validate, even if a date/select input cannot display them.
    for (const field of complaintFields) if (params.has(field)) activeFilters.set(field, params.get(field));
    return params.get('page') || '1';
  }
  function fromForm() {
    const values = new URLSearchParams();
    for (const field of complaintFields) {
      const value = $('complaint-' + field).value.trim();
      if (value) values.set(field, value);
    }
    return values;
  }
  function address(query, push) {
    const url = '/complaints' + (query.size ? '?' + query : '');
    if (push && url !== location.pathname + location.search) history.pushState(null, '', url);
  }
  async function load(pageNumber = 1, push = true) {
    controller?.abort(); controller = new AbortController(); const active = controller;
    const query = new URLSearchParams(activeFilters);
    if (String(pageNumber) !== '1') query.set('page', pageNumber);
    address(query, push); query.set('pageSize', 50);
    root.replaceChildren(); $('complaint-pagination').hidden = true;
    $('complaint-count-label').textContent = 'Searching…';
    $('complaint-results-section').setAttribute('aria-busy', 'true');
    status('complaint-status', 'Finding matching reports…');
    try {
      const result = await api('/api/complaints?' + query, {signal: active.signal});
      if (controller !== active) return;
      $('complaint-count-label').textContent = `${count(result.pagination.total)} found`;
      for (const item of result.items) root.append(complaintCard(item));
      if (!result.items.length) root.append(emptyState('No reports on this page', 'Try fewer filters, an exact component name, or return to the first page.'));
      const {page, pageSize, total} = result.pagination;
      status('complaint-status', result.items.length ? `Showing ${count((page - 1) * pageSize + 1)}–${count(Math.min(page * pageSize, total))} of ${count(total)} reports · Newest received first.` : `${count(total)} matching reports in the imported snapshot.`);
      pagination('complaint-pagination', result.pagination, number => load(number));
      if (!result.items.length && page > 1) root.append(button('Return to first page', () => load(1)));
    } catch (error) {
      if (error.name !== 'AbortError' && controller === active) {
        $('complaint-count-label').textContent = 'Unavailable'; status('complaint-status', error.message, 'error');
        root.append(emptyState('Reports could not be loaded', 'Check the filters or try the request again.'), button('Retry these filters', () => load(pageNumber, false)));
      }
    } finally { if (controller === active) $('complaint-results-section').setAttribute('aria-busy', 'false'); }
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    const start = $('complaint-receivedFrom'), end = $('complaint-receivedTo');
    end.setCustomValidity(start.value && end.value && start.value > end.value ? 'The end date must be on or after the start date.' : '');
    if (!form.reportValidity()) return;
    activeFilters = fromForm(); load();
  });
  for (const id of ['receivedFrom', 'receivedTo']) $('complaint-' + id).addEventListener('input', () => $('complaint-receivedTo').setCustomValidity(''));
  $('complaint-reset').addEventListener('click', () => { form.reset(); $('complaint-receivedTo').setCustomValidity(''); $('incident-filters').open = false; activeFilters = new URLSearchParams(); load(); });
  window.addEventListener('popstate', () => load(restore(), false));
  load(restore(), false);
}

function fact(root, label, value) {
  const row = element('div', 'detail-fact'); row.append(element('dt', '', label), element('dd', '', value ?? 'Not reported')); root.append(row);
}
function facts(root, title) { root.append(element('h2', '', title)); const list = element('dl', 'fact-list'); root.append(list); return list; }
function table(headers, rows, label) {
  const wrap = element('div', 'table-wrap'); wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', label);
  const grid = element('table', 'research-table'), head = element('thead'), tr = element('tr'), body = element('tbody');
  for (const header of headers) { const cell = element('th', '', header); cell.scope = 'col'; tr.append(cell); }
  head.append(tr);
  for (const values of rows) { const row = element('tr'); for (const value of values) { const cell = element('td'); cell.append(value instanceof Node ? value : document.createTextNode(value ?? 'Not reported')); row.append(cell); } body.append(row); }
  grid.append(head, body); wrap.append(grid); return wrap;
}

function relatedList(kind, identifier, records = false) {
  const prefix = records ? 'source-records' : 'related-vehicles', root = $(prefix);
  let controller, loaded = false;
  async function load(pageNumber = 1) {
    controller?.abort(); controller = new AbortController(); const active = controller;
    root.replaceChildren(); root.setAttribute('aria-busy', 'true'); $(prefix + '-pagination').hidden = true;
    status(prefix + '-status', records ? 'Loading source rows…' : 'Loading related vehicles…');
    try {
      const result = await api(`/api/${kind}/${encodeURIComponent(identifier)}/${records ? 'records' : 'vehicles'}?` + new URLSearchParams({page: pageNumber, pageSize: 20}), {signal: active.signal});
      if (controller !== active) return;
      if (!result.items.length) root.append(element('p', 'status-line', 'No related rows on this page.'));
      else if (records) {
        root.append(table(['Vehicle', 'Component', 'Production dates', 'Source archive / line'], result.items.map(item => [
          link(vehicleName(item), profileURL(item)), item.component || 'Not reported',
          `${dateLabel(item.manufacturingStarted)} – ${dateLabel(item.manufacturingEnded)}`,
          `${item.sourceArchive ?? 'Unknown archive'} / ${item.sourceLine ?? 'Unknown line'}`,
        ]), 'Recall source rows; scroll horizontally if needed'));
      } else {
        root.append(table(['Model year', 'Make', 'Model', 'Research'], result.items.map(item => [
          String(item.year), item.make, item.model, link('View safety profile →', profileURL(item)),
        ]), 'Related vehicle identities; scroll horizontally if needed'));
      }
      status(prefix + '-status', `${count(result.pagination.total)} ${records ? 'source rows' : 'vehicle identities'} in the imported snapshot.`);
      pagination(prefix + '-pagination', result.pagination, load); loaded = true;
    } catch (error) {
      if (error.name !== 'AbortError' && controller === active) {
        status(prefix + '-status', error.message, 'error'); root.append(button('Retry', () => load(pageNumber)));
      }
    } finally { if (controller === active) root.setAttribute('aria-busy', 'false'); }
  }
  if (records) $('source-records-disclosure').addEventListener('toggle', () => { if ($('source-records-disclosure').open && !loaded && !controller) load(); });
  else load();
}

function renderComplaint(record) {
  const narrative = $('detail-narrative'), sidebar = $('detail-facts');
  $('detail-subtitle').textContent = vehicleName(record.vehicle);
  addTextSection(narrative, 'Consumer narrative', record.narrative);
  const list = facts(sidebar, 'Report details');
  fact(list, 'Vehicle', vehicleName(record.vehicle)); fact(list, 'Components', record.components.join(' · ') || 'Not reported');
  fact(list, 'Received', dateLabel(record.receivedDate)); fact(list, 'Incident date', dateLabel(record.incidentDate));
  fact(list, 'Manufacturer', record.manufacturer); fact(list, 'Reported mileage', knownCount(record.mileage)); fact(list, 'Occurrences', knownCount(record.occurrences));
  fact(list, 'Crash / fire', `${flag(record.incident.crash)} / ${flag(record.incident.fire)}`);
  fact(list, 'Injuries / fatalities', `${knownCount(record.incident.injuries)} / ${knownCount(record.incident.fatalities)}`);
  sidebar.append(link('View vehicle safety profile →', profileURL(record.vehicle), 'text-link'));
  const source = record.source;
  const provenance = element('details', 'complaint-provenance'); provenance.append(element('summary', '', 'Imported source information'));
  const sourceFacts = element('dl', 'fact-list');
  fact(sourceFacts, 'Archives', source.archives?.join(', ')); fact(sourceFacts, 'Source row IDs', source.rowIds?.join(', '));
  fact(sourceFacts, 'Merged component rows', knownCount(source.componentRowCount));
  fact(sourceFacts, 'Conflicting source columns', source.conflictingScalarColumns?.join(', ') || 'None recorded');
  provenance.append(element('p', 'field-hint', 'Multiple component rows with the same ODI number are merged into one complaint. Source differences are retained for review.'), sourceFacts);
  narrative.append(provenance);
}

function renderOfficial(kind, record, identifier) {
  const narrative = $('detail-narrative'), sidebar = $('detail-facts'), isRecall = kind === 'recalls';
  $('detail-subtitle').textContent = isRecall ? record.manufacturer || 'Reporting manufacturer not supplied' : record.subject || 'Subject not supplied';
  addTextSection(narrative, isRecall ? 'Recall summary' : 'Official summary', record.summary);
  if (isRecall) { addTextSection(narrative, 'Consequence', record.consequence); addTextSection(narrative, 'Remedy', record.remedy); }
  const list = facts(sidebar, isRecall ? 'Campaign details' : 'Investigation details');
  fact(list, isRecall ? 'Report date' : 'Opened', dateLabel(isRecall ? record.reportDate : record.openedDate));
  fact(list, 'Components', record.components.join(' · ') || 'Not reported');
  fact(list, 'Related vehicle identities', count(record.affectedVehicleCount));
  if (isRecall) {
    fact(list, 'Potentially affected units', knownCount(record.potentiallyAffected)); fact(list, 'Do not drive flag', flag(record.doNotDrive)); fact(list, 'Park outside flag', flag(record.parkOutside));
    fact(list, 'Source rows', count(record.sourceRecordCount));
    $('source-records-section').hidden = false; relatedList(kind, identifier, true);
  } else {
    fact(list, 'Snapshot status', record.status); fact(list, 'Closed', dateLabel(record.closedDate)); fact(list, 'Type', record.investigationType);
    fact(list, 'Manufacturers', record.manufacturers.join(' · ') || 'Not reported');
    const root = $('linked-recalls'); $('linked-recalls-section').hidden = false;
    if (!record.linkedRecalls.length) root.append(element('p', 'status-line', 'No linked recall campaigns in this imported record.'));
    for (const recall of record.linkedRecalls) {
      const row = element('div', 'linked-record');
      row.append(recall.inImportedSnapshot ? link(recall.campaignNumber + ' →', recordURL('recalls', recall.campaignNumber), 'text-link') : element('span', '', recall.campaignNumber),
        element('span', 'muted', recall.inImportedSnapshot ? 'Available in the imported snapshot' : 'Referenced by the investigation; recall details are outside this snapshot'));
      root.append(row);
    }
  }
  $('related-vehicle-count').textContent = `${count(record.affectedVehicleCount)} identities`;
  $('related-vehicles-section').hidden = false; relatedList(kind, identifier);
}

export async function initRecord() {
  const kind = $('record-page').dataset.kind;
  let identifier = location.pathname.split('/').pop();
  try { identifier = decodeURIComponent(identifier); } catch { /* The API will reject malformed record numbers. */ }
  async function load() {
    $('detail-content').hidden = true; $('detail-status').replaceChildren(); status('detail-status', 'Loading the full record…');
    try {
      const result = await api(`/api/${kind}/${encodeURIComponent(identifier)}`);
      const record = result[kind === 'complaints' ? 'complaint' : kind === 'recalls' ? 'recall' : 'investigation'];
      const number = record.odiNumber ?? record.campaignNumber ?? record.investigationNumber;
      $('detail-title').textContent = kind === 'complaints' ? `Complaint ${number}` : kind === 'recalls' ? `Recall ${number}` : `Investigation ${number}`;
      document.title = $('detail-title').textContent + ' · RecallScope';
      $('detail-interpretation').textContent = result.interpretation;
      if (kind === 'complaints') renderComplaint(record); else renderOfficial(kind, record, number);
      status('detail-status'); $('detail-content').hidden = false;
    } catch (error) {
      $('detail-title').textContent = error.status === 404 ? 'Record not in this snapshot' : 'Record unavailable';
      $('detail-subtitle').textContent = 'Check the record number, or return to vehicle search and choose a record.';
      status('detail-status', error.message, 'error');
      if (![400, 404].includes(error.status)) $('detail-status').append(document.createTextNode(' '), button('Retry', load));
    }
  }
  await load();
}
