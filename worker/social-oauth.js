// Studio-owned OAuth adapters for Instagram, Facebook, LinkedIn and YouTube.
// Provider user tokens are encrypted in D1 and are never written to GitHub secrets.

const STUDIO_BASE = "https://studio.golidee.com";
const META_API_VERSION = "v23.0";
const YOUTUBE_EXPECTED_CHANNEL_ID = "UCqaXVBSBz7iQsRHOupKt-3w";

const REDIRECTS = {
  instagram: STUDIO_BASE + "/api/oauth/instagram/callback",
  facebook: STUDIO_BASE + "/api/oauth/facebook/callback",
  linkedin: STUDIO_BASE + "/api/oauth/linkedin/callback",
  youtube: STUDIO_BASE + "/api/oauth/youtube/callback",
};

const INSTAGRAM_SCOPES = "instagram_business_basic,instagram_business_content_publish";
const FACEBOOK_SCOPES = "pages_show_list,pages_read_engagement,pages_manage_posts";
const LINKEDIN_SCOPES = "openid profile w_member_social";
const YOUTUBE_SCOPES = [
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube.readonly",
  "https://www.googleapis.com/auth/yt-analytics.readonly",
  "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
];

function text(value) { return String(value ?? "").trim(); }
function nowIso() { return new Date().toISOString(); }

function clientId(env, platform) {
  if (platform === "instagram") return text(env.INSTAGRAM_OAUTH_CLIENT_ID);
  if (platform === "facebook") return text(env.FACEBOOK_OAUTH_CLIENT_ID);
  if (platform === "linkedin") return text(env.LINKEDIN_OAUTH_CLIENT_ID);
  if (platform === "youtube") return text(env.GOOGLE_OAUTH_CLIENT_ID);
  return "";
}

function clientSecret(env, platform) {
  if (platform === "instagram") return text(env.INSTAGRAM_OAUTH_CLIENT_SECRET);
  if (platform === "facebook") return text(env.FACEBOOK_OAUTH_CLIENT_SECRET);
  if (platform === "linkedin") return text(env.LINKEDIN_OAUTH_CLIENT_SECRET);
  if (platform === "youtube") return text(env.GOOGLE_OAUTH_CLIENT_SECRET);
  return "";
}

export function socialOAuthConfigured(env, platform) {
  return Boolean(clientId(env, platform) && clientSecret(env, platform));
}

function b64(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function unb64(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, (ch) => ch.charCodeAt(0));
}

function randomUrlSafe(size = 32) {
  const bytes = new Uint8Array(size);
  crypto.getRandomValues(bytes);
  return b64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function tokenKey(env, platform) {
  const secret = clientSecret(env, platform);
  if (!secret) throw new Error(platform + " OAuth client secret is not configured");
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode("golide-social-token:" + platform + ":" + secret)
  );
  return crypto.subtle.importKey("raw", digest, {name:"AES-GCM"}, false, ["encrypt","decrypt"]);
}

async function seal(env, platform, value) {
  if (!text(value)) return "";
  const iv = new Uint8Array(12);
  crypto.getRandomValues(iv);
  const key = await tokenKey(env, platform);
  const encrypted = new Uint8Array(await crypto.subtle.encrypt(
    {name:"AES-GCM", iv}, key, new TextEncoder().encode(value)
  ));
  return b64(iv) + "." + b64(encrypted);
}

async function openToken(env, platform, value) {
  if (!text(value)) return "";
  const parts = text(value).split(".");
  if (parts.length !== 2) throw new Error("invalid encrypted " + platform + " token");
  const key = await tokenKey(env, platform);
  const clear = await crypto.subtle.decrypt(
    {name:"AES-GCM", iv:unb64(parts[0])}, key, unb64(parts[1])
  );
  return new TextDecoder().decode(clear);
}

