const labels = {
  instagram: "Instagram",
  facebook: "Facebook",
  linkedin: "LinkedIn",
  x: "X",
  youtube: "YouTube",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

let policy = null;
let overview = null;
let productionJobs = [];
let r2Ready = false;
let uploadCount = 0;

async function api(path, opts = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[char]));
}

function escAttr(value) {
  return esc(value).replace(/\n/g, "");
}

function pretty(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function money(value) {
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(Number(value || 0));
}

function switchView(name) {
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === name));
  $$(".nav").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  const titles = {
    dashboard: "Dashboard",
    create: "Automation",
    schedule: "Schedule",
    inbox: "Inbox",
    connections: "Connections",
  };
  $("#view-title").textContent = titles[name] || pretty(name);
  if (name === "create") loadProductionJobs();
  if (name === "schedule") loadSchedule();
  if (name === "inbox") loadInbox();
  if (name === "connections") loadConnections();
}

$$(".nav").forEach((button) => {
  button.onclick = () => switchView(button.dataset.view);
});
$$("[data-open-automation]").forEach((button) => {
  button.onclick = () => switchView("create");
});
$$("[data-view-link]").forEach((link) => {
  link.onclick = (event) => {
    event.preventDefault();
    switchView(link.dataset.viewLink);
  };
});

async function loadHealth() {
  try {
    await api("/api/health");
    $("#health").textContent = "Engine online";
    $("#health").style.color = "var(--ok)";
  } catch {
    $("#health").textContent = "Engine offline";
    $("#health").style.color = "var(--danger)";
  }
}

async function loadPolicy() {
  try {
    policy = await api("/api/policy");
  } catch {
    policy = null;
  }
  renderCadence();
}

async function loadOverview() {
  overview = await api("/api/overview");
  r2Ready = Boolean(overview.r2_ready);

  const stats = [
    ["Waiting on you", overview.waiting_voice],
    ["Engine running", overview.production_running],
    ["Scheduled", overview.scheduled],
    ["Published", overview.published],
    ["Failed / partial", overview.failed],
    ["Temp media", overview.temporary_media],
  ];
  $("#stats").innerHTML = stats.map(([label, value]) =>
    '<div class="stat"><b>' + esc(value) + '</b><span>' + esc(label) + '</span></div>'
  ).join("");

  const scheduled = await api("/api/posts?status=scheduled");
  renderPosts($("#upcoming"), scheduled.posts.slice(0, 6));

  renderBudget();
}

function renderBudget() {
  if (!overview) return;
  const budget = policy?.budget || {
    openai_deposit_target_usd: 10,
    scheduled_video_guard_usd: 7,
    static_post_guard_usd: 3,
    x_opening_credit_usd: 5,
  };
  const video = Number(overview.video_openai_spend_usd || 0);
  const staticEstimate = Number(overview.static_openai_estimate_usd || 0);
  const cards = [
    [money(budget.openai_deposit_target_usd), "OpenAI API opening balance", "One prepaid API balance"],
    [money(video), "Video API spend this month", "Guard: " + money(budget.scheduled_video_guard_usd)],
    [money(staticEstimate), "Static estimate this month", "Guard: " + money(budget.static_post_guard_usd)],
    [money(budget.x_opening_credit_usd), "X opening credits", "Separate pay-per-use balance"],
  ];
  $("#budget-strip").innerHTML = cards.map(([amount, label, note]) =>
    '<div class="budget-card"><strong>' + esc(amount) + '</strong><span>' +
    esc(label) + '</span><small>' + esc(note) + '</small></div>'
  ).join("");
}

function renderPosts(root, posts) {
  if (!posts.length) {
    root.innerHTML = "No scheduled content yet.";
    root.className = "stack empty-state";
    return;
  }
  root.className = "stack";
  root.innerHTML = posts.map((post) => {
    const platforms = (post.variants || []).map((variant) => labels[variant.platform] || variant.platform).join(", ");
    const when = post.scheduled_at ? new Date(post.scheduled_at).toLocaleString() : "Unscheduled";
    return '<div class="item"><div class="item-main"><strong>' +
      esc(post.title || post.master_text || "Scheduled content") +
      '</strong><small>' + esc(String(post.content_class || "").toUpperCase()) +
      " · " + esc(when) + " · " + esc(platforms) +
      '</small></div><span class="pill">' + esc(post.status) + '</span></div>';
  }).join("");
}

function renderThreads(root, threads) {
  if (!threads.length) {
    root.innerHTML = "No open conversations.";
    root.className = "stack empty-state";
    return;
  }
  root.className = "stack";
  root.innerHTML = threads.map((thread) => {
    const last = thread.messages?.[thread.messages.length - 1];
    return '<div class="item"><div class="item-main"><strong>' +
      esc(thread.participant_ref || thread.subject || "Conversation") +
      '</strong><small>' + esc(labels[thread.platform] || thread.platform) +
      " · " + (last ? esc(last.body) : "No messages") +
      '</small></div><span class="pill">open</span></div>';
  }).join("");
}

