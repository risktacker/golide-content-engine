const labels = {
  instagram: "Instagram",
  facebook: "Facebook",
  linkedin: "LinkedIn",
  x: "X",
  youtube: "YouTube",
};

const routes = {
  post: ["instagram", "facebook", "linkedin", "x"],
  short: ["instagram", "facebook", "youtube"],
  long: ["youtube"],
};

const routeText = {
  post: "Post: IG + FB + LinkedIn + X",
  short: "Short: IG + FB + YouTube Shorts",
  long: "Long: YouTube only",
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

let policy = null;
let r2Ready = false;
let uploadCount = 0;
let mediaRefs = { meta: null, square: null, voice: null, video: null };

function switchView(name) {
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === name));
  $$(".nav").forEach((v) => v.classList.toggle("active", v.dataset.view === name));
  $("#view-title").textContent = name[0].toUpperCase() + name.slice(1);
  if (name === "schedule") loadSchedule();
  if (name === "inbox") loadInbox();
  if (name === "connections") loadConnections();
}

$$(".nav").forEach((b) => (b.onclick = () => switchView(b.dataset.view)));
$$("[data-open-create]").forEach((b) => (b.onclick = () => switchView("create")));

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "content-type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function currentClass() {
  return $("#content-class").value;
}

function valueUnits() {
  return [1, 2, 3, 4]
    .map((n) => $("#unit-" + n).value.trim())
    .filter(Boolean);
}

function platformRows() {
  const klass = currentClass();
  $("#route-chip").textContent = routeText[klass];
  const root = $("#platforms");
  root.innerHTML = routes[klass]
    .map((p) => {
      const youtubeTitle = p === "youtube"
        ? '<label class="mini-label">YouTube title<input id="title-' + p + '" placeholder="Platform title"></label>'
        : "";
      return '<div class="platform-row">' +
        '<div class="platform-top"><span class="route-dot"></span><strong>' + labels[p] + '</strong><small>locked route</small></div>' +
        youtubeTitle +
        '<label class="mini-label">Platform framing / copy<textarea id="copy-' + p + '" placeholder="Leave blank to use the locked value sequence"></textarea></label>' +
        '</div>';
    }).join("");
}

function syncProductContext() {
  const mode = $("#product-mode").value;
  const product = $("#product-id");
  const bridge = $("#bridge-position");
  const url = $("#product-url");
  const status = $("#product-context-status");
  const products = policy?.product_registry?.products || [];

  product.disabled = mode !== "specific_product";
  if (mode === "brand") {
    product.value = "";
    bridge.value = "";
    bridge.disabled = true;
    url.value = "";
    status.textContent = "Brand mode keeps this static post non-product-centered.";
    return;
  }

  bridge.disabled = false;
  if (mode === "auto_product") {
    product.value = "";
    url.value = "";
    status.textContent = "Auto Product favors new and under-covered products while keeping mature products in rotation.";
    return;
  }

  if (!product.value && products.length) product.value = products[0].id;
  const selected = products.find((item) => item.id === product.value);
  url.value = selected?.marketplace_url || "";
  status.textContent = selected
    ? selected.name + " · " + selected.lifecycle_status + " · priority " + selected.priority
    : "Choose a registered product.";
}

function renderProductRegistry() {
  const products = policy?.product_registry?.products || [];
  const select = $("#product-id");
  const current = select.value;
  select.innerHTML = '<option value="">Auto selects from registry</option>' +
    products.map((item) => '<option value="' + escAttr(item.id) + '">' +
      esc(item.name) + " · " + esc(item.lifecycle_status) + "</option>").join("");
  if (products.some((item) => item.id === current)) select.value = current;
  syncProductContext();
}

function classChanged() {
  const isPost = currentClass() === "post";
  $("#post-fields").hidden = !isPost;
  $("#video-fields").hidden = isPost;
  $("#media-approved").closest("label").hidden = !isPost;
  $("#qa-approved").closest("label").hidden = isPost;
  platformRows();
  if (isPost) syncProductContext();
}

$("#content-class").onchange = classChanged;
$("#product-mode").onchange = syncProductContext;
$("#product-id").onchange = syncProductContext;

$("#fill-platforms").onclick = () => {
  const klass = currentClass();
  if (klass === "post") {
    const parts = valueUnits();
    const text = parts.join("\n\n");
    routes[klass].forEach((p) => {
      const box = $("#copy-" + p);
      if (box) box.value = text;
    });
    if (!$("#master").value.trim()) $("#master").value = text;
  } else {
    const text = $("#master").value.trim();
    routes[klass].forEach((p) => {
      const box = $("#copy-" + p);
      if (box) box.value = text;
    });
  }
};

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
    renderCadence();
    renderProductRegistry();
  } catch {
    policy = null;
  }
}