export async function ensureSocialOauthSchema(db) {
  await db.prepare(
    "CREATE TABLE IF NOT EXISTS social_oauth_sessions (" +
    "state TEXT PRIMARY KEY, platform TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL)"
  ).run();
  await db.prepare(
    "CREATE TABLE IF NOT EXISTS social_oauth_tokens (" +
    "platform TEXT PRIMARY KEY, access_token_enc TEXT NOT NULL, refresh_token_enc TEXT NOT NULL DEFAULT '', " +
    "expires_at TEXT NOT NULL DEFAULT '', scope TEXT NOT NULL DEFAULT '', account_id TEXT NOT NULL DEFAULT '', " +
    "account_label TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL)"
  ).run();
  try {
    await db.prepare("ALTER TABLE social_oauth_tokens ADD COLUMN account_id TEXT NOT NULL DEFAULT ''").run();
  } catch {}
  try {
    await db.prepare(
      "UPDATE social_oauth_tokens SET account_id=external_account_id " +
      "WHERE account_id='' AND external_account_id<>''"
    ).run();
  } catch {}
}

async function createSession(env, platform) {
  const state = randomUrlSafe(32);
  const now = nowIso();
  const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();
  await env.DB.prepare("DELETE FROM social_oauth_sessions WHERE expires_at<?").bind(now).run();
  await env.DB.prepare(
    "INSERT INTO social_oauth_sessions(state,platform,expires_at,created_at) VALUES(?,?,?,?)"
  ).bind(state, platform, expiresAt, now).run();
  return state;
}

async function consumeSession(env, platform, state) {
  const row = await env.DB.prepare(
    "SELECT platform,expires_at FROM social_oauth_sessions WHERE state=?"
  ).bind(state).first();
  if (!row || text(row.platform) !== platform || new Date(row.expires_at).valueOf() <= Date.now()) return false;
  await env.DB.prepare("DELETE FROM social_oauth_sessions WHERE state=?").bind(state).run();
  return true;
}

function resultRedirect(platform, status) {
  const params = new URLSearchParams({provider:platform, oauth:status});
  return Response.redirect(STUDIO_BASE + "/?" + params.toString(), 302);
}

async function saveToken(env, platform, data) {
  const accessToken = text(data.accessToken);
  if (!accessToken) throw new Error(platform + " access token is empty");
  const refreshToken = text(data.refreshToken);
  const now = nowIso();

  await env.DB.prepare(
    "INSERT INTO social_oauth_tokens " +
    "(platform,access_token_enc,refresh_token_enc,expires_at,scope,account_id,account_label,metadata_json,updated_at) " +
    "VALUES(?,?,?,?,?,?,?,?,?) " +
    "ON CONFLICT(platform) DO UPDATE SET " +
    "access_token_enc=excluded.access_token_enc," +
    "refresh_token_enc=CASE WHEN excluded.refresh_token_enc<>'' THEN excluded.refresh_token_enc ELSE social_oauth_tokens.refresh_token_enc END," +
    "expires_at=excluded.expires_at,scope=excluded.scope,account_id=excluded.account_id," +
    "account_label=excluded.account_label,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at"
  ).bind(
    platform,
    await seal(env, platform, accessToken),
    refreshToken ? await seal(env, platform, refreshToken) : "",
    text(data.expiresAt),
    text(data.scope),
    text(data.accountId),
    text(data.accountLabel),
    JSON.stringify(data.metadata || {}),
    now
  ).run();

  await env.DB.prepare(
    "INSERT INTO engine_connections " +
    "(platform,connected,account_label,external_account_id,synced_at,verification_status,verification_note) " +
    "VALUES(?,1,?,?,?,'connected',?) " +
    "ON CONFLICT(platform) DO UPDATE SET connected=1,account_label=excluded.account_label," +
    "external_account_id=excluded.external_account_id,synced_at=excluded.synced_at," +
    "verification_status='connected',verification_note=excluded.verification_note"
  ).bind(
    platform, text(data.accountLabel), text(data.accountId), now,
    "Verified directly through Studio OAuth."
  ).run();
}

