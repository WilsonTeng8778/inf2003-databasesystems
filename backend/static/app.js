/* The workspace renders all database content as text, never as HTML. */
"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const state = {user: null, csrf: null, vehicle: null, evidence: "recalls", evidencePage: 1,
  caseId: null, fleetId: null, casePage: 1, fleetPage: 1, savedPage: 1, matchPage: 1, vehiclePage: 1, adminPage: 1, authMode: "login"};
const fmt = value => Number(value || 0).toLocaleString();

function el(tag, attrs = {}, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "className") element.className = value;
    else if (key === "onClick") element.addEventListener("click", value);
    else if (key === "onSubmit") element.addEventListener("submit", value);
    else if (key === "value") element.value = value;
    else if (key === "style") Object.assign(element.style, value);
    else if (value === true) element.setAttribute(key, "");
    else element.setAttribute(key, String(value));
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}
function replace(target, ...children) {
  target.replaceChildren(...children.flat(Infinity).filter(child => child !== null && child !== undefined && child !== false)
    .map(child => child instanceof Node ? child : document.createTextNode(String(child))));
}
function message(text, error = false) {
  const target = $("#notice"); target.textContent = text; target.classList.toggle("error", error); target.hidden = !text;
}
function clearPrivateViews() {
  for (const id of ["saved-content", "case-list", "case-detail", "fleet-list", "fleet-detail", "admin-users", "admin-imports"]) replace($(`#${id}`));
  state.caseId = null; state.fleetId = null;
}
async function refreshAfterWrite(callback) {
  try { await callback(); } catch (error) { message(`Saved, but the display could not refresh: ${error.message}`, true); }
}
function action(fn) { return async event => { try { await fn(event); } catch (error) { message(error.message || "The request failed.", true); } }; }
function button(label, handler, extra = "button-outline") { return el("button", {type:"button", className:`button button-small ${extra}`, onClick:action(handler)}, label); }
function empty(title, description) { return el("div", {className:"empty-state"}, el("strong", {}, title), el("p", {}, description)); }
function dateText(value) { return value ? String(value).slice(0, 10) : "Date not supplied"; }
function vehicleText(vehicle) { return `${vehicle.year} ${vehicle.make} ${vehicle.model}`; }

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = {"Accept":"application/json"};
  if (method !== "GET") { headers["Content-Type"] = "application/json"; headers["X-CSRF-Token"] = state.csrf || ""; }
  const response = await fetch(path, {method, headers, credentials:"same-origin",
    body: method === "GET" ? undefined : JSON.stringify(options.body || {})});
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/auth/login") { state.user = null; state.csrf = null; clearPrivateViews(); updateAccount(); }
    const error = new Error(data?.error?.message || `Request failed (${response.status})`); error.status = response.status; throw error;
  }
  return data;
}
async function ensureCsrf() { if (!state.csrf) state.csrf = (await api("/api/auth/csrf")).csrfToken; }
function requireUser(analyst = false) {
  if (!state.user) { if (!$("#auth-dialog").open) $("#auth-dialog").showModal(); return false; }
  if (analyst && !["ANALYST", "ADMIN"].includes(state.user.role)) { message("Analyst or administrator access is needed for investigation cases.", true); return false; }
  return true;
}
function updateAccount() {
  $("#account-label").textContent = state.user ? `${state.user.email} · ${state.user.role.replace("_", " ")}` : "Guest access";
  $("#account-button").textContent = state.user ? "Sign out" : "Sign in";
  $("#nav-admin").hidden = state.user?.role !== "ADMIN";
}
async function refreshSession() {
  try { state.user = (await api("/api/auth/me")).user; }
  catch (error) { if (error.status !== 401) throw error; state.user = null; }
  state.csrf = (await api("/api/auth/csrf")).csrfToken;
  updateAccount();
}
function showView(name, refresh = true) {
  for (const section of document.querySelectorAll(".view")) section.hidden = section.id !== `view-${name}`;
  for (const item of document.querySelectorAll(".nav-item")) {
    const active = item.dataset.view === name; item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page"); else item.removeAttribute("aria-current");
  }
  $("#breadcrumb").textContent = ({research:"VEHICLE RESEARCH", saved:"SAVED VEHICLES", cases:"INVESTIGATION CASES", fleets:"FLEET RECALLS", admin:"ADMINISTRATION"})[name];
  if (refresh && name === "saved") action(loadSaved)();
  if (refresh && name === "cases") action(loadCases)();
  if (refresh && name === "fleets") action(loadFleets)();
  if (refresh && name === "admin") action(loadAdmin)();
}