async function loadOverview() {
  const o = await api("/api/overview");
  r2Ready = Boolean(o.r2_ready);
  const stats = [
    ["Posts today", o.posts_today],
    ["Draft posts", o.draft_posts],
    ["Draft Shorts", o.draft_shorts],
    ["Draft long", o.draft_longs],
    ["Scheduled", o.scheduled],
    ["Failed / partial", o.failed],
  ];
  $("#stats").innerHTML = stats
    .map(([l, v]) => '<div class="stat"><b>' + v + '</b><span>' + l + '</span></div>')
    .join("");

  const posts = await api("/api/posts?status=scheduled");
  renderPosts($("#upcoming"), posts.posts.slice(0, 6));
  const inbox = await api("/api/inbox");
  renderThreads($("#dashboard-inbox"), inbox.threads.slice(0, 5));
}

function renderPosts(root, posts) {
  if (!posts.length) {
    root.innerHTML = "No scheduled content yet.";
    root.className = "stack empty-state";
    return;
  }
  root.className = "stack";
  root.innerHTML = posts.map((p) => {
    const platforms = p.variants.map((v) => labels[v.platform] || v.platform).join(", ");
    const when = p.scheduled_at ? new Date(p.scheduled_at).toLocaleString() : "Unscheduled";
    return '<div class="item"><div class="item-main"><strong>' +
      esc(p.title || p.master_text) +
      '</strong><small>' + esc(p.content_class.toUpperCase()) + ' · ' + esc(when) + ' · ' + esc(platforms) +
      '</small></div><span class="pill">' + esc(p.status) + '</span></div>';
  }).join("");
}

function renderThreads(root, threads) {
  if (!threads.length) {
    root.innerHTML = "No open conversations.";
    root.className = "stack empty-state";
    return;
  }
  root.className = "stack";
  root.innerHTML = threads.map((t) => {
    const last = t.messages[t.messages.length - 1];
    return '<div class="item"><div class="item-main"><strong>' +
      esc(t.participant_ref || t.subject || "Conversation") +
      '</strong><small>' + esc(labels[t.platform] || t.platform) + ' · ' +
      (last ? esc(last.body) : "No messages") +
      '</small></div><span class="pill">open</span></div>';
  }).join("");
}