async function markReconnect(env, platform, note) {
  await env.DB.prepare(
    "INSERT INTO engine_connections " +
    "(platform,connected,account_label,external_account_id,synced_at,verification_status,verification_note) " +
    "VALUES(?,0,'','',?,'needs_attention',?) " +
    "ON CONFLICT(platform) DO UPDATE SET connected=0,synced_at=excluded.synced_at," +
    "verification_status='needs_attention',verification_note=excluded.verification_note"
  ).bind(platform, nowIso(), text(note).slice(0,300)).run();
}

export async function studioSocialConnectionRows(db, env) {
  await ensureSocialOauthSchema(db);
  const stored = (await db.prepare(
    "SELECT platform,expires_at,account_id,account_label,updated_at FROM social_oauth_tokens"
  ).all()).results || [];
  const rows = (await db.prepare(
    "SELECT platform,connected,account_label,external_account_id,synced_at,verification_status,verification_note " +
    "FROM engine_connections WHERE platform IN ('instagram','facebook','linkedin','youtube')"
  ).all()).results || [];
  const rowMap = new Map(rows.map((row) => [text(row.platform), row]));
  const tokenMap = new Map(stored.map((row) => [text(row.platform), row]));

  return ["instagram","facebook","linkedin","youtube"].map((platform) => {
    const token = tokenMap.get(platform);
    const row = rowMap.get(platform) || {};
    let connected = Boolean(token) && Number(row.connected) === 1;
    let note = text(row.verification_note);
    if (platform === "linkedin" && connected) {
      const expiry = new Date(token.expires_at || "").valueOf();
      if (Number.isFinite(expiry) && expiry <= Date.now()) {
        connected = false;
        note = "LinkedIn authorization expired. Reconnect from Studio.";
      }
    }
    return {
      id:platform,
      platform,
      configured:socialOAuthConfigured(env, platform),
      connected,
      account_label:connected ? text(token.account_label || row.account_label) : "",
      external_account_id:connected ? text(token.account_id || row.external_account_id) : "",
      transport:"studio_oauth",
      status:connected ? "connected" : "needs_attention",
      verification_note:note,
      synced_at:connected ? (row.synced_at || token.updated_at || null) : null,
    };
  });
}

export async function startSocialOauth(env, platform) {
  if (!["instagram","facebook","linkedin","youtube"].includes(platform)) {
    throw new Error("unsupported OAuth provider");
  }
  if (!socialOAuthConfigured(env, platform)) {
    throw new Error(platform + " OAuth app credentials are not configured in Studio");
  }

  await ensureSocialOauthSchema(env.DB);
  const state = await createSession(env, platform);
  const redirect = REDIRECTS[platform];

  if (platform === "instagram") {
    const params = new URLSearchParams({
      client_id:clientId(env,platform), redirect_uri:redirect, response_type:"code",
      scope:INSTAGRAM_SCOPES, state,
      enable_fb_login:"0",
      force_authentication:"1",
    });
    return "https://www.instagram.com/oauth/authorize?" + params.toString();
  }

  if (platform === "facebook") {
    const params = new URLSearchParams({
      client_id:clientId(env,platform), redirect_uri:redirect, response_type:"code",
      scope:FACEBOOK_SCOPES, state,
    });
    return "https://www.facebook.com/" + META_API_VERSION + "/dialog/oauth?" + params.toString();
  }

  if (platform === "linkedin") {
    const params = new URLSearchParams({
      response_type:"code", client_id:clientId(env,platform), redirect_uri:redirect,
      state, scope:LINKEDIN_SCOPES,
    });
    return "https://www.linkedin.com/oauth/v2/authorization?" + params.toString();
  }

  const params = new URLSearchParams({
    response_type:"code", client_id:clientId(env,platform), redirect_uri:redirect,
    scope:YOUTUBE_SCOPES.join(" "), access_type:"offline", include_granted_scopes:"true",
    prompt:"consent", state,
  });
  return "https://accounts.google.com/o/oauth2/v2/auth?" + params.toString();
}