function formDialog(title, description, fields, submitLabel, callback) {
  const dialog = el("dialog");
  const form = el("form", {className:"dialog-card"});
  const error = el("div", {className:"form-error", role:"alert"});
  const inputs = fields.map(field => {
    let input;
    if (field.options) {
      input = el("select", {name:field.name}, field.options.map(value => el("option", {value}, value.replaceAll("_", " "))));
      input.value = field.value || field.options[0];
    } else if (field.multiline) input = el("textarea", {name:field.name, maxlength:field.maxlength || 2000, required:field.required !== false}, field.value || "");
    else input = el("input", {name:field.name, type:field.type || "text", value:field.value || "", maxlength:field.maxlength || 200, required:field.required !== false});
    return el("label", {}, field.label.toUpperCase(), input);
  });
  const submit = el("button", {type:"submit", className:"button button-primary full"}, submitLabel);
  form.append(el("div", {className:"dialog-top"}, el("span", {className:"eyebrow"}, "WORKSPACE ACTION"),
      el("button", {type:"button", className:"icon-button", "aria-label":"Close", onClick:() => dialog.close()}, "×")),
    el("h2", {}, title), el("p", {}, description), ...inputs, error, submit);
  form.addEventListener("submit", async event => {
    event.preventDefault(); error.textContent = ""; submit.disabled = true;
    try { await callback(Object.fromEntries(new FormData(form))); dialog.close(); }
    catch (exception) { error.textContent = exception.message || "The request failed."; }
    finally { submit.disabled = false; }
  });
  dialog.append(form); document.body.append(dialog); dialog.addEventListener("close", () => dialog.remove()); dialog.showModal();
}
function pagination(target, pageInfo, onPage) {
  if (!pageInfo || pageInfo.totalPages <= 1) { replace(target); return; }
  const prev = button("Previous", () => onPage(pageInfo.page - 1)); prev.disabled = pageInfo.page <= 1;
  const next = button("Next", () => onPage(pageInfo.page + 1)); next.disabled = pageInfo.page >= pageInfo.totalPages;
  replace(target, prev, el("span", {}, `Page ${pageInfo.page} of ${pageInfo.totalPages}`), next);
}

