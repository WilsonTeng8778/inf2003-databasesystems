/* Real owner-scoped fleet and work-order browser journeys; fixtures belong to temporary accounts. */
export async function fleetChecks({page, evaluate, goto, wait, click, fill, submit, screenshot, check, login, signedOut}) {
  const json = expression => evaluate(`(async()=>{const m=await import('/static/api.js');return ${expression};})()`);
  const fleetReady = () => wait(`document.querySelector('#fleet-rename-submit') && !document.querySelector('#fleet-rename-submit').disabled`, 'fleet detail');
  const listReady = () => wait(`document.querySelector('#fleet-list-status')?.textContent.endsWith('fleets found.') && !document.querySelector('#fleet-create-submit').disabled`, 'fleet list');
  const orderReady = () => wait(`document.querySelector('#order-edit-submit') && !document.querySelector('#order-edit-submit').disabled`, 'work-order detail');
  async function createFleet(name) {
    await goto('/fleets'); await listReady(); await fill('fleet-create-name',name); await submit('#fleet-create-form');
    await wait(`document.querySelector('#fleet-page')?.dataset.view==='detail' && document.body.dataset.ready==='true'`, 'new fleet navigation'); await fleetReady();
    return Number((await evaluate('location.pathname')).split('/').pop());
  }
  async function addVehicle(label) {
    await evaluate(`document.querySelector('#fleet-add-disclosure').open=true`);
    await fill('fleet-search-make','HONDA'); await fill('fleet-search-model','CIVIC'); await fill('fleet-search-year','2022'); await submit('#fleet-vehicle-search');
    await wait(`document.querySelector('#fleet-search-results button')`, 'vehicle choices'); await click('#fleet-search-results button'); await fill('fleet-vehicle-label',label);
    await submit('#fleet-add-form'); await wait(`document.querySelector('#fleet-search-results').children.length===0 && !document.querySelector('#fleet-rename-submit').disabled`, 'fleet vehicle added');
  }
  async function filter(id,value,statusId,expected) { await fill(id,value); await evaluate(`document.getElementById(${JSON.stringify(id)}).dispatchEvent(new Event('change'))`); await wait(`document.getElementById(${JSON.stringify(statusId)}).textContent===${JSON.stringify(expected)} && !document.querySelector('#fleet-rename-submit').disabled`, 'applied fleet filter'); }
  async function confirm() { await wait(`document.querySelector('#fleet-confirm-dialog').open`, 'fleet removal confirmation'); await submit('#fleet-confirm-form'); }
  await page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await goto('/fleets');
  check(await evaluate(`document.querySelector('#fleet-workspace').hidden && document.querySelector('#fleet-gate').textContent.includes('Sign in')`), 'Signed-out fleet pages show a sign-in gate without private records');
  await click('#fleet-gate a'); await wait(`document.body.dataset.page==='login' && document.body.dataset.ready==='true'`, 'fleet sign-in link'); await login(0);
  await wait(`location.pathname==='/fleets' && document.body.dataset.ready==='true'`, 'return to fleets after login'); await listReady();
  check((await json(`m.api('/api/auth/me')`)).user.role==='NORMAL_USER' && await evaluate(`document.querySelector('#fleet-list-status').textContent==='0 fleets found.'`), 'An ordinary user can sign in directly to its own fleet workspace without analyst/admin access');
  const main = await createFleet('<img src=x onerror=alert(1)> Family fleet'); const mainPath = '/fleets/'+main;
  check(await evaluate(`document.querySelector('#fleet-page-title').textContent.startsWith('<img') && !document.querySelector('#fleet-page-title img') && document.querySelector('#fleet-vehicle-count').textContent==='0'`), 'Creating a fleet persists it and renders name markup literally');
  await fill('fleet-name','Family cars'); await submit('#fleet-rename-form'); await wait(`document.querySelector('#fleet-page-title').textContent==='Family cars' && !document.querySelector('#fleet-rename-submit').disabled`, 'fleet rename');
  check((await json(`m.api('/api/fleets/${main}')`)).fleet.name==='Family cars', 'Fleet rename persists through the owner-scoped API');
  await goto('/fleets'); await listReady(); await fill('fleet-create-name','Family cars'); await submit('#fleet-create-form');
  await wait(`document.querySelector('#fleet-message').textContent.includes('already have a fleet') && !document.querySelector('#fleet-create-submit').disabled`, 'duplicate fleet');
  check((await json(`m.api('/api/fleets')`)).pagination.total===1, 'Duplicate fleet creation shows a readable error and retains one fleet');
  const second = await createFleet('Weekend cars'); await goto(mainPath); await fleetReady();
  await addVehicle('Car 1');
  check(await evaluate(`document.querySelector('#fleet-vehicle-count').textContent==='1' && document.querySelector('#fleet-matches-status').textContent==='4 vehicle–recall matches found.'`), 'Adding the 2022 Civic produces four native model-year recall matches');
  let vehicles = (await json(`m.api('/api/fleets/${main}/vehicles')`)).items; const car1 = vehicles[0].fleetVehicleId;
  await evaluate(`document.querySelector('#fleet-add-disclosure').open=true`); await submit('#fleet-vehicle-search'); await wait(`document.querySelector('#fleet-search-results button')`, 'duplicate label choice'); await click('#fleet-search-results button'); await fill('fleet-vehicle-label','Car 1'); await submit('#fleet-add-form');
  await wait(`document.querySelector('#fleet-message').textContent.includes('already has a vehicle') && !document.querySelector('#fleet-rename-submit').disabled`, 'duplicate vehicle label');
  check((await json(`m.api('/api/fleets/${main}/vehicles')`)).pagination.total===1, 'Duplicate labels within a fleet are rejected without adding another vehicle');
  await addVehicle('Car 2'); vehicles=(await json(`m.api('/api/fleets/${main}/vehicles')`)).items; const car2=vehicles.find(v=>v.label==='Car 2').fleetVehicleId;
  check(await evaluate(`document.querySelector('#fleet-vehicle-count').textContent==='2' && document.querySelector('#fleet-matches-status').textContent==='8 vehicle–recall matches found.'`), 'Two labelled Civics produce eight vehicle–recall pairs rather than eight distinct campaigns');
  await fill('fleet-label-'+car1,'<script>do not execute</script> Car 1'); await submit(`[data-vehicle-id="${car1}"] form`);
  await wait(`document.querySelector('[data-vehicle-id="${car1}"] h3')?.textContent.startsWith('<script>') && !document.querySelector('#fleet-rename-submit').disabled`, 'vehicle label rename');
  check(await evaluate(`!document.querySelector('#fleet-vehicles script')`), 'Vehicle label markup remains literal after a stored rename');
  await fill('fleet-label-'+car1,'Daily Civic'); await submit(`[data-vehicle-id="${car1}"] form`); await wait(`document.querySelector('[data-vehicle-id="${car1}"] h3')?.textContent==='Daily Civic' && !document.querySelector('#fleet-rename-submit').disabled`, 'friendly vehicle label');
  const match=(await json(`m.api('/api/fleets/${main}/recall-matches')`)).items.find(v=>v.fleetVehicleId===car1); const recall=match.recallId;
  await click(`#fleet-matches [data-vehicle-id="${car1}"][data-recall-id="${recall}"] button`); await wait(`document.querySelector('#fleet-order-dialog').open`, 'order create dialog');
  const notes='<img src=x onerror=alert(1)>\nAsk the dealer about applicability.'; await fill('fleet-order-notes',notes); await submit('#fleet-order-create-form');
  await wait(`document.querySelector('#fleet-page')?.dataset.view==='order' && document.body.dataset.ready==='true'`, 'new work-order navigation'); await orderReady();
  const order=Number((await evaluate('location.pathname')).split('/').pop()), orderPath='/work-orders/'+order;
  let item=(await json(`m.api('/api/work-orders/${order}')`)).workOrder;
  check(item.status==='OPEN' && item.fleetVehicleId===car1 && item.recallId===recall && item.notes===notes && item.completedAt===null, 'A work order is created for the selected matched recall and starts Open with its stored notes');
  check(await evaluate(`document.querySelector('#order-notes').value.startsWith('<img') && !document.querySelector('#fleet-workspace img')`), 'Work-order notes are displayed as text in the editor');
  for(const state of ['IN_PROGRESS','COMPLETED']) { await fill('order-status',state); await submit('#order-edit-form'); await wait(`!document.querySelector('#order-edit-submit').disabled && document.querySelector('#order-status').value==='${state}'`, 'work-order status'); }
  const completed=(await json(`m.api('/api/work-orders/${order}')`)).workOrder.completedAt; await submit('#order-edit-form'); await wait(`!document.querySelector('#order-edit-submit').disabled`, 'repeat completion');
  check(completed && (await json(`m.api('/api/work-orders/${order}')`)).workOrder.completedAt===completed, 'Completing records a timestamp and repeating Completed preserves it');
  await fill('order-status','OPEN'); await fill('order-notes',''); await submit('#order-edit-form'); await wait(`!document.querySelector('#order-edit-submit').disabled`, 'reopen order'); item=(await json(`m.api('/api/work-orders/${order}')`)).workOrder;
  check(item.status==='OPEN' && item.notes==='' && item.completedAt===null, 'Reopening clears the completion timestamp and blank notes clear stored text');
  await fill('order-status','CANCELLED'); await fill('order-notes','Owner cancelled follow-up.'); await submit('#order-edit-form'); await wait(`!document.querySelector('#order-edit-submit').disabled`, 'cancel tracking'); await goto(orderPath); await orderReady();
  check(await evaluate(`document.querySelector('#order-status').value==='CANCELLED' && document.querySelector('#order-notes').value==='Owner cancelled follow-up.'`), 'Status and notes persist through a full work-order reload'); await screenshot('work-order-desktop.png');
  await page.send('Network.setBlockedURLs',{urls:[`*/api/work-orders/${order}`]}); await click('#fleet-refresh'); await wait(`!document.querySelector('#fleet-gate').hidden`, 'failed order read');
  check(await evaluate(`document.querySelector('#fleet-workspace').hidden && document.querySelector('#order-edit-submit').disabled`), 'A failed work-order refresh hides its editor and disables mutations');
  await page.send('Network.setBlockedURLs',{urls:[]}); await click('#fleet-refresh'); await orderReady(); check(true,'Refreshing restores the work order after the connection returns');
  await page.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true}); await goto(orderPath); await orderReady();
  check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`), 'The work-order editor fits a 390px viewport'); await screenshot('work-order-mobile.png');
  await page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false}); await goto(mainPath); await fleetReady();
  await filter('fleet-tracked-filter','true','fleet-matches-status','1 vehicle–recall matches found.'); check(await evaluate(`document.querySelector('#fleet-matches').textContent.includes('CANCELLED') && !document.querySelector('#fleet-matches button')`), 'Cancelled work orders remain tracked and open through their existing order links');
  await filter('fleet-tracked-filter','false','fleet-matches-status','7 vehicle–recall matches found.'); check(true,'The untracked match filter excludes the existing vehicle–recall order');
  await filter('fleet-order-status-filter','CANCELLED','fleet-orders-status','1 work orders found.'); await filter('fleet-order-status-filter','OPEN','fleet-orders-status','0 work orders found.'); check(true,'Work-order status filters update the real owner-scoped order list');
  await click(`#fleet-vehicles [data-vehicle-id="${car1}"] .saved-card-actions a`); await wait(`document.body.dataset.ready==='true' && !document.querySelector('#fleet-rename-submit')?.disabled && !document.querySelector('#fleet-vehicle-scope').hidden`, 'selected fleet vehicle');
  check(await evaluate(`document.querySelector('#fleet-matches-status').textContent==='4 vehicle–recall matches found.' && document.querySelector('#fleet-scope-label').textContent.includes('Daily Civic')`), 'Selecting a fleet vehicle scopes matches and orders to its labelled entry');
  await goto(`/fleets/${second}?vehicle=${car1}`); check(await evaluate(`document.querySelector('#fleet-page-title').textContent==='Record not found' && document.querySelector('#fleet-workspace').hidden`), 'A vehicle from another owned fleet cannot be used as this fleet’s filter');
  await goto(mainPath); await fleetReady();
  const race=(await json(`m.api('/api/fleets/${main}/recall-matches')`)).items.find(v=>!v.workOrderId && v.fleetVehicleId===car2);
  await click(`#fleet-matches [data-vehicle-id="${car2}"][data-recall-id="${race.recallId}"] button`); await wait(`document.querySelector('#fleet-order-dialog').open`, 'duplicate-order race dialog');
  const raceOrder=(await json(`m.api('/api/work-orders',{method:'POST',body:{fleetVehicleId:${car2},recallId:${race.recallId}}})`)).workOrder.workOrderId; await submit('#fleet-order-create-form');
  await wait(`document.querySelector('#fleet-message').textContent.includes('already has a work order') && !document.querySelector('#fleet-rename-submit').disabled`, 'duplicate order race');
  check((await json(`m.api('/api/work-orders?fleetVehicleId=${car2}')`)).pagination.total===1 && await evaluate(`document.querySelector('#fleet-matches').textContent.includes('Open work order #${raceOrder}')`), 'A concurrent order creation shows the existing order instead of inserting a duplicate');
  await goto('/work-orders/'+raceOrder); await orderReady(); await click('#order-delete'); await wait(`document.querySelector('#fleet-confirm-dialog').open`, 'order removal cancellation'); await click('[data-close-dialog="fleet-confirm-dialog"]');
  check((await json(`m.api('/api/work-orders/${raceOrder}')`)).workOrder.workOrderId===raceOrder,'Cancelling work-order deletion retains the order');
  await click('#order-delete'); await confirm(); await wait(`document.querySelector('#fleet-page')?.dataset.view==='detail' && document.body.dataset.ready==='true'`, 'deleted order returns to fleet'); await fleetReady();
  check((await json(`m.api('/api/fleets/${main}/recall-matches')`)).items.find(v=>v.fleetVehicleId===car2&&v.recallId===race.recallId).workOrderId===null,'Deleting a work order makes the vehicle–recall pair untracked again');

  // Prepare enough real owned records to exercise all independent pagers and cascades.
  await json(`(async()=>{for(let n=0;n<9;n++)await m.api('/api/fleets/${main}/vehicles',{method:'POST',body:{modelYearId:17527,label:'Pagination car '+n}});const matches=await m.api('/api/fleets/${main}/recall-matches?pageSize=100');let existing=1;for(const row of matches.items){if(!row.workOrderId&&existing<11){await m.api('/api/work-orders',{method:'POST',body:{fleetVehicleId:row.fleetVehicleId,recallId:row.recallId}});existing++;}}for(let n=0;n<10;n++)await m.api('/api/fleets',{method:'POST',body:{name:'Fleet pagination fixture '+n}});return true;})()`);
  await goto('/fleets'); await listReady(); await screenshot('fleets-desktop.png'); await click('#fleet-list-pagination button:last-child'); await wait(`document.querySelector('#fleet-list-pagination').textContent.includes('Page 2')`, 'fleet list page two');
  check(await evaluate(`document.querySelectorAll('#fleet-list .fleet-card').length===2`),'The fleet list paginates actual owner records');
  await goto(mainPath); await fleetReady(); await screenshot('fleet-detail-desktop.png'); await click('#fleet-vehicles-pagination button:last-child'); await wait(`document.querySelector('#fleet-vehicles-pagination').textContent.includes('Page 2')`, 'vehicle page two');
  check(await evaluate(`document.querySelectorAll('.fleet-vehicle-card').length===1`),'Fleet vehicles paginate independently of recall matches and work orders');
  await click('#fleet-matches-pagination button:last-child'); await wait(`document.querySelector('#fleet-matches-pagination').textContent.includes('Page 2')`, 'recall matches page two'); check(true,'Recall matches paginate across multiple labelled vehicles');
  await click('#fleet-orders-pagination button:last-child'); await wait(`document.querySelector('#fleet-orders-pagination').textContent.includes('Page 2')`, 'orders page two'); check(await evaluate(`document.querySelectorAll('#fleet-orders .fleet-card').length===1`),'Work-order pagination keeps its own page and filter state');
  await page.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true}); await goto(mainPath); await fleetReady(); await evaluate(`document.querySelector('#fleet-add-disclosure').open=true`);
  check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),'Fleet summary, vehicle forms and recall/order cards fit a 390px viewport'); await screenshot('fleet-mobile.png');
  await page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await signedOut(); await goto('/login?next=%2Ffleets'); await login(1); await wait(`location.pathname==='/fleets' && document.body.dataset.ready==='true'`, 'second owner'); await listReady();
  check(await evaluate(`document.querySelector('#fleet-list-status').textContent==='0 fleets found.'`),'Another normal account sees its own empty fleet list');
  await goto(mainPath); check(await evaluate(`document.querySelector('#fleet-page-title').textContent==='Record not found' && document.querySelector('#fleet-workspace').hidden`),'A foreign fleet URL exposes the same not-found state as a missing fleet');
  await goto(orderPath); check(await evaluate(`document.querySelector('#fleet-page-title').textContent==='Record not found'`),'A foreign work-order URL does not expose order notes or vehicle details');
  await signedOut(); await goto('/login?next=%2Ffleets'); await login(4); await wait(`location.pathname==='/fleets' && document.body.dataset.ready==='true'`, 'admin own fleets'); await listReady();
  check(await evaluate(`document.querySelector('#fleet-list-status').textContent==='0 fleets found.'`),'An admin sees only its own fleets despite having analyst-case oversight');
  await goto(mainPath); check(await evaluate(`document.querySelector('#fleet-page-title').textContent==='Record not found'`),'Admin cannot inspect another owner’s fleet by its ID');
  check((await json(`m.api('/api/work-orders/${order}',{method:'PATCH',body:{notes:'Must be denied'}}).catch(e=>e.status)`))===404,'Admin cannot mutate another owner’s work order');
  await signedOut(); await goto('/login?next='+encodeURIComponent(mainPath)); await login(0); await wait(`location.pathname===${JSON.stringify(mainPath)} && document.body.dataset.ready==='true'`, 'owner returns'); await fleetReady();
  let ownedOrders=(await json(`m.api('/api/work-orders?fleetVehicleId=${car2}&pageSize=100')`)).items; const removedIds=ownedOrders.map(v=>v.workOrderId);
  await click(`#fleet-vehicles [data-vehicle-id="${car2}"] .remove-link`); await wait(`document.querySelector('#fleet-confirm-dialog').open`, 'vehicle removal cancel'); await click('[data-close-dialog="fleet-confirm-dialog"]');
  check((await json(`m.api('/api/fleet-vehicles/${car2}')`)).fleetVehicle.fleetVehicleId===car2,'Cancelling fleet vehicle removal keeps its entry and dependent orders');
  await click(`#fleet-vehicles [data-vehicle-id="${car2}"] .remove-link`); await confirm(); await wait(`document.querySelector('#fleet-vehicle-count').textContent==='10' && !document.querySelector('#fleet-rename-submit').disabled`, 'vehicle cascade');
  check((await json(`m.api('/api/work-orders?fleetVehicleId=${car2}')`)).pagination.total===0 && (await json(`m.api('/api/work-orders/${order}')`)).workOrder.workOrderId===order && removedIds.length>0,'Removing one fleet vehicle deletes its orders and retains another vehicle’s order');
  const navigation=await page.send('Page.getNavigationHistory');const prior=[...navigation.entries].reverse().find(e=>new URL(e.url).pathname===mainPath); await signedOut();
  if(prior){await page.send('Page.navigateToHistoryEntry',{entryId:prior.id});await wait(`document.body.dataset.page==='fleets' && document.body.dataset.ready==='true' && !document.querySelector('#log-out')`, 'fleet history after logout');check(await evaluate(`document.querySelector('#fleet-workspace').hidden && document.querySelectorAll('.fleet-vehicle-card,.fleet-card').length===0 && !document.querySelector('#fleet-page-title').textContent.includes('Family')`),'Browser history after logout clears private fleet names, vehicles and order cards');}
  await goto('/login?next=%2Ffleets');await login(0);await wait(`location.pathname==='/fleets' && document.body.dataset.ready==='true'`, 'owner re-login');await listReady();
  await evaluate(`(()=>{const native=window.fetch.bind(window);window.fleetCreatePosts=0;let lost=false;window.fetch=async(input,options)=>{const selected=String(input)==='/api/fleets'&&options?.method==='POST';if(selected)window.fleetCreatePosts++;const result=await native(input,options);if(selected&&!lost){lost=true;throw new TypeError('Injected lost fleet response after commit');}return result;};})()`);
  await fill('fleet-create-name','Lost response fleet');await submit('#fleet-create-form');await wait(`!document.querySelector('#fleet-uncertain').hidden`, 'uncertain fleet create');
  check(await evaluate(`document.querySelector('#fleet-create-submit').disabled && window.fleetCreatePosts===1`),'A lost fleet-create response blocks another write and requests a read before resubmission');
  await click('#fleet-review-records');await listReady();check(await evaluate(`document.querySelector('#fleet-list').textContent.includes('Lost response fleet') && window.fleetCreatePosts===1 && document.querySelector('#fleet-uncertain').hidden`),'Refreshing an uncertain create reveals the committed fleet without automatically repeating its POST');
  await evaluate(`(()=>{const native=window.fetch.bind(window);let broken=false;window.fetch=async(input,options)=>{const response=await native(input,options);if(!broken&&String(input)==='/api/fleets'&&options?.method==='POST'){broken=true;return new Response('incomplete JSON',{status:201,headers:{'Content-Type':'application/json'}});}return response;};})()`);
  await fill('fleet-create-name','Unreadable response fleet');await submit('#fleet-create-form');await wait(`!document.querySelector('#fleet-uncertain').hidden`, 'unreadable successful fleet response');
  check(await evaluate(`document.querySelector('#fleet-create-submit').disabled`),'A successful HTTP write with unreadable JSON is treated as uncertain instead of enabling another create');
  await click('#fleet-review-records');await listReady();check((await json(`m.api('/api/fleets?pageSize=100')`)).items.filter(f=>f.name==='Unreadable response fleet').length===1,'Reading after an unreadable write response finds the single committed fleet');
  await goto(mainPath);await fleetReady();await click('#fleet-delete');await wait(`document.querySelector('#fleet-confirm-dialog').open`, 'fleet deletion cancel');await click('[data-close-dialog="fleet-confirm-dialog"]');
  check((await json(`m.api('/api/fleets/${main}')`)).fleet.fleetId===main,'Cancelling fleet deletion preserves the fleet');
  await click('#fleet-delete');await confirm();await wait(`location.pathname==='/fleets' && document.body.dataset.ready==='true'`, 'fleet deletion returns to list');await listReady();
  check((await json(`m.api('/api/fleets/${main}').catch(e=>e.status)`))===404 && (await json(`m.api('/api/work-orders/${order}').catch(e=>e.status)`))===404 && (await json(`m.api('/api/fleet-vehicles/${car1}').catch(e=>e.status)`))===404 && (await json(`m.api('/api/fleets/${second}')`)).fleet.fleetId===second,'Deleting a fleet cascades its vehicles/orders and preserves another owned fleet');
  await json(`m.api('/api/auth/logout',{method:'POST',body:{}})`);await click('#fleet-refresh');await wait(`!document.querySelector('#fleet-gate').hidden && document.querySelector('#fleet-gate').textContent.includes('Sign in')`, 'fleet session expiry');
  check(await evaluate(`document.querySelector('#fleet-workspace').hidden && document.querySelectorAll('.fleet-card').length===0 && !document.querySelector('#log-out')`),'Session expiry clears private fleet records when the next request is denied');
}