async function instagramCallback(env, code) {
  const tokenResponse = await fetch("https://api.instagram.com/oauth/access_token", {
    method:"POST",
    headers:{"content-type":"application/x-www-form-urlencoded", accept:"application/json"},
    body:new URLSearchParams({
      client_id:clientId(env,"instagram"),
      client_secret:clientSecret(env,"instagram"),
      grant_type:"authorization_code",
      redirect_uri:REDIRECTS.instagram,
      code,
    }),
  });
  if (!tokenResponse.ok) throw new Error("Instagram authorization-code exchange failed");
  const shortToken = await tokenResponse.json();
  if (!text(shortToken.access_token)) throw new Error("Instagram did not return an access token");

  const longUrl = new URL("https://graph.instagram.com/access_token");
  longUrl.search = new URLSearchParams({
    grant_type:"ig_exchange_token",
    client_secret:clientSecret(env,"instagram"),
    access_token:text(shortToken.access_token),
  }).toString();
  const longResponse = await fetch(longUrl, {headers:{accept:"application/json"}});
  if (!longResponse.ok) throw new Error("Instagram long-lived token exchange failed");
  const longToken = await longResponse.json();
  const access = text(longToken.access_token);

  const meUrl = new URL("https://graph.instagram.com/" + META_API_VERSION + "/me");
  meUrl.search = new URLSearchParams({fields:"id,username", access_token:access}).toString();
  const meResponse = await fetch(meUrl, {headers:{accept:"application/json"}});
  if (!meResponse.ok) throw new Error("Instagram identity verification failed");
  const me = await meResponse.json();
  if (!text(me.id)) throw new Error("Instagram did not return an account id");

  const expiresIn = Math.max(3600, Number(longToken.expires_in || 5184000));
  await saveToken(env, "instagram", {
    accessToken:access,
    expiresAt:new Date(Date.now()+expiresIn*1000).toISOString(),
    scope:INSTAGRAM_SCOPES,
    accountId:text(me.id),
    accountLabel:text(me.username) ? "@" + text(me.username) : "Instagram",
    metadata:{graph_host:"graph.instagram.com",api_version:META_API_VERSION},
  });
}

async function facebookCallback(env, code) {
  const shortUrl = new URL("https://graph.facebook.com/" + META_API_VERSION + "/oauth/access_token");
  shortUrl.search = new URLSearchParams({
    client_id:clientId(env,"facebook"),
    client_secret:clientSecret(env,"facebook"),
    redirect_uri:REDIRECTS.facebook,
    code,
  }).toString();
  const shortResponse = await fetch(shortUrl, {headers:{accept:"application/json"}});
  if (!shortResponse.ok) throw new Error("Facebook authorization-code exchange failed");
  const short = await shortResponse.json();
  const shortAccess = text(short.access_token);
  if (!shortAccess) throw new Error("Facebook did not return an access token");

  const longUrl = new URL("https://graph.facebook.com/" + META_API_VERSION + "/oauth/access_token");
  longUrl.search = new URLSearchParams({
    grant_type:"fb_exchange_token",
    client_id:clientId(env,"facebook"),
    client_secret:clientSecret(env,"facebook"),
    fb_exchange_token:shortAccess,
  }).toString();
  const longResponse = await fetch(longUrl, {headers:{accept:"application/json"}});
  if (!longResponse.ok) throw new Error("Facebook long-lived token exchange failed");
  const long = await longResponse.json();
  const userAccess = text(long.access_token) || shortAccess;

  const pagesUrl = new URL("https://graph.facebook.com/" + META_API_VERSION + "/me/accounts");
  pagesUrl.search = new URLSearchParams({
    fields:"id,name,access_token,tasks",
    access_token:userAccess,
  }).toString();
  const pagesResponse = await fetch(pagesUrl, {headers:{accept:"application/json"}});
  if (!pagesResponse.ok) throw new Error("Facebook Page discovery failed");
  const usable = ((await pagesResponse.json())?.data || []).filter(
    (page) => text(page.id) && text(page.access_token)
  );
  if (!usable.length) throw new Error("No manageable Facebook Page was returned");

  let page = usable.find((item) => text(item.name).toLowerCase().includes("golide"));
  if (!page && usable.length === 1) page = usable[0];
  if (!page) throw new Error("Multiple Facebook Pages were returned and no GOLIDE Page was identifiable");

  const expiresIn = Math.max(3600, Number(long.expires_in || 5184000));
  await saveToken(env, "facebook", {
    accessToken:text(page.access_token),
    refreshToken:userAccess,
    expiresAt:new Date(Date.now()+expiresIn*1000).toISOString(),
    scope:FACEBOOK_SCOPES,
    accountId:text(page.id),
    accountLabel:text(page.name) || "Facebook Page",
    metadata:{api_version:META_API_VERSION,tasks:Array.isArray(page.tasks)?page.tasks:[]},
  });
}