async function searchVehicles(event) {
  event.preventDefault(); const form = new FormData(event.currentTarget); const params = new URLSearchParams();
  for (const name of ["year", "make", "model"]) { const value = String(form.get(name) || "").trim(); if (value) params.set(name, value); }
  params.set("pageSize", "20");
  const result = await api(`/api/vehicles/search?${params}`);
  const target = $("#search-results");
  if (!result.items.length) { replace(target, el("span", {className:"subtle"}, "No matching vehicles in the imported catalogue.")); return; }
  replace(target, ...result.items.map(item => el("button", {type:"button", className:"search-choice", onClick:action(() => selectVehicle(item))}, vehicleText(item))),
    result.pagination.total > result.items.length ? el("span", {className:"subtle"}, `Showing 20 of ${fmt(result.pagination.total)} matches. Refine your search.`) : null);
}
async function selectVehicle(vehicle) {
  if (state.vehicle?.modelYearId !== vehicle.modelYearId) $("#complaint-filters").reset();
  state.vehicle = vehicle; state.evidencePage = 1; $("#selected-vehicle").hidden = false;
  $("#vehicle-title").textContent = vehicleText(vehicle); $("#overview-meta").textContent = "IMPORTED DATA SNAPSHOT";
  for (const id of ["recalls", "investigations", "complaints"]) $(`#metric-${id}`).textContent = "…";
  const query = new URLSearchParams({year:vehicle.year, make:vehicle.make, model:vehicle.model});
  const [profile, insight] = await Promise.all([api(`/api/vehicles/safety-profile?${query}`), api(`/api/vehicles/${vehicle.modelYearId}/insights`)]);
  if (state.vehicle?.modelYearId !== vehicle.modelYearId) return;
  $("#metric-recalls").textContent = fmt(profile.officialRecallCampaigns);
  $("#metric-investigations").textContent = fmt(profile.officialInvestigations);
  $("#metric-complaints").textContent = fmt(profile.consumerComplaints);
  renderInsights(insight); await loadEvidence();
}
function renderInsights(data) {
  const components = $("#component-chart"), timeline = $("#timeline-chart");
  components.className = ""; timeline.className = "";
  if (!data.components.length) replace(components, el("div", {className:"chart-empty"}, "No component data in this snapshot."));
  else {
    const max = Math.max(...data.components.map(item => item.count), 1);
    replace(components, el("div", {className:"bar-list"}, data.components.map(item => {
      const name = String(item._id || "Unknown");
      const label = el("button", {type:"button", className:"text-button bar-label", title:`Filter by ${name}`,
        onClick:action(async () => { $("#complaint-filters [name=component]").value = name; setEvidence("complaints"); await loadEvidence(); })}, name);
      return el("div", {className:"bar-row"}, label, el("div", {className:"bar-track"}, el("div", {className:"bar-fill", style:{width:`${100 * item.count / max}%`}})), el("strong", {}, fmt(item.count)));
    })));
  }
  if (!data.monthly.length) replace(timeline, el("div", {className:"chart-empty"}, "No dated reports in this snapshot."));
  else {
    const items = data.monthly.slice(-12), max = Math.max(...items.map(item => item.count), 1);
    replace(timeline, el("div", {className:"timeline", role:"img", "aria-label":`Last ${items.length} available months of complaint counts`},
      items.map(item => el("div", {className:"timeline-column", title:`${item._id}: ${item.count} reports`},
        el("div", {className:"timeline-bar", style:{height:`${Math.max(2, 75 * item.count / max)}px`}}), el("span", {className:"timeline-label"}, item._id)))));
  }
}
function setEvidence(kind) {
  state.evidence = kind; state.evidencePage = 1;
  document.querySelectorAll(".tab").forEach(tab => { const active = tab.dataset.evidence === kind; tab.classList.toggle("active", active); tab.setAttribute("aria-selected", String(active)); });
  $("#complaint-filters").hidden = kind !== "complaints";
}
async function loadEvidence() {
  if (!state.vehicle) return;
  const vehicleId = state.vehicle.modelYearId, kind = state.evidence;
  const params = new URLSearchParams({page:String(state.evidencePage), pageSize:"10"});
  if (kind === "complaints") for (const [key, value] of new FormData($("#complaint-filters"))) if (String(value).trim()) params.set(key, value);
  const data = await api(`/api/vehicles/${vehicleId}/${kind}?${params}`);
  if (vehicleId !== state.vehicle?.modelYearId || kind !== state.evidence) return;
  const target = $("#evidence-list");
  if (!data.items.length) replace(target, empty("No records found", "Try another vehicle or adjust the filters."));
  else replace(target, el("div", {className:"record-list"}, data.items.map(item => evidenceRecord(kind, item))));
  pagination($("#evidence-pagination"), data.pagination, async page => {state.evidencePage = page; await loadEvidence();});
}
function evidenceRecord(kind, item) {
  if (kind === "recalls") return el("article", {className:"record"},
    el("div", {className:"record-head"}, el("h4", {}, `Recall ${item.campaignNumber}`), el("span", {className:"badge"}, dateText(item.reportDate))),
    el("p", {}, item.summary || "No summary supplied."),
    item.consequence ? el("p", {}, `Consequence: ${item.consequence}`) : null,
    item.remedy ? el("p", {}, `Remedy: ${item.remedy}`) : null,
    item.doNotDrive || item.parkOutside ? el("p", {className:"error-text"}, [item.doNotDrive ? "Do not drive" : "", item.parkOutside ? "Park outside" : ""].filter(Boolean).join(" · ")) : null);
  if (kind === "investigations") return el("article", {className:"record"},
    el("div", {className:"record-head"}, el("h4", {}, item.subject || `Investigation ${item.investigationNumber}`), el("span", {className:"badge"}, item.status)),
    el("div", {className:"record-meta"}, `${item.investigationNumber} · Opened ${dateText(item.openedDate)}`),
    el("p", {}, item.summary || "No summary supplied."));
  return el("article", {className:"record"},
    el("div", {className:"record-head"}, el("h4", {}, `Complaint ${item.odiNumber}`), el("span", {className:"badge"}, dateText(item.receivedDate))),
    el("div", {className:"record-meta"}, (item.components || []).join(" · ") || "Component not supplied"),
    el("p", {}, item.narrative || "No narrative supplied."),
    el("div", {className:"inline-actions"}, button("Create case with this report", () => openCreateCase(item.odiNumber))));
}