function renderCadence() {
  if (!policy) return;
  const cal = policy.calendar;
  const days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"];
  const shorts = Object.fromEntries(cal.shorts.map((x) => [x.day, x.time]));
  const longs = Object.fromEntries(cal.long_videos.map((x) => [x.day, x.time]));
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

async function loadSchedule() {
  const data = await api("/api/posts?status=scheduled");
  renderPosts($("#schedule-list"), data.posts);
  if (!policy) await loadPolicy();
  renderCadence();
}

async function loadInbox() {
  const data = await api("/api/inbox");
  renderThreads($("#inbox-list"), data.threads);
}

async function loadConnections() {
  const data = await api("/api/connections");
  const by = Object.fromEntries(data.connections.map((c) => [c.platform, c]));
  $("#connection-grid").innerHTML = ["instagram", "facebook", "linkedin", "x", "youtube"]
    .map((p) => {
      const c = by[p];
      return '<div class="connection ' + (c && c.status === "connected" ? "connected" : "") + '">' +
        '<strong>' + labels[p] + '</strong>' +
        '<small>' + (c ? esc(c.account_label || c.external_account_id) : "Not connected") + '</small>' +
        '<div class="state">' + (c ? esc(c.status) : "Setup required") + '</div></div>';
    }).join("");
}

function mediaKind(file) {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  return "render_asset";
}

async function uploadFile(file, statusText) {
  if (!file) return null;
  if (!r2Ready) throw new Error("Temporary R2 storage is not configured.");
  uploadCount += 1;
  setBusy(true);
  if (statusText) statusText.textContent = "Uploading " + file.name + "...";
  try {
    const prepared = await api("/api/media/prepare", {
      method: "POST",
      body: JSON.stringify({ filename: file.name, media_kind: mediaKind(file) }),
    });
    const uploaded = await fetch(prepared.upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
    if (!uploaded.ok) throw new Error("Temporary upload failed (" + uploaded.status + ")");
    if (statusText) statusText.textContent = "Ready: " + file.name;
    return prepared.media_ref;
  } finally {
    uploadCount -= 1;
    setBusy(uploadCount > 0);
  }
}

$("#meta-image-file").onchange = async (e) => {
  try { mediaRefs.meta = await uploadFile(e.target.files[0], $("#image-generation-status")); }
  catch (err) { $("#image-generation-status").textContent = err.message; }
};
$("#square-image-file").onchange = async (e) => {
  try { mediaRefs.square = await uploadFile(e.target.files[0], $("#image-generation-status")); }
  catch (err) { $("#image-generation-status").textContent = err.message; }
};
$("#owner-voice-file").onchange = async (e) => {
  try { mediaRefs.voice = await uploadFile(e.target.files[0], $("#video-status")); }
  catch (err) { $("#video-status").textContent = err.message; }
};
$("#final-video-file").onchange = async (e) => {
  try { mediaRefs.video = await uploadFile(e.target.files[0], $("#video-status")); }
  catch (err) { $("#video-status").textContent = err.message; }
};

$("#generate-image").onclick = async () => {
  const status = $("#image-generation-status");
  status.textContent = "Generating one paid master and adapting it...";
  setBusy(true);
  try {
    const result = await api("/api/social-image/generate", {
      method: "POST",
      body: JSON.stringify({
        hook: $("#image-hook").value,
        concept: $("#image-concept").value,
        context: $("#master").value || valueUnits().join(" "),
      }),
    });
    mediaRefs.meta = result.meta_4x5.media_ref;
    mediaRefs.square = result.square_1x1.media_ref;
    $("#image-previews").innerHTML =
      '<figure><img src="' + escAttr(result.meta_4x5.preview_url) + '" alt="Meta 4:5 preview"><figcaption>Meta 4:5</figcaption></figure>' +
      '<figure><img src="' + escAttr(result.square_1x1.preview_url) + '" alt="LinkedIn and X square preview"><figcaption>LinkedIn / X 1:1</figcaption></figure>';
    status.textContent = "Generated. Review both crops, then tick Static image approved.";
  } catch (err) {
    status.textContent = err.message;
  } finally {
    setBusy(false);
  }
};

function setBusy(busy) {
  const button = $("#create-form button[type=submit]");
  button.disabled = busy;
  button.textContent = busy ? "Working..." : "Save to queue";
}

$("#create-form").onsubmit = async (e) => {
  e.preventDefault();
  if (uploadCount > 0) {
    $("#form-message").textContent = "Wait for temporary media uploads to finish.";
    return;
  }

  const klass = currentClass();
  const units = klass === "post" ? valueUnits() : [];
  const bridge = $("#bridge-position").value || null;
  const route = routes[klass];

  const variants = route.map((p) => {
    let mediaRef = null;
    if (klass === "post") {
      mediaRef = ["instagram", "facebook"].includes(p) ? mediaRefs.meta : mediaRefs.square;
    } else {
      mediaRef = mediaRefs.video;
    }
    const copy = $("#copy-" + p);
    const title = $("#title-" + p);
    return {
      platform: p,
      title: title ? title.value.trim() : "",
      body: copy ? copy.value.trim() : "",
      media_ref: mediaRef,
    };
  });

  let scheduled = $("#scheduled-at").value;
  scheduled = scheduled ? new Date(scheduled).toISOString() : null;

  try {
    const result = await api("/api/posts", {
      method: "POST",
      body: JSON.stringify({
        content_class: klass,
        content_lane: $("#content-lane").value,
        weekly_theme: $("#weekly-theme").value,
        title: $("#title").value,
        master_text: $("#master").value,
        value_units: units,
        product_bridge_position: bridge,
        product_url: klass === "post" ? $("#product-url").value : "",
        product_mode: klass === "post" ? $("#product-mode").value : "brand",
        product_id: klass === "post" && $("#product-mode").value === "specific_product" ? $("#product-id").value : "",
        selection_seed: [
          $("#weekly-theme").value,
          $("#title").value,
          units.join("|"),
          scheduled || "",
        ].join("::"),
        owner_voice_media_ref: klass === "post" ? null : mediaRefs.voice,
        media_approved: $("#media-approved").checked,
        qa_approved: $("#qa-approved").checked,
        release_approved: $("#release-approved").checked,
        scheduled_at: scheduled,
        variants,
      }),
    });

    const productNote = result.product_name ? " Product: " + result.product_name + "." : "";
    $("#form-message").textContent =
      (result.status === "scheduled" ? "Added to locked schedule." : "Draft saved.") + productNote;
    e.target.reset();
    mediaRefs = { meta: null, square: null, voice: null, video: null };
    $("#image-previews").innerHTML = "";
    $("#image-generation-status").textContent = "Generation remains behind the paid-production lock.";
    $("#video-status").textContent = "Product-independent business content. Topic selection follows strong current niche demand. AI or cloned narration is not allowed; owner recording is the master timeline.";
    $("#product-mode").value = "auto_product";
    classChanged();
    await loadOverview();
  } catch (err) {
    $("#form-message").textContent = err.message;
  }
};

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[c]));
}

function escAttr(v) {
  return esc(v).replace(/\n/g, "");
}

classChanged();
loadHealth();
loadPolicy();
loadOverview();
