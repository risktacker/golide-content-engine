const platforms=["instagram","facebook","linkedin","x"];const labels={instagram:"Instagram",facebook:"Facebook",linkedin:"LinkedIn",x:"X"};const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];

function switchView(name){$$(".view").forEach(v=>v.classList.toggle("active",v.id===name));$$(".nav").forEach(v=>v.classList.toggle("active",v.dataset.view===name));$("#view-title").textContent=name[0].toUpperCase()+name.slice(1);if(name==="schedule")loadSchedule();if(name==="inbox")loadInbox();if(name==="connections")loadConnections()}
$$(".nav").forEach(b=>b.onclick=()=>switchView(b.dataset.view));$$("[data-open-create]").forEach(b=>b.onclick=()=>switchView("create"));

function platformRows(){const root=$("#platforms");root.innerHTML=platforms.map((p,i)=>`<div class="platform-row"><div class="platform-top"><input type="checkbox" id="use-${p}" ${i<2?"checked":""}><label for="use-${p}">${labels[p]}</label></div><textarea id="copy-${p}" placeholder="${labels[p]} version"></textarea></div>`).join("")}
platformRows();

$("#copy-master").onclick=()=>{const text=$("#master").value;platforms.forEach(p=>{$("#copy-"+p).value=text})};

async function api(path,opts={}){const res=await fetch(path,{headers:{"content-type":"application/json",...(opts.headers||{})},...opts});const data=await res.json();if(!res.ok)throw new Error(data.error||"Request failed");return data}

async function loadHealth(){try{await api("/api/health");$("#health").textContent="Engine online";$("#health").style.color="var(--ok)"}catch{$("#health").textContent="Engine offline";$("#health").style.color="var(--danger)"}}

async function loadOverview(){const o=await api("/api/overview");const stats=[["Posts today",o.posts_today],["Scheduled",o.scheduled],["Published",o.published],["Failed / partial",o.failed],["Open replies",o.open_responses],["Connections",o.connected_platforms]];$("#stats").innerHTML=stats.map(([l,v])=>`<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");const posts=await api("/api/posts?status=scheduled");renderPosts($("#upcoming"),posts.posts.slice(0,5));const inbox=await api("/api/inbox");renderThreads($("#dashboard-inbox"),inbox.threads.slice(0,5))}

function renderPosts(root,posts){if(!posts.length){root.innerHTML="No scheduled posts yet.";root.className="stack empty-state";return}root.className="stack";root.innerHTML=posts.map(p=>`<div class="item"><div class="item-main"><strong>${esc(p.title||p.master_text)}</strong><small>${p.scheduled_at?new Date(p.scheduled_at).toLocaleString():"Unscheduled"} · ${p.variants.map(v=>labels[v.platform]||v.platform).join(", ")}</small></div><span class="pill">${p.status}</span></div>`).join("")}

function renderThreads(root,threads){if(!threads.length){root.innerHTML="No open conversations.";root.className="stack empty-state";return}root.className="stack";root.innerHTML=threads.map(t=>{const last=t.messages[t.messages.length-1];return `<div class="item"><div class="item-main"><strong>${esc(t.participant_ref||t.subject||"Conversation")}</strong><small>${labels[t.platform]||t.platform} · ${last?esc(last.body):"No messages"}</small></div><span class="pill">open</span></div>`}).join("")}

async function loadSchedule(){const data=await api("/api/posts?status=scheduled");renderPosts($("#schedule-list"),data.posts)}
async function loadInbox(){const data=await api("/api/inbox");renderThreads($("#inbox-list"),data.threads)}

async function loadConnections(){const data=await api("/api/connections");const by=Object.fromEntries(data.connections.map(c=>[c.platform,c]));$("#connection-grid").innerHTML=["instagram","facebook","linkedin","x","youtube"].map(p=>{const c=by[p];return `<div class="connection ${c&&c.status==="connected"?"connected":""}"><strong>${labels[p]||"YouTube"}</strong><small>${c?esc(c.account_label||c.external_account_id):"Not connected"}</small><div class="state">${c?c.status:"Setup required"}</div></div>`}).join("")}

$("#create-form").onsubmit=async e=>{e.preventDefault();const variants=platforms.filter(p=>$("#use-"+p).checked).map(p=>({platform:p,body:$("#copy-"+p).value.trim()||$("#master").value.trim()}));if(!variants.length){$("#form-message").textContent="Select at least one platform.";return}let scheduled=$("#scheduled-at").value;scheduled=scheduled?new Date(scheduled).toISOString():null;try{const result=await api("/api/posts",{method:"POST",body:JSON.stringify({title:$("#title").value,master_text:$("#master").value,kind:$("#kind").value,scheduled_at:scheduled,variants})});$("#form-message").textContent=result.status==="scheduled"?"Added to schedule.":"Draft saved.";e.target.reset();platformRows();await loadOverview()}catch(err){$("#form-message").textContent=err.message}}

function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
loadHealth();loadOverview();