async function loadSaved() {
  const target = $("#saved-content"); if (!requireUser()) { replace(target, empty("Sign in to see saved vehicles", "Your saved models stay attached to your account.")); return; }
  const result = await api(`/api/saved-vehicles?page=${state.savedPage}&pageSize=20`);
  if (!result.items.length) { replace(target, empty("No saved vehicles yet", "Search for a vehicle and choose Save vehicle.")); return; }
  const page = el("div", {className:"pagination"});
  pagination(page, result.pagination, async n => {state.savedPage = n; await loadSaved();});
  replace(target, ...result.items.map(item => el("article", {className:"card record"},
    el("div", {className:"record-head"}, el("div", {}, el("h4", {}, item.nickname || vehicleText(item.vehicle)),
      el("div", {className:"record-meta"}, vehicleText(item.vehicle))), el("span", {className:"badge"}, "SAVED")),
    el("div", {className:"inline-actions"},
      button("Open profile", async () => {showView("research"); await selectVehicle({modelYearId:item.modelYearId, ...item.vehicle});}),
      button("Rename", () => formDialog("Rename vehicle", "Give this saved model a personal nickname.",
        [{name:"nickname", label:"Nickname", value:item.nickname, required:false, maxlength:100}], "Save changes", async values => {
          await api(`/api/saved-vehicles/${item.savedVehicleId}`, {method:"PATCH", body:values}); await loadSaved();})),
      button("Remove", async () => {if (confirm("Remove this saved vehicle?")) {await api(`/api/saved-vehicles/${item.savedVehicleId}`, {method:"DELETE"}); await loadSaved();}}, "button-danger")))), page);
}
async function saveCurrentVehicle() {
  if (!state.vehicle || !requireUser()) return;
  await api("/api/saved-vehicles", {method:"POST", body:{modelYearId:state.vehicle.modelYearId}}); message("Vehicle saved to your account.");
}