async function linkedinCallback(env, code) {
  const response = await fetch("https://www.linkedin.com/oauth/v2/accessToken", {
    method:"POST",
    headers:{"content-type":"application/x-www-form-urlencoded", accept:"application/json"},
    body:new URLSearchParams({
      grant_type:"authorization_code",
      code,
      redirect_uri:REDIRECTS.linkedin,
      client_id:clientId(env,"linkedin"),
      client_secret:clientSecret(env,"linkedin"),
    }),
  });
  if (!response.ok) throw new Error("LinkedIn authorization-code exchange failed");
  const token = await response.json();
  const access = text(token.access_token);
  if (!access) throw new Error("LinkedIn did not return an access token");

  const meResponse = await fetch("https://api.linkedin.com/v2/userinfo", {
    headers:{authorization:"Bearer " + access, accept:"application/json"},
  });
  if (!meResponse.ok) throw new Error("LinkedIn identity verification failed");
  const me = await meResponse.json();
  const sub = text(me.sub);
  if (!sub) throw new Error("LinkedIn userinfo did not return a member id");

  const label = text(me.name) ||
    [text(me.given_name),text(me.family_name)].filter(Boolean).join(" ") ||
    "LinkedIn";
  const expiresIn = Math.max(300, Number(token.expires_in || 5184000));

  await saveToken(env, "linkedin", {
    accessToken:access,
    refreshToken:text(token.refresh_token),
    expiresAt:new Date(Date.now()+expiresIn*1000).toISOString(),
    scope:text(token.scope) || LINKEDIN_SCOPES,
    accountId:"urn:li:person:" + sub,
    accountLabel:label,
    metadata:{subject:sub},
  });
}

async function youtubeCallback(env, code) {
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method:"POST",
    headers:{"content-type":"application/x-www-form-urlencoded", accept:"application/json"},
    body:new URLSearchParams({
      code,
      client_id:clientId(env,"youtube"),
      client_secret:clientSecret(env,"youtube"),
      redirect_uri:REDIRECTS.youtube,
      grant_type:"authorization_code",
    }),
  });
  if (!response.ok) throw new Error("Google authorization-code exchange failed");
  const token = await response.json();
  const access = text(token.access_token);
  const refresh = text(token.refresh_token);
  if (!access || !refresh) throw new Error("Google did not return offline access");

  const channelResponse = await fetch(
    "https://www.googleapis.com/youtube/v3/channels?part=id%2Csnippet&mine=true",
    {headers:{authorization:"Bearer " + access, accept:"application/json"}}
  );
  if (!channelResponse.ok) throw new Error("YouTube channel verification failed");
  const items = (await channelResponse.json())?.items || [];
  if (items.length !== 1 || text(items[0]?.id) !== YOUTUBE_EXPECTED_CHANNEL_ID) {
    throw new Error("The authorized Google account does not own the GOLIDE YouTube channel");
  }

  const expiresIn = Math.max(300, Number(token.expires_in || 3600));
  await saveToken(env, "youtube", {
    accessToken:access,
    refreshToken:refresh,
    expiresAt:new Date(Date.now()+expiresIn*1000).toISOString(),
    scope:text(token.scope) || YOUTUBE_SCOPES.join(" "),
    accountId:YOUTUBE_EXPECTED_CHANNEL_ID,
    accountLabel:text(items[0]?.snippet?.title) || "GOLIDE YouTube",
    metadata:{channel_id:YOUTUBE_EXPECTED_CHANNEL_ID},
  });
}

