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
let automationControl = null;
let automationBusy = false;

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

const VIEWS = ["dashboard", "create", "schedule", "inbox", "connections"];

function switchView(name) {
  if (!VIEWS.includes(name)) name = "dashboard";
  // Keep the current page in the address bar so a refresh lands back here.
  if (!window.location.hash.startsWith("#job-") && window.location.hash !== "#" + name) {
    window.history.replaceState({}, "", window.location.pathname + window.location.search + "#" + name);
  }
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

function renderAutomationControl() {
  const enabled = Boolean(automationControl?.enabled);
  const panel = $("#automation-control");
  const button = $("#automation-toggle");
  if (panel) {
    panel.classList.toggle("running", enabled);
    panel.classList.toggle("paused", !enabled);
  }
  if ($("#automation-control-title")) {
    $("#automation-control-title").textContent = enabled ? "Automation running" : "Automation paused";
  }
  if ($("#automation-control-copy")) {
    $("#automation-control-copy").textContent = enabled
      ? "The engine is armed. It will generate and resume work only at the locked schedule windows."
      : "Deployment is safe: scheduled runners can wake, but paid generation and publishing stay blocked until you start automation.";
  }
  if ($("#automation-control-meta")) {
    const stamp = automationControl?.updated_at
      ? new Date(automationControl.updated_at).toLocaleString()
      : "not changed yet";
    $("#automation-control-meta").textContent = enabled
      ? "Started " + stamp + ". Pause blocks new automated work."
      : "Paused " + stamp + ". Existing Studio data and schedules are preserved.";
  }
  if (button) {
    button.disabled = automationBusy;
    button.textContent = automationBusy
      ? "Updating..."
      : (enabled ? "Pause automation" : "Start automation");
  }
  if ($("#autopilot-label")) {
    $("#autopilot-label").textContent = enabled ? "Automation running" : "Automation paused";
  }
  if ($("#autopilot-state")) {
    $("#autopilot-state").classList.toggle("running", enabled);
    $("#autopilot-state").classList.toggle("paused", !enabled);
  }
}

async function loadAutomationControl() {
  try {
    automationControl = await api("/api/automation-control");
  } catch {
    automationControl = { enabled: false, state: "paused" };
  }
  renderAutomationControl();
}

async function toggleAutomation() {
  if (automationBusy) return;
  automationBusy = true;
  renderAutomationControl();
  try {
    automationControl = await api("/api/automation-control", {
      method: "POST",
      body: JSON.stringify({ enabled: !Boolean(automationControl?.enabled) }),
    });
  } catch (error) {
    alert(error.message);
  } finally {
    automationBusy = false;
    renderAutomationControl();
  }
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

// Locked 2026-10-04: recordings outside these windows are refused before upload.
const RECORDING_WINDOWS = { short: [30, 90], long: [210, 300] };

function clock(seconds) {
  const whole = Math.round(seconds);
  return Math.floor(whole / 60) + ":" + String(whole % 60).padStart(2, "0");
}

function audioDuration(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      if (Number.isFinite(audio.duration) && audio.duration > 0) resolve(audio.duration);
      else reject(new Error("Could not read the length of this recording. Try exporting it as MP3 or M4A."));
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("This file could not be read as audio. Try exporting it as MP3 or M4A."));
    };
    audio.src = url;
  });
}

function recordingLengthProblem(format, seconds) {
  const key = format === "long" ? "long" : "short";
  const [low, high] = RECORDING_WINDOWS[key];
  const label = key === "long" ? "Long video" : "Short";
  seconds = Math.round(seconds);
  if (seconds < low) return label + " recording is " + clock(seconds) + ", too short. Allowed: " + clock(low) + " to " + clock(high) + ". Please re-record and upload again.";
  if (seconds > high) return label + " recording is " + clock(seconds) + ", too long. Allowed: " + clock(low) + " to " + clock(high) + ". Please re-record and upload again.";
  return "";
}