function openCreateCase(complaintId = null) {
  if (!requireUser(true)) return;
  if (!state.vehicle) { message("Select a vehicle in research before creating a case.", true); showView("research"); return; }
  const vehicle = state.vehicle;
  formDialog("Open an investigation", `Create an internal case for ${vehicleText(vehicle)}.`,
    [{name:"title", label:"Case title"}, {name:"priority", label:"Priority", options:["MEDIUM", "LOW", "HIGH"]}], "Create case", async values => {
      const result = await api("/api/cases", {method:"POST", body:{modelYearId:vehicle.modelYearId, ...values}});
      const id = result.case.caseId; state.caseId = id;
      if (complaintId && !result.sync.pending) {
        try { await api(`/api/cases/${id}/links`, {method:"PUT", body:{complaintIds:[String(complaintId)]}}); }
        catch (error) { message(`Case created, but the complaint was not linked: ${error.message}`, true); }
      } else if (result.sync.pending) message(`Case created. Retry synchronization from the case${complaintId ? `, then link complaint ${complaintId}` : ""}.`, true);
      showView("cases", false); await refreshAfterWrite(loadCases);
    });
}
async function loadCases() {
  const list = $("#case-list"), detail = $("#case-detail");
  if (!requireUser(true)) { replace(list, empty("Analyst access required", "Sign in with an analyst or administrator account.")); replace(detail); return; }
  const result = await api(`/api/cases?page=${state.casePage}&pageSize=20`);
  const page = el("div", {className:"pagination"}); pagination(page, result.pagination, async n => {state.casePage=n; await loadCases();});
  replace(list, el("h3", {}, "Your cases"), result.items.length ? result.items.map(item => el("button", {type:"button", className:`list-button${item.caseId===state.caseId ? " active" : ""}`, onClick:action(async () => {state.caseId=item.caseId; await loadCases();})},
    el("strong", {}, item.title), el("small", {}, `${vehicleText(item.vehicle)} · ${item.status}`))) : el("p", {}, "No cases yet. Select a vehicle in research to create one."), page);
  if (state.caseId) await loadCase(state.caseId);
}
async function loadCase(id) {
  state.caseId = id; const data = await api(`/api/cases/${id}`), c = data.case, panel = $("#case-detail");
  const header = el("div", {className:"mini-heading"}, el("div", {}, el("span", {className:"eyebrow"}, `CASE ${id} · ${c.syncStatus.toUpperCase()}`), el("h3", {}, c.title), el("p", {}, `${vehicleText(c.vehicle)} · ${c.priority} · ${c.status}`)),
    el("div", {className:"inline-actions"}, button("Edit case", () => formDialog("Edit case", "Update the case title, priority or status.",
      [{name:"title",label:"Title",value:c.title},{name:"priority",label:"Priority",options:["LOW","MEDIUM","HIGH"],value:c.priority},{name:"status",label:"Status",options:["OPEN","REVIEWING","CLOSED"],value:c.status}], "Save changes", async values => {await api(`/api/cases/${id}`, {method:"PATCH", body:values}); await refreshAfterWrite(loadCases);})),
      button("Delete", async () => {if(confirm("Delete this case and its investigation details?")){const result=await api(`/api/cases/${id}`, {method:"DELETE"}); state.caseId=null; replace(panel, empty("Case deleted", result?.sync?.pending ? "Document deletion is pending; an administrator can retry synchronization." : "Select another case.")); await loadCases();}}, "button-danger")));
  if (!data.details) {
    replace(panel, header, el("p", {}, c.syncStatus === "pending" ? "Case details are waiting for database synchronization." : "Case details are missing. Ask an administrator to investigate."),
      c.syncStatus === "pending" ? button("Retry synchronization", async () => {const result=await api(`/api/cases/${id}/sync`, {method:"POST"}); message(result.sync.pending ? "Synchronization is still pending." : "Case details are ready.", !!result.sync.pending); await loadCase(id);}) : null);
    return;
  }
  const d = data.details;
  const linked = d.linkedComplaints.length ? await api(`/api/cases/${id}/complaints`) : {items:[], missingIds:[]};
  const links = el("form", {onSubmit:action(async event => {event.preventDefault(); const ids=String(new FormData(event.currentTarget).get("ids")||"").split(",").map(x=>x.trim()).filter(Boolean); await api(`/api/cases/${id}/links`, {method:"PUT", body:{complaintIds:ids}}); message("Linked complaints updated."); await loadCase(id);})},
    el("label", {}, "COMPLAINT ODI IDS · COMMA SEPARATED", el("input", {name:"ids", value:d.linkedComplaints.join(", "), placeholder:"e.g. 12345678, 12345679"})), el("button", {className:"button button-outline button-small", type:"submit"}, "Save links"));
  const classification = el("form", {onSubmit:action(async event => {event.preventDefault(); const values=new FormData(event.currentTarget); const list=name=>String(values.get(name)||"").split(",").map(x=>x.trim()).filter(Boolean); await api(`/api/cases/${id}/classification`, {method:"PUT", body:{tags:list("tags"),suspectedComponents:list("components")}}); message("Classification updated."); await loadCase(id);})},
    el("div", {className:"field-grid"}, el("label", {}, "TAGS · COMMA SEPARATED", el("input", {name:"tags", value:d.tags.join(", ")})),
      el("label", {}, "SUSPECTED COMPONENTS", el("input", {name:"components", value:d.suspectedComponents.join(", ")}))),
    el("button", {className:"button button-outline button-small", type:"submit"}, "Save classification"));
  const entries = kind => {
    const idKey = kind === "notes" ? "noteId" : "findingId", textKey = kind === "notes" ? "text" : "observation";
    const add = button(`+ Add ${kind === "notes" ? "note" : "finding"}`, () => editEntry(id, kind));
    return el("div", {}, el("div", {className:"mini-heading"}, el("h4", {}, kind === "notes" ? "Notes" : "Findings"), add),
      d[kind].length ? d[kind].map(item => el("article", {className:"record"}, el("p", {}, item[textKey]), el("div", {className:"record-meta"}, `Author ${item.authorId} · ${dateText(item.createdAt)}`),
        el("div", {className:"inline-actions"}, button("Edit", () => editEntry(id, kind, item)), button("Delete", async () => {if(confirm("Delete this entry?")){await api(`/api/cases/${id}/${kind}/${item[idKey]}`, {method:"DELETE"}); await loadCase(id);}}, "button-danger")))) : el("p", {}, `No ${kind} added yet.`));
  };
  const evidence = linked.items.map(item => el("article", {className:"record"},
    el("div", {className:"record-head"}, el("h4", {}, `Complaint ${item.odiNumber}`), el("span", {className:"badge"}, dateText(item.receivedDate))),
    el("div", {className:"record-meta"}, (item.components || []).join(" · ")), el("p", {}, item.narrative || "No narrative supplied."),
    button("Unlink", async () => {await api(`/api/cases/${id}/links`, {method:"PUT", body:{complaintIds:d.linkedComplaints.filter(value => value !== item.odiNumber)}}); await loadCase(id);}))); 
  replace(panel, header, el("h4", {}, "Linked complaint evidence"), el("p", {}, "Only complaints for this vehicle can be linked."), links,
    evidence, linked.missingIds.length ? el("p", {className:"error-text"}, `Unavailable linked complaint IDs: ${linked.missingIds.join(", ")}`) : null,
    el("h4", {}, "Classification"), classification, entries("findings"), entries("notes"),
    el("h4", {}, "Status history"), data.history.length ? data.history.map(item => el("p", {}, `${item.from} → ${item.to} · ${dateText(item.changedAt)}`)) : el("p", {}, "No status changes yet."));
}
function editEntry(caseId, kind, item = null) {
  const key = kind === "notes" ? "text" : "observation", idKey = kind === "notes" ? "noteId" : "findingId";
  formDialog(item ? `Edit ${kind.slice(0,-1)}` : `Add ${kind.slice(0,-1)}`, "Keep the observation grounded in the available evidence.",
    [{name:key, label:key, multiline:true, value:item?.[key] || ""}], "Save", async values => {
      await api(`/api/cases/${caseId}/${kind}${item ? `/${item[idKey]}` : ""}`, {method:item ? "PATCH" : "POST", body:values}); await refreshAfterWrite(() => loadCase(caseId));
    });
}