export async function handleSocialOauthCallback(env, platform, url) {
  await ensureSocialOauthSchema(env.DB);
  if (!["instagram","facebook","linkedin","youtube"].includes(platform)) {
    return resultRedirect(platform, "error");
  }

  const state = text(url.searchParams.get("state"));
  if (!state || !(await consumeSession(env, platform, state))) {
    return resultRedirect(platform, "expired");
  }
  if (text(url.searchParams.get("error"))) return resultRedirect(platform, "cancelled");
  const code = text(url.searchParams.get("code"));
  if (!code || !socialOAuthConfigured(env, platform)) return resultRedirect(platform, "error");

  try {
    if (platform === "instagram") await instagramCallback(env, code);
    else if (platform === "facebook") await facebookCallback(env, code);
    else if (platform === "linkedin") await linkedinCallback(env, code);
    else await youtubeCallback(env, code);
    return resultRedirect(platform, "connected");
  } catch (error) {
    const message = text(error?.message || error || "OAuth connection failed").slice(0,280);
    await markReconnect(env, platform, message);
    return resultRedirect(platform, "error");
  }
}

async function readToken(env, platform) {
  await ensureSocialOauthSchema(env.DB);
  const row = await env.DB.prepare(
    "SELECT * FROM social_oauth_tokens WHERE platform=?"
  ).bind(platform).first();
  if (!row) throw new Error(platform + " is not connected in Studio");
  return row;
}

async function refreshInstagram(env, row) {
  const expiry = new Date(row.expires_at).valueOf();
  const current = await openToken(env, "instagram", row.access_token_enc);
  if (Number.isFinite(expiry) && expiry > Date.now()+7*24*3600*1000) {
    return {row,access:current};
  }

  const url = new URL("https://graph.instagram.com/refresh_access_token");
  url.search = new URLSearchParams({
    grant_type:"ig_refresh_token",
    access_token:current,
  }).toString();
  const response = await fetch(url, {headers:{accept:"application/json"}});
  if (!response.ok) throw new Error("Instagram token refresh failed; reconnect in Studio");
  const payload = await response.json();
  const access = text(payload.access_token) || current;
  const expiresIn = Math.max(3600, Number(payload.expires_in || 5184000));
  const expiresAt = new Date(Date.now()+expiresIn*1000).toISOString();

  await env.DB.prepare(
    "UPDATE social_oauth_tokens SET access_token_enc=?,expires_at=?,updated_at=? WHERE platform='instagram'"
  ).bind(await seal(env,"instagram",access),expiresAt,nowIso()).run();
  row.expires_at = expiresAt;
  return {row,access};
}

async function refreshYouTube(env, row) {
  const expiry = new Date(row.expires_at).valueOf();
  let access = await openToken(env, "youtube", row.access_token_enc);
  const refresh = await openToken(env, "youtube", row.refresh_token_enc);
  if (Number.isFinite(expiry) && expiry > Date.now()+5*60*1000) {
    return {row,access,refresh};
  }
  if (!refresh) throw new Error("YouTube refresh token is missing; reconnect in Studio");

  const response = await fetch("https://oauth2.googleapis.com/token", {
    method:"POST",
    headers:{"content-type":"application/x-www-form-urlencoded", accept:"application/json"},
    body:new URLSearchParams({
      client_id:clientId(env,"youtube"),
      client_secret:clientSecret(env,"youtube"),
      refresh_token:refresh,
      grant_type:"refresh_token",
    }),
  });
  if (!response.ok) throw new Error("YouTube token refresh failed; reconnect in Studio");
  const payload = await response.json();
  access = text(payload.access_token);
  const expiresIn = Math.max(300, Number(payload.expires_in || 3600));
  const expiresAt = new Date(Date.now()+expiresIn*1000).toISOString();

  await env.DB.prepare(
    "UPDATE social_oauth_tokens SET access_token_enc=?,expires_at=?,updated_at=? WHERE platform='youtube'"
  ).bind(await seal(env,"youtube",access),expiresAt,nowIso()).run();
  row.expires_at = expiresAt;
  return {row,access,refresh};
}

