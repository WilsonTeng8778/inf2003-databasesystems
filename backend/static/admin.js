/* Admin views use guarded APIs; role changes never write directly to either DBMS. */
import {api} from './api.js';
import {$, element, link, button, status, count, emptyState, pagination} from './ui.js';

let actor = null, generation = 0, bound = false, busy = false, ready = false, uncertain = false;
let refreshIdentity, selection = null, deletionSelection = null, userPage = 1, importPage = 1, filters = new URLSearchParams();
let usersGeneration = 0, importsGeneration = 0, summaryGeneration = 0;
const view = () => $('admin-page')?.dataset.view;
const aborted = () => Object.assign(new Error('Administrator access changed'), {name: 'AbortError'});
const roleLabel = role => ({NORMAL_USER: 'Normal user', ANALYST: 'Analyst', ADMIN: 'Admin'})[role] || role;
function timestamp(value) {
  if (!value) return 'Not recorded';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? 'Not recorded' : new Intl.DateTimeFormat('en', {year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(date);
}
function lockControls() {
  for (const node of document.querySelectorAll('[data-admin-write],.admin-role-form select,.admin-role-form button')) node.disabled = !actor || !ready || busy || uncertain;
  $('admin-refresh').disabled = busy; $('admin-review-roles').disabled = busy;
  $('admin-delete-confirm').disabled = !actor || !ready || busy || uncertain || !deletionSelection || $('admin-delete-email').value.trim().toLowerCase() !== deletionSelection.email;
}
export function clearAdministration() {
  if (!$('admin-page')) return;
  generation++; usersGeneration++; importsGeneration++; summaryGeneration++;
  actor = null; selection = null; deletionSelection = null; busy = false; ready = false; uncertain = false;
  $('admin-workspace').hidden = true; $('admin-refresh').hidden = true; $('admin-uncertain').hidden = true;
  $('admin-page-title').textContent = 'Administration'; $('admin-page-subtitle').textContent = 'Administrator access required';
  for (const id of ['admin-users','admin-imports','admin-datasets']) $(id)?.replaceChildren();
  for (const id of ['admin-users-status','admin-imports-status','admin-datasets-status','admin-schema-version','admin-current-user','admin-role-description']) if ($(id)) $(id).textContent = '';
  for (const node of document.querySelectorAll('#admin-workspace .pagination')) { node.replaceChildren(); node.hidden = true; }
  $('admin-role-dialog').close();
  $('admin-delete-dialog').close(); $('admin-delete-email').value = ''; $('admin-delete-description').textContent = '';
  $('admin-gate').hidden = false; $('admin-gate').replaceChildren(element('p', '', 'Checking administrator access…')); status('admin-message'); lockControls();
}
function deny(message, signIn = false) {
  clearAdministration();
  for (const node of document.querySelectorAll('[data-admin-nav]')) node.hidden = true;
  $('admin-gate').replaceChildren(emptyState(signIn ? 'Sign in to continue' : 'Administrator access required', message,
    signIn ? 'Sign in' : 'Return to vehicle search', signIn ? '/login?' + new URLSearchParams({next: location.pathname + location.search}) : '/vehicles'));
}
async function read(path) {
  const active = generation; const result = await api(path);
  if (active !== generation || !actor) throw aborted();
  return result;
}
async function failure(error, id) {
  if (!actor || error.name === 'AbortError') return;
  ready = false; lockControls();
  if (error.status === 401) { deny('Your sign-in expired. Sign in again to open administration.', true); return; }
  if (error.status === 403) {
    const identity=await refreshIdentity();
    deny(identity?'This session no longer allows administration. Sign in with an admin account or continue with your current permissions.':'Your sign-in expired. Sign in again to open administration.',!identity); return;
  }
  status(id, error.message + ' Use Refresh view to try again.', 'error');
}
function fact(root, label, value) {
  const row = element('div', 'detail-fact'); row.append(element('dt', '', label), element('dd', '', value)); root.append(row);
}
function runCard(item) {
  const card = element('article', 'admin-import-card'); card.dataset.importId = item.importId;
  const head = element('div', 'section-heading'); head.append(element('h3', '', `Attempt #${item.importId} · ${item.dataset}`), element('span', 'case-badge', item.status));
  card.append(head, element('p', 'field-hint', `Started ${timestamp(item.startedAt)} · Finished ${timestamp(item.completedAt)}`));
  const metrics = element('dl', 'import-metrics');
  for (const [label, key] of [['Rows read','recordsRead'],['Inserted entities','recordsInserted'],['Updated entities','recordsUpdated'],['Skipped rows','recordsSkipped'],['Rejected rows','recordsRejected']]) fact(metrics, label, count(item[key]));
  card.append(metrics);
  if (item.hasError) card.append(element('p', 'notice notice-error', item.failureCategory ? `Recorded failure category: ${item.failureCategory}. This is historical import information.` : 'A failure was recorded. Detailed diagnostics are not exposed here.'));
  const source = element('details', 'operation-reference'); source.append(element('summary', '', 'Source fingerprint'), element('p', '', item.sourceFingerprint || 'No fingerprint recorded for this import.'));
  card.append(source); return card;
}
async function loadSummary() {
  const requestId = ++summaryGeneration, root = $('admin-datasets'); root.replaceChildren(); root.setAttribute('aria-busy','true'); status('admin-datasets-status','Reading current dataset counts…');
  try {
    const result = await read('/api/admin/datasets'); if (requestId !== summaryGeneration) return false;
    for (const item of result.items) {
      const card = element('article','panel admin-dataset-card'); card.dataset.dataset = item.key;
      card.append(element('span','eyebrow',item.database),element('h3','',item.title),element('strong','dataset-count',count(item.recordCount)),element('p','muted',item.unit));
      for (const relation of item.relationships) card.append(element('p','dataset-relationship',`${count(relation.count)} ${relation.label.toLowerCase()}`));
      const archives = element('details','dataset-archives'); archives.append(element('summary','','Source archives'));
      const list = element('ul'); for (const name of item.sourceArchives) list.append(element('li','',name)); archives.append(list); card.append(archives);
      card.append(element('p','field-hint',item.latestRun ? `Latest recorded attempt: ${item.latestRun.status} · ${timestamp(item.latestRun.startedAt)}` : 'No import attempt recorded for this dataset.'),
        link('Review import attempts →','/admin/imports?'+new URLSearchParams({dataset:item.key}),'text-link')); root.append(card);
    }
    $('admin-schema-version').textContent = `SQL schema version ${result.schemaVersion ?? 'unknown'}`; $('admin-data-interpretation').textContent = result.interpretation;
    status('admin-datasets-status',`Counts checked ${timestamp(result.checkedAtUtc)}.`); return true;
  } catch (error) { if (requestId === summaryGeneration) await failure(error,'admin-datasets-status'); return false; }
  finally { if (requestId === summaryGeneration) root.setAttribute('aria-busy','false'); }
}
function userCard(item) {
  const card = element('article','admin-user-card'); card.dataset.userId = item.userId;
  const identity = element('div'); identity.append(element('h3','',item.email),element('p','field-hint',`Account #${item.userId} · Created ${timestamp(item.createdAt)}${item.userId===actor.userId?' · Your account':''}`));
  const form = element('form','admin-role-form'); form.method = 'post';
  const label = element('label','','Application role'), select = element('select'); select.id = 'admin-role-'+item.userId; label.htmlFor = select.id;
  for (const role of ['NORMAL_USER','ANALYST','ADMIN']) { const option = element('option','',roleLabel(role)); option.value = role; select.append(option); } select.value = item.role;
  const change = element('button','button button-quiet button-small','Review change'); change.type = 'submit'; form.append(label,select,change);
  form.addEventListener('submit',event=>{
    event.preventDefault(); if (!actor || !ready || busy || uncertain) return;
    if (select.value===item.role) { status('admin-message','This account already has that role.'); return; }
    selection = {userId:item.userId,email:item.email,oldRole:item.role,role:select.value};
    $('admin-role-description').textContent = `Change ${item.email} from ${roleLabel(item.role)} to ${roleLabel(select.value)}?${item.userId===actor.userId?' You are changing your own access.':''}`;
    $('admin-role-dialog').showModal();
  });
  if (item.userId !== actor.userId) {
    const remove = button('Delete unused account',()=>{
      if(!actor || !ready || busy || uncertain)return;
      deletionSelection = {userId:item.userId,email:item.email}; $('admin-delete-email').value='';
      $('admin-delete-description').textContent=`Permanently delete ${item.email} (account #${item.userId})?`;
      $('admin-delete-dialog').showModal(); lockControls(); $('admin-delete-email').focus();
    },'button button-quiet button-small');
    remove.dataset.adminWrite=''; remove.dataset.deleteUser=item.userId;
    identity.append(remove);
  } else identity.append(element('p','field-hint','Your signed-in account cannot be deleted here.'));
  card.append(identity,form); return card;
}
async function loadUsers(page = 1) {
  userPage = page; const requestId = ++usersGeneration, root = $('admin-users'); root.replaceChildren(); root.setAttribute('aria-busy','true'); $('admin-users-pagination').hidden = true; status('admin-users-status','Loading application accounts…');
  try {
    const result = await read('/api/admin/users?'+new URLSearchParams({page,pageSize:10})); if (requestId!==usersGeneration) return false;
    for (const item of result.items) root.append(userCard(item));
    if (!result.items.length) root.append(element('p','field-hint','No accounts on this page.'));
    status('admin-users-status',`${count(result.pagination.total)} application accounts.`); pagination('admin-users-pagination',result.pagination,number=>refreshView(false,number));
    if (!result.items.length && Number(page)>1) root.append(button('Return to first page',()=>refreshView(false,1)));
    history.replaceState(null,'','/admin/users'+(Number(page)===1?'':'?'+new URLSearchParams({page}))); return true;
  } catch (error) { if (requestId===usersGeneration) await failure(error,'admin-users-status'); return false; }
  finally { if (requestId===usersGeneration) root.setAttribute('aria-busy','false'); }
}
async function loadImports(page = 1) {
  importPage = page; const requestId = ++importsGeneration, root = $('admin-imports'); root.replaceChildren(); root.setAttribute('aria-busy','true'); $('admin-imports-pagination').hidden = true; status('admin-imports-status','Loading recorded import attempts…');
  const query = new URLSearchParams(filters); if (String(page)!=='1') query.set('page',page);
  history.replaceState(null,'','/admin/imports'+(query.size?'?'+query:'')); query.set('pageSize',10);
  try {
    const result = await read('/api/admin/import-runs?'+query); if(requestId!==importsGeneration)return false;
    for(const item of result.items)root.append(runCard(item));
    if(!result.items.length)root.append(element('p','field-hint','No recorded attempts for these filters on this page.'));
    status('admin-imports-status',`${count(result.pagination.total)} import attempts found.`); pagination('admin-imports-pagination',result.pagination,number=>refreshView(false,number));
    if(!result.items.length && Number(page)>1)root.append(button('Return to first page',()=>refreshView(false,1))); return true;
  } catch(error){if(requestId===importsGeneration)await failure(error,'admin-imports-status');return false;}
  finally{if(requestId===importsGeneration)root.setAttribute('aria-busy','false');}
}
async function refreshView(review = false, page) {
  if(!actor || busy)return;
  const active=generation;ready=false;lockControls();
  if(review){const identity=await refreshIdentity();if(active!==generation)return;if(!identity){deny('Your sign-in expired. Sign in again to open administration.',true);return;}if(identity.role!=='ADMIN'){deny('Administrator access is no longer available in this session.');return;}}
  const ok = view()==='overview'?await loadSummary():view()==='users'?await loadUsers(page??userPage):await loadImports(page??importPage);
  if(active!==generation || !actor)return;
  ready=ok;if(ok&&review&&uncertain){uncertain=false;$('admin-uncertain').hidden=true;status('admin-message','Accounts refreshed. Review current records before another change.');}lockControls();
}
async function deleteAccount() {
  if(!deletionSelection || !actor || !ready || busy || uncertain)return;
  const target=deletionSelection, email=$('admin-delete-email').value.trim().toLowerCase();
  if(email!==target.email)return;
  const active=generation;deletionSelection=null;$('admin-delete-dialog').close();busy=true;lockControls();status('admin-message','Deleting unused account…');
  try {
    const result=await api(`/api/admin/users/${target.userId}`,{method:'DELETE',body:{confirmEmail:email}});
    if(active!==generation || !actor)return;
    if(result?.deletedUserId!==target.userId)throw new Error('The service did not confirm account deletion.');
    busy=false;status('admin-message','Unused account deleted. Its sign-in sessions have been revoked.','success');await refreshView();
  }catch(error){
    if(active!==generation || !actor)return;
    if(error.status===401 || error.status===403){await failure(error,'admin-message');return;}
    status('admin-message',error.message,'error');
    if(!error.status || error.status<400 || error.status>=500){uncertain=true;$('admin-uncertain').hidden=false;}
  }finally{if(active===generation){busy=false;lockControls();}}
}
async function changeRole() {
  if(!selection || !actor || !ready || busy || uncertain)return;
  const target=selection, active=generation;selection=null;$('admin-role-dialog').close();busy=true;lockControls();status('admin-message','Saving role change…');
  try {
    const result=await api(`/api/admin/users/${target.userId}/role`,{method:'PATCH',body:{role:target.role}});
    if(active!==generation || !actor)return;
    if(!result?.user)throw new Error('The service did not confirm the new user role.');
    if(target.userId===actor.userId && result.user.role!=='ADMIN'){
      clearAdministration();await refreshIdentity();deny('Your role changed. Administration is no longer available; use the features allowed by your new role.');return;
    }
    busy=false;status('admin-message',`Role updated to ${roleLabel(result.user.role)}.`,'success');await refreshView();
  }catch(error){
    if(active!==generation || !actor)return;
    if(error.status===401 || error.status===403){await failure(error,'admin-message');return;}
    status('admin-message',error.message,'error');
    if(!error.status || error.status<400 || error.status>=500){uncertain=true;$('admin-uncertain').hidden=false;}
    else if($('admin-role-'+target.userId)) $('admin-role-'+target.userId).value=target.oldRole;
  }finally{if(active===generation){busy=false;lockControls();}}
}
function bindEvents() {
  $('admin-refresh').addEventListener('click',()=>refreshView(true));$('admin-review-roles').addEventListener('click',()=>refreshView(true));
  $('admin-role-confirm-form').addEventListener('submit',event=>{event.preventDefault();changeRole();});
  $('admin-delete-form').addEventListener('submit',event=>{event.preventDefault();deleteAccount();});
  $('admin-delete-email').addEventListener('input',lockControls);
  $('admin-delete-dialog').addEventListener('close',()=>{deletionSelection=null;$('admin-delete-email').value='';$('admin-delete-description').textContent='';lockControls();});
  $('admin-import-filter')?.addEventListener('submit',event=>{event.preventDefault();filters=new URLSearchParams();for(const [name,id]of[['dataset','admin-import-dataset'],['status','admin-import-state']])if($(id).value)filters.set(name,$(id).value);refreshView(false,1);});
  $('admin-import-clear')?.addEventListener('click',()=>{$('admin-import-filter').reset();filters=new URLSearchParams();refreshView(false,1);});
  document.addEventListener('sessionexpired',()=>{if($('admin-page'))deny('Your sign-in expired. Sign in again to open administration.',true);});
}
export async function initAdministration(auth, refreshAccount) {
  if(!bound){bindEvents();bound=true;}
  refreshIdentity=async()=>{await refreshAccount();if(actor&&auth.user?.role==='ADMIN')actor=auth.user;else if(actor)actor={...actor,role:auth.user?.role??null};return auth.user;};
  clearAdministration();
  if(!auth.user){deny(auth.error||'Use an administrator application account to continue.',true);return;}
  if(auth.user.role!=='ADMIN'){deny('Your account does not have administrator access. Research and your personal workflows remain available.');return;}
  actor=auth.user;$('admin-gate').hidden=true;$('admin-workspace').hidden=false;$('admin-refresh').hidden=false;
  $('admin-page-title').textContent=view()==='overview'?'Know your data.':view()==='users'?'User roles':'Import history';
  $('admin-page-subtitle').textContent=view()==='overview'?'Current records, source archives and the import trail.':view()==='users'?'Assign the access each teammate needs.':'Review what was loaded, when, and with which outcome.';
  const query=new URLSearchParams(location.search);
  if(view()==='users'){$('admin-current-user').textContent=`Your account #${actor.userId} · Admin`;userPage=query.get('page')||1;}
  if(view()==='imports'){filters=new URLSearchParams();for(const[name,id]of[['dataset','admin-import-dataset'],['status','admin-import-state']]){if(query.has(name))filters.set(name,query.get(name));$(id).value=query.get(name)||'';}importPage=query.get('page')||1;}
  await refreshView();
}