async function loadFleets() {
  const list=$("#fleet-list"), detail=$("#fleet-detail");
  if (!requireUser()) {replace(list,empty("Sign in to manage a fleet","Fleet records are private to their owner."));replace(detail);return;}
  const data=await api(`/api/fleets?page=${state.fleetPage}&pageSize=20`), page=el("div",{className:"pagination"});
  pagination(page,data.pagination,async n=>{state.fleetPage=n;await loadFleets();});
  replace(list,el("h3",{},"Your fleets"),data.items.length ? data.items.map(item=>el("button",{type:"button",className:`list-button${item.fleetId===state.fleetId?" active":""}`,onClick:action(async()=>{state.fleetId=item.fleetId;state.matchPage=1;state.vehiclePage=1;await loadFleets();await loadFleet(item.fleetId);})},el("strong",{},item.name),el("small",{},`Created ${dateText(item.createdAt)}`))) : el("p",{},"Create a fleet to track its model-level recall matches."),page);
}
function createFleet() {
  if (!requireUser()) return;
  formDialog("Create a fleet","Give your fleet a name.",[{name:"name",label:"Fleet name",maxlength:120}],"Create fleet",async values=>{
    const result=await api("/api/fleets",{method:"POST",body:values});state.fleetId=result.fleet.fleetId;await refreshAfterWrite(async()=>{await loadFleets();await loadFleet(state.fleetId);});
  });
}
async function loadFleet(id) {
  state.fleetId=id; const [data,matches]=await Promise.all([api(`/api/fleets/${id}?page=${state.vehiclePage}&pageSize=20`),api(`/api/fleets/${id}/matches?page=${state.matchPage}&pageSize=20`)]), panel=$("#fleet-detail");
  const header=el("div",{className:"mini-heading"},el("div",{},el("span",{className:"eyebrow"},`FLEET ${id}`),el("h3",{},data.fleet.name)),
    el("div",{className:"inline-actions"},button("Rename",()=>formDialog("Rename fleet","Update your fleet name.",[{name:"name",label:"Fleet name",value:data.fleet.name}],"Save",async values=>{await api(`/api/fleets/${id}`,{method:"PATCH",body:values});await loadFleets();await loadFleet(id);})),
      button("Delete fleet",async()=>{if(confirm("Delete this fleet, its vehicles and its work orders?")){await api(`/api/fleets/${id}`,{method:"DELETE"});state.fleetId=null;replace(panel,empty("Fleet deleted","Select another fleet."));await loadFleets();}},"button-danger")));
  const add=button("+ Add selected vehicle",()=>{
    if(!state.vehicle){message("Select a vehicle in research first, then return to your fleet.",true);return;}
    formDialog("Add a vehicle",`Add ${vehicleText(state.vehicle)} to this fleet.`,[{name:"label",label:"Vehicle label",maxlength:120}],"Add vehicle",async values=>{await api(`/api/fleets/${id}/vehicles`,{method:"POST",body:{modelYearId:state.vehicle.modelYearId,label:values.label}});await refreshAfterWrite(()=>loadFleet(id));});
  });
  const vehicles=data.vehicles.length ? data.vehicles.map(item=>el("article",{className:"record"},el("div",{className:"record-head"},el("div",{},el("h4",{},item.label),el("div",{className:"record-meta"},vehicleText(item.vehicle))),button("Remove",async()=>{if(confirm("Remove this vehicle and its work orders?")){await api(`/api/fleets/${id}/vehicles/${item.fleetVehicleId}`,{method:"DELETE"});await loadFleet(id);}},"button-danger")))) : el("p",{},"No vehicles added. Select a model in research first.");
  const vehiclePage=el("div",{className:"pagination"}); pagination(vehiclePage,data.vehiclePagination,async n=>{state.vehiclePage=n;await loadFleet(id);});
  const matchPage=el("div",{className:"pagination"}); pagination(matchPage,matches.pagination,async n=>{state.matchPage=n;await loadFleet(id);});
  const records=matches.items.length ? matches.items.map(item=>{
    const actions = item.workOrderId ? [
      button("Update work order",()=>formDialog("Update work order","Record the current action status.",
        [{name:"status",label:"Status",options:["OPEN","IN_PROGRESS","COMPLETED","CANCELLED"],value:item.workOrderStatus},
         {name:"notes",label:"Notes",multiline:true,required:false,value:item.workOrderNotes || ""}],"Save",async values=>{
          await api(`/api/fleets/${id}/work-orders/${item.workOrderId}`,{method:"PATCH",body:values});await loadFleet(id);
        })),
      button("Delete order",async()=>{if(confirm("Delete this work order?")){
        await api(`/api/fleets/${id}/work-orders/${item.workOrderId}`,{method:"DELETE"});await loadFleet(id);
      }},"button-danger")
    ] : [button("Create work order",()=>formDialog("Create work order",`Track ${item.campaignNumber} for ${item.label}.`,
      [{name:"notes",label:"Notes",multiline:true,required:false}],"Create order",async values=>{
        await api(`/api/fleets/${id}/work-orders`,{method:"POST",body:{fleetVehicleId:item.fleetVehicleId,recallId:item.recallId,notes:values.notes}});await refreshAfterWrite(()=>loadFleet(id));
      }))];
    return el("article",{className:"record"},el("div",{className:"record-head"},
      el("div",{},el("h4",{},`${item.label} · ${item.campaignNumber}`),el("div",{className:"record-meta"},`${item.year} ${item.make} ${item.model}`)),
      el("span",{className:"badge"},item.workOrderStatus || "NO WORK ORDER")),el("div",{className:"inline-actions"},actions));
  }) : el("p",{},"No recall matches in the imported snapshot.");
  replace(panel,header,el("div",{className:"mini-heading"},el("h4",{},"Fleet vehicles"),add),vehicles,vehiclePage,el("h4",{},"Recall matches & work orders"),el("p",{},matches.interpretation),records,matchPage);
}

