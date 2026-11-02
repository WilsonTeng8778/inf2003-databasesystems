/* Real Chromium checks via its local DevTools protocol. Fixture credentials arrive on stdin only. */
import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {researchChecks} from './browser_research_checks.mjs';
import {caseChecks} from './browser_case_checks.mjs';
import {fleetChecks} from './browser_fleet_checks.mjs';
import {adminChecks} from './browser_admin_checks.mjs';
import {analyticsChecks} from './browser_analytics_checks.mjs';
import {accountChecks} from './browser_account_checks.mjs';

let input = '';
for await (const part of process.stdin) input += part;
const config = JSON.parse(input); input = '';
const origin = new URL(config.baseUrl);
if (origin.hostname !== '127.0.0.1' || origin.protocol !== 'http:' ||
    !config.emails.every(email => email.startsWith('frontend-verification-') && email.endsWith('@example.invalid'))) {
  throw new Error('Browser verification requires a loopback server and synthetic fixture accounts.');
}
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const checks = [], exceptions = [], loaded = new Set();
const check = (condition, description) => { if (!condition) throw new Error(description); checks.push(description); };

class CDP {
  constructor(url) {
    this.ws = new WebSocket(url); this.next = 0; this.pending = new Map(); this.handlers = [];
    this.open = new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, {once: true});
      this.ws.addEventListener('error', () => reject(new Error('Could not connect to the owned browser.')), {once: true});
    });
    this.ws.addEventListener('message', event => {
      const value = JSON.parse(event.data);
      if (value.id) {
        const pending = this.pending.get(value.id);
        if (!pending) return;
        clearTimeout(pending.timer); this.pending.delete(value.id);
        if (value.error) pending.reject(new Error('Browser command failed: ' + pending.method));
        else pending.resolve(value.result);
      } else for (const handler of this.handlers) handler(value);
    });
    this.ws.addEventListener('close', () => {
      for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(new Error('Owned browser connection closed.')); }
      this.pending.clear();
    });
  }
  async send(method, params = {}) {
    await this.open;
    return new Promise((resolve, reject) => {
      const id = ++this.next;
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error('Browser command timed out: ' + method)); }, 20000);
      this.pending.set(id, {resolve, reject, timer, method});
      this.ws.send(JSON.stringify({id, method, params}));
    });
  }
  close() { this.ws.close(); }
}

await mkdir(config.profilePath, {recursive: true});
await mkdir(config.screenshotPath, {recursive: true});
const child = spawn(config.browserPath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--disable-sync', '--disable-background-networking', '--disable-component-update',
  '--disable-features=Translate,OptimizationHints,PasswordManagerOnboarding', '--remote-debugging-port=0',
  '--remote-debugging-address=127.0.0.1', '--user-data-dir=' + config.profilePath, 'about:blank'],
  {windowsHide: true, stdio: 'ignore'});