function actionCard(job) {
  const script = job.script || "The engine is finishing the approved script.";
  const windowRange = RECORDING_WINDOWS[job.format === "long" ? "long" : "short"];
  const rejected = job.stage === "recording-rejected" && job.error
    ? '<p class="voice-rejected">Last upload was rejected: ' + esc(job.error) + '</p>'
    : "";
  return '<article class="action-card" id="job-' + escAttr(job.job_id) + '"><div><span class="kicker gold">VOICE NEEDED · ' +
    esc(String(job.format || "video").toUpperCase()) + '</span><h4>' +
    esc(job.title || "Script ready") + '</h4><p>The topic was selected from current demand and researched by the engine. Record this script in your own voice (' + clock(windowRange[0]) + ' to ' + clock(windowRange[1]) + '); the pipeline resumes automatically after upload.</p>' + rejected +
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
    input.onchange = () => {
      uploadVoice(input.dataset.job, input.files?.[0]);
      input.value = "";
    };
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
  const job = productionJobs.find((item) => item.job_id === jobId);
  try {
    if (status) status.textContent = "Checking length...";
    const seconds = await audioDuration(file);
    const problem = recordingLengthProblem(job?.format, seconds);
    if (problem) {
      if (status) status.textContent = problem;
      alert(problem);
      return;
    }
  } catch (error) {
    if (status) status.textContent = error.message;
    alert(error.message);
    return;
  }
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
    const item = byPlatform[platform] || {};
    const connected = Boolean(item.connected || item.status === "connected");
    const configured = Boolean(item.configured);
    const stateClass = connected ? "connected" : "attention";
    const state = connected ? "Connected" : (configured ? "Ready to connect" : "App credentials needed");
    const account = item.account_label || item.external_account_id || "";
    const detail = account || (configured
      ? "Authorize this account directly from Studio"
      : "Add this provider's OAuth Client ID and Secret to Studio");
    const verified = item.synced_at
      ? "Verified " + new Date(item.synced_at).toLocaleString()
      : (configured ? "Not connected yet" : "OAuth app not configured");
    const action = configured
      ? '<a class="connection-action" href="/api/' + platform + '/connect">' +
        (connected ? "Reconnect " : "Connect ") + esc(labels[platform]) + "</a>"
      : "";

    return '<div class="connection ' + stateClass + '"><strong>' +
      esc(labels[platform]) + '</strong><small>' + esc(detail) +
      '</small><small class="verified-at">' + esc(verified) +
      '</small><div class="state">' + esc(state) + '</div>' + action + '</div>';
  }).join("");
}

$("#refresh-jobs").onclick = loadProductionJobs;
$("#automation-toggle").onclick = toggleAutomation;

async function boot() {
  // Restore the page before any data loads, so refresh and OAuth returns are instant.
  const earlyParams = new URLSearchParams(window.location.search);
  const startHash = window.location.hash.slice(1);
  if (earlyParams.get("provider") || earlyParams.get("oauth") || earlyParams.get("x")) {
    switchView("connections");
  } else if (VIEWS.includes(startHash)) {
    switchView(startHash);
  }
  await Promise.all([loadHealth(), loadPolicy(), loadAutomationControl()]);
  await Promise.all([loadOverview(), loadProductionJobs(), loadConnections()]);
  renderBudget();

  // Links from the "record needed" email land on the exact job card.
  if (window.location.hash.startsWith("#job-")) {
    switchView("create");
    await loadProductionJobs();
    const card = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    if (card) card.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const params = new URLSearchParams(window.location.search);
  const legacyX = params.get("x");
  const provider = params.get("provider") || (legacyX ? "x" : "");
  const oauthResult = params.get("oauth") || legacyX;
  if (provider && oauthResult) {
    switchView("connections");
    const health = $("#health");
    const name = labels[provider] || pretty(provider);
    if (oauthResult === "connected") { health.textContent = name + " connected"; health.style.color = "var(--ok)"; }
    else if (oauthResult === "cancelled") { health.textContent = name + " authorization cancelled"; health.style.color = "var(--gold)"; }
    else if (oauthResult === "expired") { health.textContent = name + " authorization expired — connect again"; health.style.color = "var(--gold)"; }
    else { health.textContent = name + " authorization failed — reconnect"; health.style.color = "var(--danger)"; }
    window.history.replaceState({}, "", window.location.pathname + "#connections");
    await loadConnections();
  }
}

boot();