async function loadAdmin() {
  if (!state.user || state.user.role !== "ADMIN") {replace($("#admin-users"),empty("Administrator access required","Sign in with an administrator account."));replace($("#admin-imports"));message("Administrator access is required.",true);return;}
  const [users,imports]=await Promise.all([api(`/api/admin/users?page=${state.adminPage}&pageSize=20`),api("/api/admin/imports")]);
  const userPage=el("div",{className:"pagination"});pagination(userPage,users.pagination,async n=>{state.adminPage=n;await loadAdmin();});
  replace($("#admin-users"),el("h3",{},"Users & roles"),el("p",{},"Role changes take effect on the user's next request."),
    users.items.map(user=>el("article",{className:"record"},el("h4",{},user.email),el("div",{className:"record-meta"},user.role),
      button("Change role",()=>formDialog("Change user role",user.email,[{name:"role",label:"Role",options:["NORMAL_USER","ANALYST","ADMIN"],value:user.role}],"Save role",async values=>{await api(`/api/admin/users/${user.userId}/role`,{method:"PATCH",body:values});await refreshAfterWrite(async()=>{await refreshSession();await loadAdmin();});})))),userPage,
    el("div",{className:"inline-actions"},button("Retry pending case sync",async()=>{const result=await api("/api/admin/case-sync",{method:"POST"});message(`${result.sync.processed} synchronization jobs processed; ${result.sync.pending} pending.`,!!result.sync.pending);}))); 
  replace($("#admin-imports"),el("h3",{},"Data imports"),el("p",{},"Refreshing imports writes reference data and may take time. Source archives must be available locally."),
    imports.sources.map(item=>el("article",{className:"record"},el("div",{className:"record-head"},el("h4",{},item.filename),el("span",{className:"badge"},item.available?"AVAILABLE":"MISSING")))),
    el("div",{className:"inline-actions"},button(imports.startedByThisServer ? "Import running" : "Start data refresh",async()=>{if(confirm("Refresh imported reference data from the four local source archives? This updates existing reference records.")){await api("/api/admin/imports/run",{method:"POST"});message("Import started. Refresh this page to inspect its progress.");await loadAdmin();}},"button-primary"),button("Refresh status",loadAdmin)),
    el("h4",{},"Recent import runs"),imports.recentImports.length ? imports.recentImports.map(item=>el("p",{},`${item.dataset} · ${item.status} · ${dateText(item.startedAt)} · ${fmt(item.read)} read`)) : el("p",{},"No import runs recorded."));
}