async function refreshLinkedIn(env, row) {
  const expiry = new Date(row.expires_at).valueOf();
  let access = await openToken(env, "linkedin", row.access_token_enc);
  if (!Number.isFinite(expiry) || expiry > Date.now()+5*60*1000) {
    return {row,access};
  }

  const refresh = await openToken(env, "linkedin", row.refresh_token_enc);
  if (!refresh) {
    await markReconnect(env,"linkedin","LinkedIn authorization expired. Reconnect from Studio.");
    throw new Error("LinkedIn authorization expired; reconnect in Studio");
  }

  const response = await fetch("https://www.linkedin.com/oauth/v2/accessToken", {
    method:"POST",
    headers:{"content-type":"application/x-www-form-urlencoded", accept:"application/json"},
    body:new URLSearchParams({
      grant_type:"refresh_token",
      refresh_token:refresh,
      client_id:clientId(env,"linkedin"),
      client_secret:clientSecret(env,"linkedin"),
    }),
  });
  if (!response.ok) {
    await markReconnect(env,"linkedin","LinkedIn authorization expired. Reconnect from Studio.");
    throw new Error("LinkedIn token refresh unavailable; reconnect in Studio");
  }

  const payload = await response.json();
  access = text(payload.access_token);
  const expiresIn = Math.max(300, Number(payload.expires_in || 5184000));
  const expiresAt = new Date(Date.now()+expiresIn*1000).toISOString();
  await env.DB.prepare(
    "UPDATE social_oauth_tokens SET access_token_enc=?,expires_at=?,updated_at=? WHERE platform='linkedin'"
  ).bind(await seal(env,"linkedin",access),expiresAt,nowIso()).run();
  row.expires_at = expiresAt;
  return {row,access};
}

export async function studioSocialCredential(env, platform) {
  if (!["instagram","facebook","linkedin","youtube"].includes(platform)) {
    throw new Error("unsupported social credential");
  }
  if (!socialOAuthConfigured(env, platform)) {
    throw new Error(platform + " OAuth app credentials are not configured in Studio");
  }

  const row = await readToken(env, platform);
  if (platform === "instagram") {
    const refreshed = await refreshInstagram(env,row);
    return {
      platform,
      access_token:refreshed.access,
      instagram_user_id:text(row.account_id),
      graph_host:"graph.instagram.com",
      api_version:META_API_VERSION,
    };
  }

  if (platform === "facebook") {
    return {
      platform,
      page_access_token:await openToken(env,platform,row.access_token_enc),
      page_id:text(row.account_id),
      api_version:META_API_VERSION,
    };
  }

  if (platform === "linkedin") {
    const refreshed = await refreshLinkedIn(env,row);
    return {
      platform,
      access_token:refreshed.access,
      author_urn:text(row.account_id),
    };
  }

  const refreshed = await refreshYouTube(env,row);
  const scopes = text(row.scope).split(/\s+/).filter(Boolean);
  return {
    platform:"youtube",
    channel_id:text(row.account_id),
    access_token:refreshed.access,
    refresh_token:refreshed.refresh,
    token_uri:"https://oauth2.googleapis.com/token",
    client_id:clientId(env,"youtube"),
    client_secret:clientSecret(env,"youtube"),
    scopes:scopes.length ? scopes : YOUTUBE_SCOPES,
    expires_at:text(row.expires_at),
  };
}