let launchError = false;
child.on('error', () => { launchError = true; });
let browser, page, version;
try {
  const activePath = join(config.profilePath, 'DevToolsActivePort');
  const deadline = Date.now() + 15000;
  while (!existsSync(activePath) && Date.now() < deadline && !launchError && child.exitCode === null) await delay(50);
  if (!existsSync(activePath)) throw new Error('The installed browser could not start its local verification session.');
  const [port, browserPath] = (await readFile(activePath, 'utf8')).trim().split(/\r?\n/);
  browser = new CDP(`ws://127.0.0.1:${port}${browserPath}`);
  version = await browser.send('Browser.getVersion');
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  page = new CDP(targets.find(item => item.type === 'page').webSocketDebuggerUrl);
  page.handlers.push(event => {
    if (event.method === 'Page.lifecycleEvent' && event.params.name === 'DOMContentLoaded') loaded.add(event.params.loaderId);
    if (event.method === 'Runtime.exceptionThrown') exceptions.push(event.params.exceptionDetails.text);
  });
  await page.send('Page.enable'); await page.send('Runtime.enable'); await page.send('Network.enable');
  await page.send('Page.setLifecycleEventsEnabled', {enabled: true});
  await page.send('Network.setCacheDisabled', {cacheDisabled: true});
  await page.send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1050, deviceScaleFactor: 1, mobile: false});

  async function evaluate(expression) {
    const value = await page.send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (value.exceptionDetails) throw new Error('A browser verification expression failed.');
    return value.result.value;
  }
  async function wait(expression, label) {
    const limit = Date.now() + 15000;
    while (Date.now() < limit) { if (await evaluate(expression)) return; await delay(50); }
    throw new Error('Timed out: ' + label);
  }
  async function goto(path) {
    const url = new URL(path, config.baseUrl).href;
    const result = await page.send('Page.navigate', {url});
    if (result.errorText) throw new Error('Navigation to the local application failed.');
    const limit = Date.now() + 15000;
    while (result.loaderId && !loaded.has(result.loaderId) && Date.now() < limit) await delay(25);
    // Search normalizes its shareable query string with history.replaceState.
    const target = new URL(url);
    await wait(`location.origin === ${JSON.stringify(target.origin)} && location.pathname === ${JSON.stringify(target.pathname)} && document.body?.dataset.ready === 'true'`, 'page initialization');
  }
  async function click(selector) {
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  }
  async function fill(id, value) {
    await evaluate(`(() => {const input=document.getElementById(${JSON.stringify(id)}); input.value=${JSON.stringify(value)}; input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  }
  async function submit(selector) { await evaluate(`document.querySelector(${JSON.stringify(selector)}).requestSubmit()`); }
  async function screenshot(name, selector) {
    await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
    const metrics = await page.send('Page.getLayoutMetrics');
    const content = metrics.cssContentSize || metrics.contentSize;
    const region = selector ? await evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,width:r.width,height:Math.min(r.height,2400)};})()`) : {x:0,y:0,width:content.width,height:Math.min(content.height,2400)};
    const shot = await page.send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true,
      clip: {...region,scale:1}});
    await writeFile(join(config.screenshotPath, name), Buffer.from(shot.data, 'base64'));
  }
  async function register(index) {
    await fill('email', config.emails[index]); await fill('password', config.password); await fill('confirm-password', config.password);
    await submit('#auth-form');
  }
  async function login(index) {
    await fill('email', config.emails[index]); await fill('password', config.password); await submit('#auth-form');
  }
  async function savedReady() { await wait(`(() => {const text=document.querySelector('#saved-status')?.textContent||'';return text.endsWith(' saved vehicle.')||text.endsWith(' saved vehicles.');})()`, 'saved-vehicle list'); }
  async function signedOut() {
    await click('#log-out'); await wait(`location.pathname==='/vehicles' && document.body.dataset.ready==='true' && !document.querySelector('#log-out')`, 'sign out');
  }

  await goto('/vehicles');
  check(await evaluate(`document.title.includes('RecallScope') && document.querySelector('#search-form') !== null`), 'Search page and shared navigation render in a real browser');
  await screenshot('search-desktop.png');
  await evaluate(`document.querySelector('.skip-link').focus()`);
  await page.send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13});
  await page.send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13});
  check(await evaluate(`document.activeElement.id==='main'`), 'Keyboard skip link focuses the main content');
  await click('#example-search');
  await wait(`document.querySelectorAll('.vehicle-card').length===1 && !document.querySelector('#search-submit').disabled`, 'Civic search');
  check(await evaluate(`document.querySelector('.vehicle-card').textContent.includes('CIVIC')`), 'Example search returns the real Civic catalogue identity');
  await click('.vehicle-card a');
  await wait(`document.body.dataset.page==='profile' && document.querySelector('#record-list .record-item')`, 'profile records');
  const profilePath = await evaluate('location.pathname+location.search');
  check(await evaluate(`document.querySelector('#recall-count').textContent==='4' && document.querySelector('#complaint-count').textContent==='885' && document.querySelector('#investigation-count').textContent==='2'`), 'Vehicle profile shows the verified 4 recall, 885 complaint and 2 investigation counts');
  await screenshot('profile-desktop.png');
  await evaluate(`document.querySelector('#record-list details').open=true`);
  await wait(`document.querySelector('#record-list .record-full h4')?.textContent==='Summary'`, 'recall detail');
  check(await evaluate(`document.querySelector('#record-list .record-full').textContent.includes('Remedy')`), 'Full official recall detail loads inside the profile');
  await click('[data-record-type="complaints"]');
  await wait(`document.querySelector('#record-status').textContent.includes('885 complaints') && document.querySelectorAll('#record-list .record-item').length===5`, 'complaint records');
  const firstComplaint = await evaluate(`document.querySelector('#record-list .record-meta').textContent`);
  await evaluate(`document.querySelector('#record-list details').open=true`);
  await wait(`document.querySelector('#record-list .record-full h4')?.textContent==='Consumer narrative'`, 'complaint detail');
  check(true, 'Complaint narrative and incident details render without raw JSON');
  await click('#record-pagination button:last-child');
  await wait(`document.querySelector('#record-pagination').textContent.includes('Page 2')`, 'complaint pagination');
  check((await evaluate(`document.querySelector('#record-list .record-meta').textContent`)) !== firstComplaint, 'Complaint pagination changes the displayed records');
  await click('[data-record-type="investigations"]');
  await wait(`document.querySelector('#record-status').textContent.includes('2 official investigations')`, 'investigation records');
  await evaluate(`document.querySelector('#record-list details').open=true`);
  await wait(`document.querySelector('#record-list .record-full h4')?.textContent==='Official summary'`, 'investigation detail');
  check(true, 'Official investigation detail and snapshot-status labels load in the profile');
  await click('#save-vehicle');
  await wait(`document.body.dataset.page==='login' && document.body.dataset.ready==='true'`, 'sign-in redirect');
  check(await evaluate(`new URLSearchParams(location.search).get('next').startsWith('/vehicles/profile?')`), 'Anonymous save preserves the selected vehicle through sign-in');
  await click('#auth-alternate-link');
  await wait(`document.body.dataset.page==='register' && document.body.dataset.ready==='true'`, 'registration page');
  await fill('email', config.emails[0]); await fill('password', config.password); await fill('confirm-password', 'Different-password-2026');
  await submit('#auth-form');
  check(await evaluate(`document.querySelector('#confirm-password').validity.customError && document.body.dataset.page==='register'`), 'Mismatched registration passwords are rejected before submission');
  await register(0);
  await wait(`document.body.dataset.page==='profile' && document.querySelector('#log-out') && !document.querySelector('#save-vehicle').disabled`, 'registration returns to profile');
  check(true, 'Registration creates a normal account and returns to the selected vehicle using real session cookies');
  const maliciousNickname = '<img src=x onerror="window.__recallXss=true">';
  await click('#save-vehicle'); await wait(`document.querySelector('#save-dialog').open`, 'save dialog');
  await fill('save-nickname', maliciousNickname); await submit('#save-form');
  await wait(`document.querySelector('#save-vehicle').dataset.saved==='true' && !document.querySelector('#save-dialog').open`, 'save vehicle');
  check(true, 'Saving a vehicle succeeds with the real CSRF/session flow');
  await goto('/saved-vehicles'); await savedReady();
  check(await evaluate(`document.querySelectorAll('.saved-card').length===1 && document.querySelector('.saved-card h2').textContent===${JSON.stringify(maliciousNickname)} && document.querySelectorAll('.saved-card img').length===0 && window.__recallXss!==true`), 'Stored nickname markup is displayed as literal text without inserting an image or executing script');
  const savedId = await evaluate(`document.querySelector('.saved-card').dataset.savedVehicleId`);
  await evaluate(`document.querySelector('.nickname-form input').value='Daily Civic'`); await submit('.nickname-form');
  await wait(`document.querySelector('.saved-card h2').textContent==='Daily Civic' && document.querySelector('.nickname-form .status-line').textContent==='Nickname updated.'`, 'nickname update');
  await goto('/saved-vehicles'); await savedReady();
  check(await evaluate(`document.querySelector('.saved-card h2').textContent==='Daily Civic'`), 'Nickname edit persists across a full page reload');
  await click('.remove-link'); await wait(`document.querySelector('#remove-dialog').open`, 'remove dialog');
  await click('[data-close-dialog="remove-dialog"]');
  check(await evaluate(`!document.querySelector('#remove-dialog').open && document.querySelectorAll('.saved-card').length===1`), 'Cancelling removal keeps the saved record');
  check(await evaluate(`localStorage.length===0 && sessionStorage.length===0`), 'Credentials and tokens are not stored in browser web storage');
  const history = await page.send('Page.getNavigationHistory');
  const priorSaved = history.entries.filter(entry => entry.url.includes('/saved-vehicles')).at(-1);
  await signedOut(); await goto('/saved-vehicles');
  check(await evaluate(`document.querySelectorAll('.saved-card').length===0 && document.querySelector('#saved-content').textContent.includes('Sign in')`), 'Signed-out saved page exposes no personal records');
  if (priorSaved) {
    await page.send('Page.navigateToHistoryEntry', {entryId: priorSaved.id});
    await wait(`document.body.dataset.page==='saved' && !document.querySelector('#log-out') && document.querySelector('#saved-content').textContent.includes('Sign in')`, 'history after logout');
    check(await evaluate(`document.querySelectorAll('.saved-card').length===0`), 'Returning through browser history after logout does not reveal the old saved list');
  }
  await goto('/register?next=%2Fsaved-vehicles'); await register(1);
  await wait(`document.body.dataset.page==='saved' && document.querySelector('#log-out')`, 'second registration'); await savedReady();
  check(await evaluate(`document.querySelectorAll('.saved-card').length===0 && document.querySelector('#saved-status').textContent==='0 saved vehicles.'`), 'A second account sees its own empty saved list');
  check((await evaluate(`fetch('/api/saved-vehicles/${savedId}').then(response=>response.status)`)) === 404, 'Another account cannot read the first account’s saved record using its ID');
  await signedOut(); await goto('/login?next=https%3A%2F%2Fexample.invalid%2Fescape');
  await login(0); await wait(`location.pathname==='/saved-vehicles' && document.querySelector('#log-out')`, 'safe login redirect'); await savedReady();
  check(await evaluate(`document.querySelector('.saved-card h2').textContent==='Daily Civic'`), 'Owner login restores its saved record and rejects an external return URL');
  check(await evaluate(`import('/static/app.js').then(module => ['//example.invalid','javascript:alert(1)','/login','/\\\\example.invalid'].every(value=>module.safeNext(value)==='/saved-vehicles'))`), 'Return-path validation rejects external, script and authentication-loop destinations');
  await goto(profilePath);
  await click('#save-vehicle'); await wait(`document.querySelector('#save-dialog').open`, 'duplicate-save dialog');
  await submit('#save-form');
  await wait(`document.querySelector('#profile-status').textContent.includes('already in your personal list')`, 'duplicate save notice');
  check((await evaluate(`fetch('/api/saved-vehicles').then(response=>response.json()).then(result=>result.pagination.total)`)) === 1, 'Duplicate saving gives a clear existing-bookmark message and preserves one record');

  await page.send('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: true});
  await goto('/vehicles?year=2022&make=HONDA&model=CIVIC');
  await wait(`document.querySelector('.vehicle-card') && !document.querySelector('#search-submit').disabled`, 'mobile search');
  check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`), 'Search layout fits a 390px mobile viewport without horizontal overflow');
  await screenshot('search-mobile.png');
  await goto(profilePath);
  check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`), 'Vehicle profile fits the mobile viewport');
  await goto('/saved-vehicles'); await savedReady();
  check(await evaluate(`document.documentElement.scrollWidth<=innerWidth`), 'Saved-vehicle forms and actions fit the mobile viewport');
  await click('.remove-link'); await submit('#remove-form');
  await wait(`document.querySelector('#saved-status').textContent==='0 saved vehicles.' && !document.querySelector('#remove-dialog').open`, 'confirmed removal');
  check(true, 'Confirmed removal deletes the personal bookmark and shows the empty-list state');
  await signedOut();
  await goto('/login'); await fill('email', config.emails[0]); await fill('password', 'Incorrect-browser-password-2026'); await submit('#auth-form');
  await wait(`document.querySelector('#auth-status').classList.contains('error')`, 'invalid credentials notice');
  check(await evaluate(`document.querySelector('#auth-status').textContent.includes('Invalid email or password') && !document.querySelector('#auth-submit').disabled`), 'Incorrect credentials produce a readable error and allow retry');
  await goto('/vehicles');
  await page.send('Network.setBlockedURLs', {urls: ['*/api/vehicles/search*']});
  await click('#example-search'); await wait(`document.querySelector('#search-status').classList.contains('error')`, 'network error');
  check(await evaluate(`!document.querySelector('#search-submit').disabled && document.querySelector('#search-results-section').getAttribute('aria-busy')==='false'`), 'Search connection errors clear loading state and leave a usable retry');
  await page.send('Network.setBlockedURLs', {urls: []}); await submit('#search-form');
  await wait(`document.querySelector('.vehicle-card') && !document.querySelector('#search-status').classList.contains('error')`, 'search retry');
  check(true, 'Search succeeds after the connection is restored');
  await fill('make', 'NO_SUCH_MAKE'); await submit('#search-form');
  await wait(`document.querySelector('#search-results').textContent.includes('No matching vehicles')`, 'empty results');
  check(true, 'Unmatched filters show an empty result instead of stale vehicle cards');
  if (config.includeResearch) await researchChecks({page, evaluate, goto, wait, click, fill, submit, screenshot, check, login, signedOut});
  if (config.includeCases) await caseChecks({page, evaluate, goto, wait, click, fill, submit, screenshot, check, login, signedOut, fixtures: config.caseFixtures});
  if (config.includeFleets) await fleetChecks({page, evaluate, goto, wait, click, fill, submit, screenshot, check, login, signedOut});
  if (config.includeAdmin) await adminChecks({page, evaluate, goto, wait, click, fill, submit, screenshot, check, login, signedOut, fixtures: config.caseFixtures, emails: config.emails});
  if (config.includeAnalytics) await analyticsChecks({page,evaluate,goto,wait,click,fill,submit,screenshot,check});
  if (config.includeAccounts) await accountChecks({page,evaluate,goto,wait,click,fill,submit,screenshot,check,login,signedOut,fixtures:config.accountFixtures});
  check(exceptions.length === 0, 'No uncaught browser JavaScript exceptions occurred');
  process.stdout.write(JSON.stringify({checks, browser: version.product, screenshots: ['search-desktop.png','profile-desktop.png','search-mobile.png',
    ...(config.includeResearch ? ['complaints-desktop.png', 'recall-desktop.png', 'investigation-desktop.png', 'complaints-mobile.png', 'record-mobile.png'] : []),
    ...(config.includeCases ? ['cases-desktop.png', 'case-detail-desktop.png', 'case-pending.png', 'case-detail-mobile.png'] : []),
    ...(config.includeFleets ? ['fleets-desktop.png', 'fleet-detail-desktop.png', 'work-order-desktop.png', 'fleet-mobile.png', 'work-order-mobile.png'] : []),
    ...(config.includeAdmin ? ['admin-datasets.png','admin-users.png','admin-imports.png','admin-mobile.png'] : []),
    ...(config.includeAnalytics ? ['analytics-desktop.png','analytics-comparison.png','analytics-mobile.png'] : []),
    ...(config.includeAccounts ? ['account-delete-dialog.png','account-delete-mobile.png','account-delete-uncertain.png','account-delete-result.png'] : [])],
    uncaught_browser_exceptions: exceptions.length}) + '\n');
} catch (error) {
  // Keep fixture values out of diagnostics, including on a failed login assertion.
  let message = error.message || 'Browser verification failed.';
  message = message.split(config.password).join('[redacted]');
  let state = null;
  if (page) {
    try {
      const result = await page.send('Runtime.evaluate', {expression: `JSON.stringify({page:document.body?.dataset.page,path:location.pathname,
        global:document.querySelector('#global-message')?.textContent,saved:document.querySelector('#saved-status')?.textContent,
        profile:document.querySelector('#profile-status')?.textContent,complaint:document.querySelector('#complaint-status')?.textContent,
        detail:document.querySelector('#detail-status')?.textContent,caseMessage:document.querySelector('#case-message')?.textContent,
        caseGate:document.querySelector('#case-gate')?.textContent,fleetMessage:document.querySelector('#fleet-message')?.textContent,
        fleetGate:document.querySelector('#fleet-gate')?.textContent,adminMessage:document.querySelector('#admin-message')?.textContent,
        adminGate:document.querySelector('#admin-gate')?.textContent,analytics:document.querySelector('#analytics-status')?.textContent})`, returnByValue: true});
      state = JSON.parse(result.result.value);
    } catch {}
  }
  process.stderr.write(JSON.stringify({failed: message, passed_checks: checks.length, last_check: checks.at(-1), state, uncaught_exceptions: exceptions.length}) + '\n');
  process.exitCode = 1;
} finally {
  if (browser) { try { await browser.send('Browser.close'); } catch {} }
  page?.close(); browser?.close();
  if (child.exitCode === null) {
    await Promise.race([new Promise(resolve=>child.once('exit', resolve)), delay(4000)]);
    if (child.exitCode === null) child.kill();
  }
}