function renderCadence() {
  if (!policy?.calendar) return;
  const calendar = policy.calendar;
  const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  const shorts = Object.fromEntries(calendar.shorts.map((item) => [item.day, item.time]));
  const longs = Object.fromEntries(calendar.long_videos.map((item) => [item.day, item.time]));
  $("#cadence-grid").innerHTML =
    '<div class="cadence-head"><span>Day</span><span>08:30</span><span>13:00</span><span>17:30</span><span>19:30</span></div>' +
    days.map((day) =>
      '<div class="cadence-row"><strong>' + day[0].toUpperCase() + day.slice(1) + '</strong>' +
      '<span class="slot post">Post A</span>' +
      '<span class="slot ' + (shorts[day] ? "short" : "") + '">' + (shorts[day] ? "Short" : "") + '</span>' +
      '<span class="slot post">Post B</span>' +
      '<span class="slot ' + (longs[day] ? "long" : "") + '">' + (longs[day] ? "Long" : "") + '</span></div>'
    ).join("");
}

function stageProgress(job) {
  const stage = String(job.stage || "").toLowerCase();
  const status = String(job.status || "").toLowerCase();
  if (["scheduled", "completed", "release_ready"].includes(status)) return 5;
  if (stage.includes("release") || stage.includes("qa") || stage.includes("upload")) return 5;
  if (stage.includes("render") || stage.includes("storyboard") || stage.includes("asset") || stage.includes("thumbnail")) return 4;
  if (status === "waiting_owner_voice" || stage.includes("script")) return 3;
  if (stage.includes("research") || stage.includes("trend") || stage.includes("demand")) return 2;
  if (status === "claimed" || status === "running") return 1;
  return 0;
}

function stageBars(job) {
  const progress = stageProgress(job);
  return '<div class="stage-track">' +
    [1, 2, 3, 4, 5].map((step) =>
      '<span class="stage-node ' + (step < progress ? "done" : step === progress ? "current" : "") + '"></span>'
    ).join("") + '</div>';
}

function jobSecondary(job) {
  const pieces = [];
  if (job.format) pieces.push(String(job.format).toUpperCase());
  if (job.stage) pieces.push(pretty(job.stage));
  if (job.scheduled_at) pieces.push(new Date(job.scheduled_at).toLocaleString());
  return pieces.join(" · ");
}

function renderJobList() {
  const root = $("#job-list");
  if (!productionJobs.length) {
    root.className = "job-list empty-state";
    root.innerHTML = "No production jobs yet. Scheduled automation will populate this pipeline.";
    return;
  }
  root.className = "job-list";
  root.innerHTML = productionJobs.map((job) => {
    const retry = ["failed", "paused_funds"].includes(job.status)
      ? '<button class="ghost retry-job" data-job="' + escAttr(job.job_id) + '">Retry</button>'
      : "";
    return '<div class="job-card"><div class="job-title"><strong>' +
      esc(job.title || "Engine planning job") + '</strong><small>' +
      esc(jobSecondary(job)) + '</small></div>' +
      stageBars(job) +
      '<div><span class="status-pill ' + escAttr(job.status) + '">' +
      esc(pretty(job.status)) + '</span>' + retry + '</div></div>';
  }).join("");

  $$(".retry-job").forEach((button) => {
    button.onclick = () => retryJob(button.dataset.job);
  });
}

function actionCard(job) {
  const script = job.script || "The engine is finishing the approved script.";
  return '<article class="action-card"><div><span class="kicker gold">VOICE NEEDED · ' +
    esc(String(job.format || "video").toUpperCase()) + '</span><h4>' +
    esc(job.title || "Script ready") + '</h4><p>The topic was selected from current demand and researched by the engine. Record this approved script in your own voice; the pipeline resumes automatically after upload.</p>' +
    '<div class="script-box">' + esc(script) + '</div></div>' +
    '<div class="action-controls">' +
      '<label class="upload-button">Upload my recording<input class="voice-input" type="file" accept="audio/*" data-job="' + escAttr(job.job_id) + '"></label>' +
      '<button class="action-button copy-script" data-job="' + escAttr(job.job_id) + '">Copy script</button>' +
      '<span class="voice-status" id="voice-status-' + escAttr(job.job_id) + '"></span>' +
    '</div></article>';
}