document.querySelectorAll(".nav-item").forEach(item=>item.addEventListener("click",()=>showView(item.dataset.view)));
$("#search-form").addEventListener("submit",action(searchVehicles));
$("#save-vehicle").addEventListener("click",action(saveCurrentVehicle));
$("#new-case-from-profile").addEventListener("click",()=>openCreateCase());
$("#create-case").addEventListener("click",()=>openCreateCase());
$("#create-fleet").addEventListener("click",createFleet);
document.querySelectorAll(".tab").forEach(tab=>tab.addEventListener("click",action(async()=>{setEvidence(tab.dataset.evidence);await loadEvidence();})));
$("#complaint-filters").addEventListener("submit",action(async event=>{event.preventDefault();state.evidencePage=1;await loadEvidence();}));
$("#account-button").addEventListener("click",action(async()=>{if(!state.user){$("#auth-dialog").showModal();return;}if(confirm("Sign out?")){const result=await api("/api/auth/logout",{method:"POST"});state.csrf=result.csrfToken;state.user=null;clearPrivateViews();updateAccount();showView("research");message("Signed out.");}}));
$("#close-auth").addEventListener("click",()=>$("#auth-dialog").close());
$("#toggle-auth").addEventListener("click",()=>{state.authMode=state.authMode==="login"?"register":"login";const register=state.authMode==="register";$("#auth-title").textContent=register?"Create your account.":"Welcome back.";$("#auth-copy").textContent=register?"Use at least 12 characters for your password.":"Sign in to save vehicles and manage your work.";$("#auth-submit").textContent=register?"Create account":"Sign in";$("#toggle-auth").textContent=register?"Already have an account? Sign in":"New here? Create an account";$("#auth-error").textContent="";});
$("#auth-form").addEventListener("submit",async event=>{event.preventDefault();const form=event.currentTarget,error=$("#auth-error"),submit=$("#auth-submit");error.textContent="";submit.disabled=true;try{await ensureCsrf();const result=await api(`/api/auth/${state.authMode}`,{method:"POST",body:Object.fromEntries(new FormData(form))});state.user=result.user;state.csrf=result.csrfToken;updateAccount();form.reset();$("#auth-dialog").close();message(`Signed in as ${state.user.email}.`);const active=document.querySelector(".nav-item.active")?.dataset.view;if(active && active!=="research") showView(active);}catch(exception){error.textContent=exception.message;}finally{submit.disabled=false;}});
action(async()=>{
  await refreshSession();
  const source=document.body.dataset.sourceLabel || "NHTSA DATA";
  try {
    await api("/api/health");
    $("#connection-label").textContent="Databases connected";
  } catch (error) {
    $("#connection-label").textContent="Databases unavailable";
    $("#connection-dot").classList.add("offline");
    $("#data-context").textContent=`Data source: ${source} · Import dates unavailable.`;
    return;
  }
  try {
    const datasets=await api("/api/datasets");
    $("#data-context").textContent=datasets.datasets.length
      ? `Data source: ${source} · Latest successful imports: ${datasets.datasets.map(item=>`${item.name} ${dateText(item.importedAt)}`).join(" · ")}`
      : `Data source: ${source} · No successful import date recorded.`;
  } catch (error) {
    $("#data-context").textContent=`Data source: ${source} · Import history unavailable; check the current database views and reader grants.`;
  }
})();
