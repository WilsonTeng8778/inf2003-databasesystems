/* Public, read-only analytics. SVG and HTML values use DOM text/attributes only. */
import {api} from './api.js';
import {$, element, link, count, pagination, profileURL} from './ui.js';

const fields = {make:'analytics-make',model:'analytics-model',year:'analytics-year',receivedFrom:'analytics-from',receivedTo:'analytics-to'};
let controller=null, current=null;
function reportsURL(selection,extra={}) {
  const query=new URLSearchParams({make:selection.make,model:selection.model,receivedFrom:selection.receivedFrom,receivedTo:selection.receivedTo});
  if(selection.year!==null && selection.year!==undefined)query.set('year',selection.year);
  for(const[key,value]of Object.entries(extra))query.set(key,value);
  return '/complaints?'+query;
}
function table(headers,rows,label) {
  const wrap=element('div','table-wrap');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',label);
  const grid=element('table','research-table'),head=element('thead'),tr=element('tr'),body=element('tbody');
  for(const title of headers){const cell=element('th','',title);cell.scope='col';tr.append(cell);}head.append(tr);
  for(const values of rows){const row=element('tr');for(const value of values){const cell=element('td');cell.append(value instanceof Node?value:document.createTextNode(String(value)));row.append(cell);}body.append(row);}
  grid.append(head,body);wrap.append(grid);return wrap;
}
function svgNode(tag,attrs={},text) {
  const node=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const[key,value]of Object.entries(attrs))node.setAttribute(key,String(value));
  if(text!==undefined)node.textContent=text;return node;
}
function renderTrend(result) {
  const root=$('analytics-trend');root.replaceChildren();
  const values=result.monthly,max=Math.max(...values.map(row=>row.count),1),peak=Math.max(...values.map(row=>row.count),0);
  $('analytics-month-peak').textContent=`Peak ${count(peak)} / month`;
  const svg=svgNode('svg',{viewBox:'0 0 640 200',role:'group','aria-label':'Monthly received complaint counts. Points open the matching complaint reports.'});
  svg.append(svgNode('title',{},'Complaints by received month'),svgNode('desc',{},`${count(result.summary.consumerComplaints)} reports across ${values.length} displayed months. Exact monthly values and links follow in the data table.`));
  for(const y of [20,95,170])svg.append(svgNode('line',{x1:15,x2:625,y1:y,y2:y,class:'analytics-grid-line'}));
  const points=values.map((row,index)=>({row,x:values.length===1?320:15+index/(values.length-1)*610,y:170-row.count/max*150}));
  svg.append(svgNode('polyline',{points:points.map(point=>`${point.x},${point.y}`).join(' '),class:'analytics-trend-line',fill:'none'}));
  for(const{x,y,row}of points){
    const label=`${row.month}: ${count(row.count)} received reports${row.partialMonth?' · Partial selected month':''}`;
    const anchor=svgNode('a',{href:reportsURL(result.selection,{receivedFrom:row.receivedFrom,receivedTo:row.receivedTo}),'aria-label':label,tabindex:0});
    anchor.append(svgNode('title',{},label),svgNode('circle',{cx:x,cy:y,r:values.length>60?2.5:3.5,class:'analytics-trend-point'}));svg.append(anchor);
  }
  root.append(svg);
  const axis=element('div','analytics-axis');for(const row of [values[0],values[Math.floor((values.length-1)/2)],values.at(-1)])axis.append(element('span','',row.month));root.append(axis);
  $('analytics-month-table').replaceChildren(table(['Received month','Loaded reports','Selected dates'],values.map(row=>[
    row.month,link(count(row.count),reportsURL(result.selection,{receivedFrom:row.receivedFrom,receivedTo:row.receivedTo})),`${row.receivedFrom} – ${row.receivedTo}${row.partialMonth?' · Partial month':''}`,
  ]),'Monthly complaint counts and report links; scroll horizontally if needed'));
}
function renderComponents(result) {
  const root=$('analytics-components');root.replaceChildren();const max=Math.max(...result.components.map(row=>row.count),1);
  for(const row of result.components){const item=link('',reportsURL(result.selection,{component:row.component}),'analytics-component');
    const label=element('div','component-title');label.append(element('span','',row.component),element('strong','',count(row.count)));
    const bar=element('div','component-bar'),fill=element('span','component-fill');fill.style.width=`${row.count/max*100}%`;bar.append(fill);item.append(label,bar);root.append(item);}
  if(!result.components.length)root.append(element('p','field-hint','No component mentions in the selected reports.'));
  $('analytics-component-note').textContent=`${result.componentsTruncated?'Showing the ten most mentioned components. ':''}${count(result.summary.complaintsWithoutComponents)} selected complaints have no non-empty component label. Select a bar to explore its reports.`;
}
function renderIncidents(result) {
  const rows=Object.entries(result.incidentReports).map(([name,data])=>[name==='crash'?'Crash':name==='fire'?'Fire':name==='injuries'?'Injury reported':'Fatality reported',count(data.positive),count(data.negative),count(data.unknown)]);
  $('analytics-incidents').replaceChildren(table(['Reported attribute','Yes / positive count','No / zero count','Unknown'],rows,'Reported incident attributes in selected complaint documents'));
}
function renderYears(page=1) {
  const rows=current.modelYears,start=(page-1)*10;
  $('analytics-year-count').textContent=`${count(rows.length)} vehicle identities`;
  $('analytics-year-table').replaceChildren(table(['Model year','Received complaints','Official campaigns','Official investigations','Profile'],rows.slice(start,start+10).map(row=>[
    String(row.year),link(count(row.consumerComplaints),reportsURL(current.selection,{year:row.year})),count(row.officialRecallCampaigns),count(row.officialInvestigations),link('Safety profile →',profileURL(row)),
  ]),'Model-year counts; scroll horizontally if needed'));
  pagination('analytics-years-pagination',{page,totalPages:Math.ceil(rows.length/10)},renderYears);
}
function clearResults() {
  current=null;$('analytics-content').hidden=true;
  for(const id of ['analytics-trend','analytics-components','analytics-incidents','analytics-year-table','analytics-month-table'])$(id).replaceChildren();
  $('analytics-years-pagination').hidden=true;
}
async function load(query) {
  controller?.abort();controller=new AbortController();const active=controller;clearResults();$('analytics-start').hidden=true;
  $('analytics-status').textContent='Combining reference counts and complaint aggregations…';$('analytics-status').className='status-line';$('analytics-form').setAttribute('aria-busy','true');$('analytics-submit').disabled=true;
  history.replaceState(null,'','/analytics?'+query);
  try {
    const result=await api('/api/analytics/vehicle?'+query,{signal:active.signal});if(active!==controller)return;current=result;
    const selection=result.selection;$('analytics-title').textContent=`${selection.year??'All model years'} ${selection.make} ${selection.model}`;
    $('analytics-complaint-count').textContent=count(result.summary.consumerComplaints);$('analytics-recall-count').textContent=count(result.summary.officialRecallCampaigns);$('analytics-investigation-count').textContent=count(result.summary.officialInvestigations);
    $('analytics-reports-link').href=reportsURL(selection);$('analytics-interpretation').textContent=result.interpretation;
    const coverage=result.coverage;
    $('analytics-coverage').textContent=`Requested complaint window: ${selection.receivedFrom} to ${selection.receivedTo} (UTC). ${count(coverage.documentsInVehicleScope)} complaint documents exist for the selected vehicle scope overall; ${count(coverage.undatedComplaintsInVehicleScope)} have no received date and cannot enter a dated chart. ${coverage.firstReceived?'Observed received dates in that scope: '+coverage.firstReceived+' to '+coverage.lastReceived+'.':'No dated reports are available in this vehicle scope.'} Observed dates do not guarantee complete reporting coverage.`;
    renderTrend(result);renderComponents(result);renderIncidents(result);renderYears();$('analytics-content').hidden=false;
    $('analytics-status').textContent=`${count(result.summary.consumerComplaints)} received complaints across ${result.monthly.length} displayed months. Generated ${new Date(result.generatedAtUtc).toLocaleString()}.`;
  } catch(error) {
    if(error.name==='AbortError' || active!==controller)return;
    $('analytics-status').textContent=error.message+' Adjust the filters or try Load analytics again.';$('analytics-status').className='status-line error';
    $('analytics-start').hidden=false;$('analytics-start').replaceChildren(element('h2','',error.status===404?'No matching vehicle':'Analytics unavailable'),element('p','',error.status===404?'Use an exact make/model name from vehicle search.':'Your previous chart has been cleared. The form remains available to retry.'));
  } finally {if(active===controller){$('analytics-submit').disabled=false;$('analytics-form').setAttribute('aria-busy','false');}}
}
export function initAnalytics() {
  const form=$('analytics-form'),initial=$('analytics-start').cloneNode(true),params=new URLSearchParams(location.search);
  for(const[key,id]of Object.entries(fields))if(params.has(key))$(id).value=params.get(key);
  for(const id of ['analytics-from','analytics-to'])$(id).addEventListener('input',()=>$('analytics-to').setCustomValidity(''));
  form.addEventListener('submit',event=>{
    event.preventDefault();const start=$('analytics-from').value,end=$('analytics-to').value;
    const [a,b]=[start,end].map(value=>new Date(value+'T00:00:00Z'));
    const months=(b.getUTCFullYear()-a.getUTCFullYear())*12+b.getUTCMonth()-a.getUTCMonth()+1;
    $('analytics-to').setCustomValidity(start>end?'End date must be on or after start date.':months>120?'Choose at most 120 calendar months.':'');if(!form.reportValidity())return;
    const query=new URLSearchParams();for(const[key,id]of Object.entries(fields))if($(id).value.trim())query.set(key,$(id).value.trim());load(query);
  });
  $('analytics-example').addEventListener('click',()=>{form.reset();$('analytics-to').setCustomValidity('');$('analytics-make').value='HONDA';$('analytics-model').value='CIVIC';$('analytics-year').value='2022';form.requestSubmit();});
  $('analytics-clear').addEventListener('click',()=>{controller?.abort();controller=null;clearResults();form.reset();$('analytics-to').setCustomValidity('');$('analytics-submit').disabled=false;form.setAttribute('aria-busy','false');$('analytics-start').replaceChildren(...Array.from(initial.cloneNode(true).childNodes));$('analytics-start').hidden=false;$('analytics-status').textContent='';history.replaceState(null,'','/analytics');});
  if(params.has('make') || params.has('model')){const query=new URLSearchParams();for(const[key,id]of Object.entries(fields))if(params.has(key))query.set(key,params.get(key));else if($(id).value)query.set(key,$(id).value);load(query);}
}