function renderActionQueues() {
  const waiting = productionJobs.filter((job) => job.status === "waiting_owner_voice");
  const root = $("#action-queue");
  const dashboard = $("#dashboard-actions");

  if (!waiting.length) {
    root.className = "action-queue empty-state";
    root.innerHTML = "No voice recordings required right now.";
    dashboard.className = "stack empty-state";
    dashboard.innerHTML = "Nothing needs you right now.";
    return;
  }

  root.className = "action-queue";
  root.innerHTML = waiting.map(actionCard).join("");
  dashboard.className = "stack";
  dashboard.innerHTML = waiting.slice(0, 4).map((job) =>
    '<div class="item"><div class="item-main"><strong>' +
    esc(job.title || "Video script ready") + '</strong><small>' +
    esc(String(job.format || "video").toUpperCase()) +
    ' · owner recording required</small></div><span class="pill">voice needed</span></div>'
  ).join("");

  $$(".voice-input").forEach((input) => {
    input.onchange = () => uploadVoice(input.dataset.job, input.files?.[0]);
  });
  $$(".copy-script").forEach((button) => {
    button.onclick = async () => {
      const job = productionJobs.find((item) => item.job_id === button.dataset.job);
      if (!job?.script) return;
      await navigator.clipboard.writeText(job.script);
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = "Copy script"; }, 1200);
    };
  });
}

async function prepareUpload(file) {
  if (!file) throw new Error("Choose an audio recording.");
  if (!r2Ready) throw new Error("Temporary R2 storage is not ready.");
  const prepared = await api("/api/media/prepare", {
    method: "POST",
    body: JSON.stringify({
      filename: file.name,
      media_kind: file.type.startsWith("audio/") ? "audio" : "render_asset",
    }),
  });
  const uploaded = await fetch(prepared.upload_url, {
    method: "PUT",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
  if (!uploaded.ok) throw new Error("Temporary upload failed (" + uploaded.status + ")");
  return prepared.media_ref;
}

async function uploadVoice(jobId, file) {
  if (!jobId || !file || uploadCount) return;
  const status = $("#voice-status-" + CSS.escape(jobId));
  uploadCount += 1;
  if (status) status.textContent = "Uploading " + file.name + "...";
  try {
    const mediaRef = await prepareUpload(file);
    await api("/api/production-jobs/" + encodeURIComponent(jobId) + "/voice", {
      method: "POST",
      body: JSON.stringify({ media_ref: mediaRef }),
    });
    if (status) status.textContent = "Uploaded. Engine will resume on the next cycle.";
    await loadProductionJobs();
    await loadOverview();
  } catch (error) {
    if (status) status.textContent = error.message;
  } finally {
    uploadCount -= 1;
  }
}

async function retryJob(jobId) {
  if (!jobId) return;
  try {
    await api("/api/production-jobs/" + encodeURIComponent(jobId) + "/retry", {
      method: "POST",
      body: "{}",
    });
    await loadProductionJobs();
  } catch (error) {
    alert(error.message);
  }
}

async function loadProductionJobs() {
  try {
    const data = await api("/api/production-jobs");
    productionJobs = data.jobs || [];
  } catch {
    productionJobs = [];
  }
  renderJobList();
  renderActionQueues();
}

async function loadSchedule() {
  const data = await api("/api/posts?status=scheduled");
  renderPosts($("#schedule-list"), data.posts || []);
  if (!policy) await loadPolicy();
  renderCadence();
}

async function loadInbox() {
  const data = await api("/api/inbox");
  renderThreads($("#inbox-list"), data.threads || []);
}

async function loadConnections() {
  let connections = [];
  try {
    const data = await api("/api/connections");
    connections = data.connections || [];
  } catch {
    connections = [];
  }
  const byPlatform = Object.fromEntries(connections.map((item) => [item.platform, item]));
  $("#connection-grid").innerHTML = ["instagram", "facebook", "linkedin", "x", "youtube"].map((platform) => {
    const connected = byPlatform[platform];
    const isX = platform === "x";
    const stateClass = connected ? "connected" : "pending";
    const state = connected ? "Connected" : (isX ? "Authorization pending" : "Awaiting engine sync");
    const detail = connected
      ? (connected.account_label || connected.external_account_id || "Verified route")
      : (isX ? "Finish OAuth user authorization" : "Existing credential will be reflected after engine sync");
    return '<div class="connection ' + stateClass + '"><strong>' +
      esc(labels[platform]) + '</strong><small>' + esc(detail) +
      '</small><div class="state">' + esc(state) + '</div></div>';
  }).join("");
}

$("#refresh-jobs").onclick = loadProductionJobs;

async function boot() {
  await Promise.all([loadHealth(), loadPolicy()]);
  await Promise.all([loadOverview(), loadProductionJobs(), loadConnections()]);
  renderBudget();
}

boot();
