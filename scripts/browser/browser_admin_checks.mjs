/* Admin-only read views and role changes. Mutations target synthetic users only. */
export async function adminChecks({page,evaluate,goto,wait,click,fill,submit,screenshot,check,login,signedOut,fixtures,emails}) {
  const json=expression=>evaluate(`(async()=>{const m=await import('/static/api.js');return ${expression};})()`);
  const usersReady=()=>wait(`document.querySelector('#admin-users-status')?.textContent.endsWith('application accounts.') && !document.querySelector('#admin-users')?.querySelector('button:disabled')`,'admin user list');
  const importsReady=()=>wait(`document.querySelector('#admin-imports')?.getAttribute('aria-busy')==='false'`,'admin import list');
  const summaryReady=()=>wait(`document.querySelectorAll('.admin-dataset-card').length===4`,'dataset summary');
  async function roleForm(id,role){await fill('admin-role-'+id,role);await submit(`[data-user-id="${id}"] form`);await wait(`document.querySelector('#admin-role-dialog').open`,'role confirmation');}
  async function confirmRole(){await submit('#admin-role-confirm-form');await wait(`document.querySelector('#admin-role-dialog').open===false`,'role dialog close');}
  await page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await goto('/admin');
  check(await evaluate(`document.querySelector('#admin-workspace').hidden && document.querySelector('#admin-gate').textContent.includes('Sign in')`),'Signed-out admin pages expose no dataset inventory or account data');
  for(const index of [0,2]){
    await goto('/login?next=%2Fadmin%2Fusers');await login(index);await wait(`document.body.dataset.page==='admin' && document.body.dataset.ready==='true'`,'non-admin gate');
    check(await evaluate(`document.querySelector('#admin-workspace').hidden && document.querySelector('[data-admin-nav]').hidden`) && (await json(`m.api('/api/admin/datasets').catch(e=>e.status)`))===403,`${index===0?'Normal users':'Analysts'} cannot read the admin UI or monitoring API`);
    await signedOut();
  }
  await goto('/login?next=%2Fadmin');await login(4);await wait(`location.pathname==='/admin' && document.body.dataset.ready==='true'`,'admin sign-in return');await summaryReady();
  const summary=await json(`m.api('/api/admin/datasets')`);
  check(summary.schemaVersion===4 && summary.items.find(x=>x.key==='complaints').recordCount===428837 && await evaluate(`!document.querySelector('[data-admin-nav]').hidden`),'Admin sign-in opens current dataset counts through the restricted monitoring APIs');
  check(await evaluate(`document.querySelector('[data-dataset="recalls"] .dataset-count').textContent==='13,600' && document.querySelector('[data-dataset="complaints"]').textContent.includes('merged complaint documents') && document.querySelector('[data-dataset="recalls"]').textContent.includes('219,728 imported source rows')`),'Dataset cards distinguish recall campaigns, source rows and merged complaint documents');
  await click('[data-dataset="complaints"] .dataset-archives summary');
  check(await evaluate(`document.querySelectorAll('[data-dataset="complaints"] .dataset-archives li').length===2`),'The complaint inventory lists both imported source archives');await screenshot('admin-datasets.png');
  await page.send('Network.setBlockedURLs',{urls:['*/api/admin/datasets']});await click('#admin-refresh');await wait(`document.querySelector('#admin-datasets-status').classList.contains('error')`,'dataset read failure');
  check(await evaluate(`document.querySelectorAll('.admin-dataset-card').length===0 && !document.querySelector('#admin-refresh').disabled`),'A dataset request failure clears old counts and leaves a refresh action');
  await page.send('Network.setBlockedURLs',{urls:[]});await click('#admin-refresh');await summaryReady();check(true,'Dataset counts reload after the connection returns');
  await click('[data-dataset="complaints"] .text-link');await wait(`location.pathname==='/admin/imports' && document.body.dataset.ready==='true'`,'dataset to audit link');await importsReady();
  check(await evaluate(`document.querySelector('#admin-import-dataset').value==='complaints' && [...document.querySelectorAll('.admin-import-card h3')].every(n=>n.textContent.includes('complaints'))`),'A dataset card opens import history scoped to that dataset');
  await click('#admin-import-clear');await importsReady();
  const allRuns=await json(`m.api('/api/admin/import-runs?pageSize=100')`);
  check(await evaluate(`document.querySelector('#admin-imports-status').textContent===${JSON.stringify(allRuns.pagination.total+' import attempts found.')}`),'Import history displays real recorded attempts without adding a new import');
  if(allRuns.pagination.total>10){await click('#admin-imports-pagination button:last-child');await wait(`document.querySelector('#admin-imports-pagination').textContent.includes('Page 2')`,'audit pagination');check(true,'Import attempt pagination reads the next stored page');}
  await fill('admin-import-state','FAILED');await submit('#admin-import-filter');await importsReady();
  const failed=await json(`m.api('/api/admin/import-runs?status=FAILED&pageSize=100')`);
  check(await evaluate(`document.querySelector('#admin-imports-status').textContent===${JSON.stringify(failed.pagination.total+' import attempts found.')} && [...document.querySelectorAll('.admin-import-card .case-badge')].every(n=>n.textContent==='FAILED')`),'The outcome filter shows only recorded failed attempts and their bounded failure categories');
  await goto('/admin/imports?dataset=complaints&status=COMPLETED');await importsReady();
  check(await evaluate(`document.querySelector('#admin-import-dataset').value==='complaints' && document.querySelector('#admin-import-state').value==='COMPLETED' && document.querySelector('.import-metrics').textContent.includes('Updated entities')`),'A shared import URL restores filters and labels row/entity counters separately');
  await click('.operation-reference summary');check(await evaluate(`document.querySelector('.operation-reference p').textContent.length===129`),'Complaint import provenance preserves the pair of SHA-256 source archive fingerprints');await screenshot('admin-imports.png');
  await goto('/admin/imports?status=RUNNING');await importsReady();const running=await json(`m.api('/api/admin/import-runs?status=RUNNING')`);
  check(await evaluate(`document.querySelector('#admin-imports-status').textContent===${JSON.stringify(running.pagination.total+' import attempts found.')}`),'A running-only filter reports the stored result, including an empty state when appropriate');
  await goto('/admin/imports?dataset=invalid');await importsReady();check(await evaluate(`document.querySelector('#admin-imports-status').classList.contains('error') && !document.querySelector('.admin-import-card')`),'An invalid pasted import filter receives a readable server validation error');
  await click('#admin-import-clear');await importsReady();check(await evaluate(`!document.querySelector('#admin-imports-status').classList.contains('error')`),'Clearing invalid import filters restores the audit list');
  check((await json(`m.api('/api/admin/import-runs',{method:'POST',body:{}}).catch(e=>e.status)`))===405,'Import monitoring has no write endpoint');

  const users=await json(`m.api('/api/admin/users?pageSize=100')`),target=users.items.find(u=>u.email===emails[0]);
  if(!target)throw new Error('Owned role fixture not found');
  const ownerPage=Math.floor(users.items.findIndex(u=>u.userId===target.userId)/10)+1,adminPage=Math.floor(users.items.findIndex(u=>u.userId===fixtures.adminId)/10)+1;
  await goto('/admin/users?page='+ownerPage);await usersReady();
  check(await evaluate(`document.querySelector('#admin-users-pagination').textContent.includes('Page ${ownerPage}')`),'User roles paginate across actual accounts');
  check(users.items.every(u=>Object.keys(u).sort().join(',')==='createdAt,email,role,userId'),'Admin user responses omit password hashes and session material');
  await roleForm(target.userId,'ANALYST');await click('[data-close-dialog="admin-role-dialog"]');
  check((await json(`m.api('/api/admin/users?pageSize=100')`)).items.find(u=>u.userId===target.userId).role==='NORMAL_USER','Cancelling a role confirmation leaves the account role unchanged');
  await roleForm(target.userId,'ANALYST');await confirmRole();await wait(`document.querySelector('#admin-message').textContent==='Role updated to Analyst.'`,'role applied');await usersReady();
  check((await json(`m.api('/api/admin/users?pageSize=100')`)).items.find(u=>u.userId===target.userId).role==='ANALYST','Confirmed role changes update the intended synthetic account through the real admin API');
  await evaluate(`(()=>{const native=window.fetch.bind(window);let lost=false;window.adminRolePatches=0;window.fetch=async(input,options)=>{const selected=String(input)==='/api/admin/users/${target.userId}/role'&&options?.method==='PATCH';if(selected)window.adminRolePatches++;const response=await native(input,options);if(selected&&!lost){lost=true;throw new TypeError('Injected lost role response');}return response;};})()`);
  await roleForm(target.userId,'ADMIN');await confirmRole();await wait(`!document.querySelector('#admin-uncertain').hidden`,'uncertain role change');
  check(await evaluate(`document.querySelector('#admin-users button').disabled && window.adminRolePatches===1`),'A lost role-change response blocks further edits and offers a read-before-resubmit action');
  await click('#admin-review-roles');await usersReady();
  check(await evaluate(`document.querySelector('#admin-role-${target.userId}').value==='ADMIN' && document.querySelector('#admin-uncertain').hidden && window.adminRolePatches===1`),'Reviewing an uncertain role change reads the committed role without automatically repeating its PATCH');
  // Last-admin SQL is separately exercised in an isolated temporary table by the
  // Python verifier. This client-injected 409 checks the UI without demoting real admins.
  await goto('/admin/users?page='+adminPage);await usersReady();
  await evaluate(`(()=>{const native=window.fetch.bind(window);let rejected=false;window.fetch=async(input,options)=>{if(!rejected&&String(input)==='/api/admin/users/${fixtures.adminId}/role'&&options?.method==='PATCH'){rejected=true;return new Response(JSON.stringify({error:{message:'At least one administrator must remain'}}),{status:409,headers:{'Content-Type':'application/json'}});}return native(input,options);};})()`);
  await roleForm(fixtures.adminId,'NORMAL_USER');await confirmRole();await wait(`document.querySelector('#admin-message').textContent.includes('At least one administrator')`,'last-admin rejection');
  check(await evaluate(`document.querySelector('#admin-role-${fixtures.adminId}').value==='ADMIN'`) && (await json(`m.api('/api/auth/me')`)).user.role==='ADMIN','A last-admin rejection keeps admin access and restores the displayed role selection');
  await goto('/admin/users?page='+Math.ceil(users.pagination.total/10));await usersReady();
  check(await evaluate(`[...document.querySelectorAll('.admin-user-card h3')].every(n=>n.textContent.startsWith('frontend-verification-'))`),'Role screenshots contain synthetic account rows only');await screenshot('admin-users.png');
  await page.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await goto('/admin');await summaryReady();
  check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),'Admin inventory fits a 390px viewport');await screenshot('admin-mobile.png');
  await goto('/admin/users?page='+ownerPage);await usersReady();check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),'User role controls fit a 390px viewport');
  await goto('/admin/imports');await importsReady();check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),'Import filters and counter cards fit a 390px viewport');
  await page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await goto('/admin/users?page='+ownerPage);await usersReady();const history=await page.send('Page.getNavigationHistory'),prior=[...history.entries].reverse().find(e=>new URL(e.url).pathname==='/admin/users');await signedOut();
  if(prior){await page.send('Page.navigateToHistoryEntry',{entryId:prior.id});await wait(`document.body.dataset.page==='admin' && document.body.dataset.ready==='true' && !document.querySelector('#log-out')`,'admin history after logout');check(await evaluate(`document.querySelector('#admin-workspace').hidden && document.querySelectorAll('.admin-user-card,.admin-import-card,.admin-dataset-card').length===0`),'History after logout clears account rows and private administration data');}
  await goto('/login?next=%2Fadmin');await login(4);await wait(`document.body.dataset.page==='admin' && document.body.dataset.ready==='true'`,'admin for expiry');await summaryReady();
  await json(`m.api('/api/auth/logout',{method:'POST',body:{}})`);await click('#admin-refresh');await wait(`!document.querySelector('#admin-gate').hidden && document.querySelector('#admin-gate').textContent.includes('Sign in')`,'expired admin session');
  check(await evaluate(`document.querySelector('#admin-workspace').hidden && !document.querySelector('.admin-dataset-card') && document.querySelector('[data-admin-nav]').hidden`),'Session expiry clears admin data and navigation before further reads');
  await goto('/login?next=%2Fadmin%2Fusers');await login(0);await wait(`document.body.dataset.page==='admin' && document.body.dataset.ready==='true'`,'promoted fixture login');await usersReady();
  await goto('/admin/users?page='+ownerPage);await usersReady();await roleForm(target.userId,'ANALYST');await confirmRole();await wait(`!document.querySelector('#admin-gate').hidden && document.querySelector('#admin-gate').textContent.includes('Your role changed')`,'self-demotion access cleanup');
  check(await evaluate(`document.querySelector('#admin-workspace').hidden && document.querySelectorAll('.admin-user-card').length===0 && document.querySelector('[data-admin-nav]').hidden`) && (await json(`m.api('/api/admin/datasets').catch(e=>e.status)`))===403,'Successful self-demotion clears private admin UI and the next API request is forbidden');
  await signedOut();
}
