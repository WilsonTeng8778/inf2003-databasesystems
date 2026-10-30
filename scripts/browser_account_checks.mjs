/* Account deletion targets only the explicitly supplied disposable fixture IDs. */
export async function accountChecks({page,evaluate,goto,wait,click,fill,submit,screenshot,check,login,signedOut,fixtures}) {
  // The preceding analytics journey finishes at mobile size.
  await page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  const json=expression=>evaluate(`(async()=>{const m=await import('/static/api.js');return ${expression};})()`);
  // Identity refresh starts before the list request. Its previous aria-busy/status
  // values can still look ready while writes are deliberately disabled.
  const ready=()=>wait(`document.querySelector('#admin-users')?.getAttribute('aria-busy')==='false' && document.querySelector('#admin-users-status')?.textContent.endsWith('application accounts.') && !document.querySelector('#admin-users')?.querySelector('button:disabled')`,'account list and enabled controls');
  const users=()=>json(`m.api('/api/admin/users?pageSize=100')`);
  async function locate(target) {
    const result=await users();const index=result.items.findIndex(item=>item.userId===target.userId);
    if(index<0)throw new Error('Owned account fixture missing before deletion');
    await goto('/admin/users?page='+(Math.floor(index/10)+1));await ready();
  }
  async function open(target) {
    await locate(target);await click(`[data-delete-user="${target.userId}"]`);
    await wait(`document.querySelector('#admin-delete-dialog').open`,'delete dialog');
  }
  async function confirm(target) {
    await fill('admin-delete-email',target.email);await submit('#admin-delete-form');
    await wait(`!document.querySelector('#admin-delete-dialog').open`,'delete dialog close');
  }
  for(const [index,expected] of [[null,401],[1,403],[2,403]]) {
    if(index!==null){await goto('/login');await login(index);await wait(`document.querySelector('#log-out')!==null`,'restricted actor login');}
    const result=await json(`m.api('/api/admin/users/${fixtures[0].userId}',{method:'DELETE',body:{confirmEmail:${JSON.stringify(fixtures[0].email)}}}).catch(error=>error.status)`);
    check(result===expected,'Account deletion rejects '+(index===null?'signed-out users':index===1?'normal users':'analysts'));
    if(index!==null)await signedOut();
  }
  await goto('/login?next=%2Fadmin%2Fusers');await login(4);await ready();
  const me=(await json(`m.api('/api/auth/me')`)).user;
  const self=await json(`m.api('/api/admin/users/${me.userId}',{method:'DELETE',body:{confirmEmail:${JSON.stringify(me.email)}}}).catch(error=>error.status)`);
  check(self===409,'The actual API rejects self-deletion while retaining the admin session');
  await locate(me);check(await evaluate(`!document.querySelector('[data-delete-user="${me.userId}"]')`),'The signed-in account has no delete action');
  const missingCsrf=await evaluate(`fetch('/api/admin/users/${fixtures[0].userId}',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmEmail:${JSON.stringify(fixtures[0].email)}})}).then(response=>response.status)`);
  check(missingCsrf===403,'Account deletion requires CSRF protection');
  check((await json(`m.api('/api/admin/users/${fixtures[0].userId}',{method:'DELETE',body:{confirmEmail:'different@example.invalid'}}).catch(error=>error.status)`))===409,'The server rejects a mismatched confirmation email');
  check((await json(`m.api('/api/admin/users/9223372036854775807',{method:'DELETE',body:{confirmEmail:'missing@example.invalid'}}).catch(error=>error.status)`))===404,'Missing accounts return a bounded not-found response');
  await open(fixtures[0]);
  check(await evaluate(`document.querySelector('#admin-delete-confirm').disabled && document.activeElement.id==='admin-delete-email' && document.querySelector('#admin-delete-dialog').textContent.includes('permanent')`),'Deletion starts with focused email confirmation and explains its permanent effect');
  await fill('admin-delete-email','wrong@example.invalid');check(await evaluate(`document.querySelector('#admin-delete-confirm').disabled`),'The confirmation button stays disabled for the wrong email');
  await click('[data-close-dialog="admin-delete-dialog"]');
  check((await users()).items.some(item=>item.userId===fixtures[0].userId),'Cancelling deletion retains the target account');
  await open(fixtures[3]);await confirm(fixtures[3]);await wait(`document.querySelector('#admin-message').textContent.includes('cannot be deleted')`,'used-account rejection');
  check((await users()).items.some(item=>item.userId===fixtures[3].userId),'A real saved-vehicle dependency blocks account deletion and keeps the account');
  await open(fixtures[0]);await screenshot('account-delete-dialog.png','#admin-delete-dialog');
  await page.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  check(await evaluate(`document.documentElement.scrollWidth<=innerWidth && document.querySelector('#admin-delete-dialog').open && document.querySelector('#admin-delete-dialog').getBoundingClientRect().width>0 && document.querySelector('#admin-delete-dialog').getBoundingClientRect().width<=innerWidth`),'Account rows and the deletion dialog fit a 390px viewport');await screenshot('account-delete-mobile.png','#admin-delete-dialog');
  await page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await confirm(fixtures[0]);await wait(`document.querySelector('#admin-message').textContent.includes('Unused account deleted')`,'successful account deletion');await ready();
  check(!(await users()).items.some(item=>item.userId===fixtures[0].userId),'A confirmed browser deletion removes only the intended unused account');
  await open(fixtures[1]);
  await evaluate(`(()=>{const native=window.fetch.bind(window);window.accountDeleteCalls=0;window.fetch=async(input,options)=>{const selected=String(input)==='/api/admin/users/${fixtures[1].userId}'&&options?.method==='DELETE';if(selected)window.accountDeleteCalls++;const response=await native(input,options);if(selected)throw new TypeError('Injected lost account response');return response;};})()`);
  await confirm(fixtures[1]);await wait(`!document.querySelector('#admin-uncertain').hidden`,'uncertain deletion');
  check(await evaluate(`window.accountDeleteCalls===1 && [...document.querySelectorAll('#admin-users [data-admin-write],.admin-role-form button')].every(node=>node.disabled)`),'A lost deletion response blocks additional account writes without automatically retrying');await screenshot('account-delete-uncertain.png');
  await click('#admin-review-roles');await ready();
  check(await evaluate(`window.accountDeleteCalls===1 && document.querySelector('#admin-uncertain').hidden && !document.querySelector('[data-user-id="${fixtures[1].userId}"]')`),'Refreshing after an uncertain deletion reads the committed result without a second DELETE');
  await open(fixtures[2]);
  await evaluate(`(()=>{const native=window.fetch.bind(window);window.unreadableDeleteCalls=0;window.fetch=async(input,options)=>{const response=await native(input,options);if(String(input)==='/api/admin/users/${fixtures[2].userId}'&&options?.method==='DELETE'){window.unreadableDeleteCalls++;return new Response('invalid json',{status:200,headers:{'Content-Type':'application/json'}});}return response;};})()`);
  await confirm(fixtures[2]);await wait(`!document.querySelector('#admin-uncertain').hidden`,'unreadable deletion response');await click('#admin-review-roles');await ready();
  check(await evaluate(`window.unreadableDeleteCalls===1 && !document.querySelector('[data-user-id="${fixtures[2].userId}"]') && document.querySelector('#admin-uncertain').hidden`),'Unreadable successful deletion also requires reading current accounts and is not replayed');
  await locate(fixtures[3]);
  check(await evaluate(`[...document.querySelectorAll('.admin-user-card h3')].every(node=>node.textContent.startsWith('frontend-verification-'))`),'Deletion screenshots contain only synthetic account rows');await screenshot('account-delete-result.png');
  await open(fixtures[3]);await fill('admin-delete-email',fixtures[3].email);
  await json(`m.api('/api/auth/logout',{method:'POST',body:{}})`);await submit('#admin-delete-form');
  await wait(`document.querySelector('#admin-workspace').hidden && !document.querySelector('#admin-delete-dialog').open`,'expiry during deletion');
  check(await evaluate(`document.querySelector('#admin-delete-email').value==='' && document.querySelectorAll('.admin-user-card').length===0 && document.querySelector('[data-admin-nav]').hidden`),'Session expiry closes deletion confirmation and clears private account data');
}
