const ADMIN_EMAILS = new Set(["esiahkapinga@gmail.com", "esiahsbusiness@gmail.com"]);
const ROUTES = {
  post: ["instagram", "facebook", "linkedin", "x"],
  short: ["instagram", "facebook", "youtube"],
  long: ["youtube"],
};
const LANES = new Set(["awareness","authority","proof","story","conversion","education","flexible"]);
const LIFECYCLE_WEIGHT = { IDEA:20, PRE_LAUNCH:75, NEW:100, ACTIVE:55, MATURE:20, PAUSED:0 };

const FALLBACK_PRODUCTS = [{
  id:"job-search-conversion-system",
  name:"Easy With Golide — Job Search Conversion System",
  lifecycle_status:"ACTIVE",
  target_audience:"Job seekers actively applying but not converting enough applications into interviews.",
  problem_solved:"Turns scattered job applications into a clearer repeatable application-to-interview system.",
  marketplace_url:"https://marketplace.golidee.com/jobsearch/jobsearch-toolkit",
  keywords:["job search","applications","interviews","resume","career"],
  creator_niches:["career coach","job search creator","resume creator","HR creator","remote work creator"],
  target_geographies:["US","India","UK","Canada","global English-speaking"],
  priority:70, affiliate_rate:80, launch_date:"", partner_coverage:0, recent_post_count:0, paused:false,
}];

const POLICY = {
  routing:{
    version:1,locked:true,timezone:"Africa/Lusaka",
    content_types:{
      post:{platforms:ROUTES.post,daily_core_items:2,weekly_core_items:14,product_context:{modes:["brand","specific_product","auto_product"],default_mode:"auto_product"}},
      short:{platforms:ROUTES.short,weekly_items:4,voice:"owner_recording_only",product_centered:false},
      long_video:{platforms:ROUTES.long,weekly_items:2,voice:"owner_recording_only",product_centered:false},
    },
    pinterest:{native_engine_integration:false,workflow:"manual reconnect and Instagram-derived distribution"},
  },
  calendar:{
    version:1,locked:true,timezone:"Africa/Lusaka",
    daily_posts:[
      {slot:"post-a",time:"08:30",days:["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],platforms:ROUTES.post},
      {slot:"post-b",time:"17:30",days:["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],platforms:ROUTES.post},
    ],
    shorts:[
      {day:"monday",time:"13:00",platforms:ROUTES.short},
      {day:"wednesday",time:"13:00",platforms:ROUTES.short},
      {day:"friday",time:"13:00",platforms:ROUTES.short},
      {day:"sunday",time:"13:00",platforms:ROUTES.short},
    ],
    long_videos:[
      {day:"tuesday",time:"19:30",platforms:ROUTES.long},
      {day:"saturday",time:"19:30",platforms:ROUTES.long},
    ],
  },
  social_image:{profile_name:"GOLIDE Social Post Editorial",generation:{temporary_media_only:true,approval_required_before_publish:true,provider:"openai",model:"gpt-image-2",quality:"medium"}},
  video:{style_name:"GOLIDE Reference Editorial Motion",voice:{source:"owner_recording_only",ai_voice_allowed:false,cloned_voice_allowed:false}},
  product_registry:{version:1,products:FALLBACK_PRODUCTS},
};

let schemaReady = false;

function json(data,status=200){return new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});}
function err(message,status=400){return json({error:message},status);}
function nowIso(){return new Date().toISOString();}
function safeText(v){return String(v??"").trim();}
function safeInt(v,d=0){const n=Number.parseInt(v,10);return Number.isFinite(n)?n:d;}
function bool(v){return Boolean(v);}
function hasAll(env,names){return names.every((name)=>safeText(env[name]));}

async function adminSession(request){
  const cookie=request.headers.get("cookie")||"";
  if(!cookie) return null;
  try{
    const response=await fetch("https://golidee.com/api/auth/session",{headers:{accept:"application/json",cookie,"user-agent":"GOLIDE-Content-Engine/2.0"}});
    if(!response.ok) return null;
    const payload=await response.json();
    const user=payload?.user||null;
    if(!user?.isAdmin || !ADMIN_EMAILS.has(safeText(user.email).toLowerCase())) return null;
    return user;
  }catch{return null;}
}

async function ensureSchema(db){
  if(schemaReady) return;
  const statements=[
    `CREATE TABLE IF NOT EXISTS content_posts (
      id TEXT PRIMARY KEY, kind TEXT NOT NULL, content_class TEXT NOT NULL,
      title TEXT NOT NULL DEFAULT '', master_text TEXT NOT NULL,
      weekly_theme TEXT NOT NULL DEFAULT '', content_lane TEXT NOT NULL DEFAULT '',
      value_units_json TEXT NOT NULL DEFAULT '[]',
      product_bridge_position INTEGER, product_url TEXT NOT NULL DEFAULT '',
      product_mode TEXT NOT NULL DEFAULT 'brand', product_id TEXT NOT NULL DEFAULT '',
      owner_voice_media_ref TEXT, media_approved INTEGER NOT NULL DEFAULT 0,
      qa_approved INTEGER NOT NULL DEFAULT 0, release_approved INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL, scheduled_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS social_variants (
      id TEXT PRIMARY KEY, post_id TEXT NOT NULL, platform TEXT NOT NULL,
      title TEXT NOT NULL DEFAULT '', body TEXT NOT NULL, parts_json TEXT NOT NULL DEFAULT '[]',
      media_ref TEXT, status TEXT NOT NULL DEFAULT 'pending', platform_content_id TEXT,
      published_url TEXT, last_error TEXT, published_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(post_id, platform)
    )`,
    `CREATE TABLE IF NOT EXISTS publish_attempts (
      id INTEGER PRIMARY KEY AUTOINCREMENT, post_id TEXT NOT NULL, variant_id TEXT NOT NULL,
      platform TEXT NOT NULL, status TEXT NOT NULL, remote_id TEXT, error TEXT, created_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS inbox_threads (
      id TEXT PRIMARY KEY, platform TEXT NOT NULL, external_thread_id TEXT NOT NULL,
      account_id TEXT NOT NULL DEFAULT '', participant_ref TEXT NOT NULL DEFAULT '',
      subject TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open',
      last_message_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS inbox_messages (
      id TEXT PRIMARY KEY, thread_id TEXT NOT NULL, external_message_id TEXT NOT NULL,
      direction TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS temporary_media (
      id TEXT PRIMARY KEY, object_key TEXT NOT NULL UNIQUE, media_kind TEXT NOT NULL,
      post_id TEXT, status TEXT NOT NULL DEFAULT 'active', expires_at TEXT NOT NULL,
      created_at TEXT NOT NULL, deleted_at TEXT
    )`,
    `CREATE TABLE IF NOT EXISTS production_jobs (
      job_id TEXT PRIMARY KEY,
      format TEXT NOT NULL,
      spec_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued',
      stage TEXT NOT NULL DEFAULT 'registered',
      title TEXT NOT NULL DEFAULT '',
      selected_topic TEXT NOT NULL DEFAULT '',
      script TEXT NOT NULL DEFAULT '',
      owner_voice_media_ref TEXT,
      generate_at TEXT,
      scheduled_at TEXT,
      actual_cost_usd REAL NOT NULL DEFAULT 0,
      openai_cost_usd REAL NOT NULL DEFAULT 0,
      run_url TEXT,
      release_url TEXT,
      error TEXT,
      claimed_at TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS engine_connections (
      platform TEXT PRIMARY KEY,
      connected INTEGER NOT NULL DEFAULT 0,
      account_label TEXT NOT NULL DEFAULT '',
      external_account_id TEXT NOT NULL DEFAULT '',
      synced_at TEXT NOT NULL
    )`,
    `CREATE INDEX IF NOT EXISTS idx_content_posts_due ON content_posts(status, scheduled_at)`,
    `CREATE INDEX IF NOT EXISTS idx_social_variants_post ON social_variants(post_id, status)`,
    `CREATE INDEX IF NOT EXISTS idx_inbox_threads_open ON inbox_threads(status, last_message_at)`,
    `CREATE INDEX IF NOT EXISTS idx_inbox_messages_thread ON inbox_messages(thread_id, created_at)`,
    `CREATE INDEX IF NOT EXISTS idx_temporary_media_cleanup ON temporary_media(status, expires_at)`,
    `CREATE INDEX IF NOT EXISTS idx_production_jobs_queue ON production_jobs(status, generate_at, updated_at)`,
  ];
  for(const sql of statements) await db.prepare(sql).run();
  schemaReady=true;
}

async function count(db,sql,...args){
  const row=await db.prepare(sql).bind(...args).first();
  return Number(row?.count||0);
}

async function overview(env){
  const db=env.DB;
  return {
    posts_today:await count(db,`SELECT COUNT(*) count FROM content_posts WHERE content_class='post' AND date(created_at)=date('now')`),
    scheduled:await count(db,`SELECT COUNT(*) count FROM content_posts WHERE status='scheduled'`),
    published:await count(db,`SELECT COUNT(*) count FROM content_posts WHERE status='published'`),
    failed:await count(db,`SELECT COUNT(*) count FROM content_posts WHERE status IN ('failed','partial')`),
    open_responses:await count(db,`SELECT COUNT(*) count FROM inbox_threads WHERE status='open'`),
    temporary_media:await count(db,`SELECT COUNT(*) count FROM temporary_media WHERE status!='deleted'`),
    draft_posts:await count(db,`SELECT COUNT(*) count FROM content_posts WHERE content_class='post' AND status='draft'`),
    draft_shorts:await count(db,`SELECT COUNT(*) count FROM content_posts WHERE content_class='short' AND status='draft'`),
    draft_longs:await count(db,`SELECT COUNT(*) count FROM content_posts WHERE content_class='long' AND status='draft'`),
    production_jobs:await count(db,`SELECT COUNT(*) count FROM production_jobs`),
    waiting_voice:await count(db,`SELECT COUNT(*) count FROM production_jobs WHERE status='waiting_owner_voice'`),
    production_running:await count(db,`SELECT COUNT(*) count FROM production_jobs WHERE status IN ('claimed','running')`),
    r2_ready:hasAll(env,["R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"]),
  };
}

async function listPosts(db,status){
  let stmt=db.prepare(`SELECT id,kind,content_class,title,master_text,weekly_theme,content_lane,value_units_json,
    product_bridge_position,product_url,product_mode,product_id,owner_voice_media_ref,media_approved,qa_approved,
    release_approved,status,scheduled_at,created_at,updated_at FROM content_posts
    ${status?"WHERE status=?":""} ORDER BY COALESCE(scheduled_at,created_at) DESC`);
  if(status) stmt=stmt.bind(status);
  const {results=[]}=await stmt.all();
  for(const row of results){
    try{row.value_units=JSON.parse(row.value_units_json||"[]");}catch{row.value_units=[];}
    delete row.value_units_json;
    const variants=await db.prepare(`SELECT id,post_id,platform,title,body,parts_json,media_ref,status,platform_content_id,published_url,last_error,published_at
      FROM social_variants WHERE post_id=? ORDER BY platform ASC`).bind(row.id).all();
    row.variants=(variants.results||[]).map((v)=>{try{v.parts=JSON.parse(v.parts_json||"[]");}catch{v.parts=[];} delete v.parts_json; return v;});
  }
  return results;
}

async function inbox(db){
  const threads=(await db.prepare(`SELECT id,platform,participant_ref,subject,status,last_message_at FROM inbox_threads WHERE status='open' ORDER BY COALESCE(last_message_at,created_at) DESC`).all()).results||[];
  for(const thread of threads){
    thread.messages=(await db.prepare(`SELECT direction,body,created_at FROM inbox_messages WHERE thread_id=? ORDER BY created_at ASC`).bind(thread.id).all()).results||[];
  }
  return threads;
}

async function connectionRows(db,env){
  const synced=(await db.prepare(`SELECT platform,connected,account_label,external_account_id,synced_at FROM engine_connections ORDER BY platform`).all()).results||[];
  if(synced.length){
    return synced.filter((row)=>Number(row.connected)===1).map((row)=>({
      id:row.platform,
      platform:row.platform,
      account_label:row.account_label,
      external_account_id:row.external_account_id,
      transport:"official_api",
      status:"connected",
      synced_at:row.synced_at,
    }));
  }
  const rows=[];
  const push=(platform,connected,label,external="")=>{if(connected)rows.push({id:platform,platform,account_label:label,external_account_id:external,transport:"official_api",status:"connected"});};
  const meta=Boolean(safeText(env.GOLIDE_META_API_VERSION));
  push("instagram",meta&&Boolean(safeText(env.INSTAGRAM_USER_ACCESS_TOKEN)),"Instagram",safeText(env.GOLIDE_INSTAGRAM_USER_ID)||"instagram-login");
  push("facebook",meta&&hasAll(env,["META_PAGE_ACCESS_TOKEN","GOLIDE_FACEBOOK_PAGE_ID"]),"Facebook Page",safeText(env.GOLIDE_FACEBOOK_PAGE_ID));
  push("linkedin",hasAll(env,["LINKEDIN_ACCESS_TOKEN","GOLIDE_LINKEDIN_AUTHOR_URN","GOLIDE_LINKEDIN_VERSION"]),"LinkedIn",safeText(env.GOLIDE_LINKEDIN_AUTHOR_URN));
  push("x",Boolean(safeText(env.X_USER_ACCESS_TOKEN)),"X","x-user");
  push("youtube",Boolean(safeText(env.YOUTUBE_REFRESH_TOKEN)||safeText(env.GOOGLE_OAUTH_REFRESH_TOKEN)||safeText(env.GOLIDE_YOUTUBE_CONNECTED)),"YouTube","UCqaXVBSBz7iQsRHOupKt-3w");
  return rows;
}

async function liveRegistry(request){
  try{
    const response=await fetch("https://marketplace.golidee.com/api/product-registry",{headers:{accept:"application/json",cookie:request.headers.get("cookie")||"","user-agent":"GOLIDE-Content-Engine/2.0"}});
    if(!response.ok) throw new Error("registry unavailable");
    const payload=await response.json();
    if(!Array.isArray(payload?.products)) throw new Error("invalid registry");
    return payload;
  }catch{return POLICY.product_registry;}
}

function productWeight(p){
  const lifecycle=LIFECYCLE_WEIGHT[safeText(p.lifecycle_status).toUpperCase()]??40;
  const coverageGap=Math.max(0,40-safeInt(p.partner_coverage,0))*2;
  const postingGap=Math.max(0,8-safeInt(p.recent_post_count,0))*5;
  const priority=Math.max(0,Math.min(100,safeInt(p.priority,50)));
  return Math.max(1,lifecycle+priority+coverageGap+postingGap);
}

async function seedNumber(seed){
  const bytes=new TextEncoder().encode(String(seed??""));
  const digest=new Uint8Array(await crypto.subtle.digest("SHA-256",bytes));
  let n=0; for(let i=0;i<8;i++) n=(n*256+digest[i])%2147483647;
  return n;
}

async function resolveProduct(payload,db){
  const mode=safeText(payload.product_mode||"brand").toLowerCase();
  if(!["brand","specific_product","auto_product"].includes(mode)) throw new Error("unsupported product mode");
  if(mode==="brand") return null;
  const source=Array.isArray(payload.registry_products)&&payload.registry_products.length?payload.registry_products:FALLBACK_PRODUCTS;
  const enriched=[];
  for(const raw of source){
    const p={...raw};
    if(p.id){
      const row=await db.prepare(`SELECT COUNT(*) count FROM content_posts WHERE content_class='post' AND product_id=? AND datetime(created_at)>=datetime('now','-14 days')`).bind(String(p.id)).first();
      p.recent_post_count=Number(row?.count||0);
    }
    enriched.push(p);
  }
  const eligible=enriched.filter((p)=>p.id&&p.name&&!p.paused&&safeText(p.lifecycle_status).toUpperCase()!=="PAUSED");
  if(mode==="specific_product"){
    const found=eligible.find((p)=>String(p.id)===safeText(payload.product_id));
    if(!found) throw new Error("specific_product requires an active product");
    return found;
  }
  if(!eligible.length) throw new Error("no active products are available for auto product selection");
  const weights=eligible.map(productWeight);
  const total=weights.reduce((a,b)=>a+b,0);
  let point=(await seedNumber(payload.selection_seed))%total;
  for(let i=0;i<eligible.length;i++){if(point<weights[i]) return eligible[i]; point-=weights[i];}
  return eligible[eligible.length-1];
}

function validateSchedule(payload,klass,variants,units){
  const scheduled=Boolean(payload.scheduled_at);
  if(!scheduled) return;
  const actual=variants.map((v)=>safeText(v.platform).toLowerCase());
  const expected=ROUTES[klass];
  if(actual.length!==expected.length||expected.some((p)=>!actual.includes(p))) throw new Error(`${klass} route is locked; all destination platforms are required`);
  if(!payload.release_approved) throw new Error("release approval is required before scheduling");
  if(klass==="post"){
    if(units.length<3||units.length>4) throw new Error("static posts require 3 to 4 related value units");
    if(!payload.media_approved) throw new Error("static image approval is required before scheduling");
    if(variants.some((v)=>!safeText(v.media_ref))) throw new Error("every static platform variant requires approved media");
  }else{
    if(!payload.qa_approved) throw new Error("video QA approval is required before scheduling");
    if(!safeText(payload.owner_voice_media_ref)) throw new Error("owner-recorded voice is required before scheduling video");
    if(variants.some((v)=>!safeText(v.media_ref))) throw new Error("every video route requires a final approved video media reference");
  }
}

async function createPost(env,payload){
  const db=env.DB;
  const klass=safeText(payload.content_class||"post").toLowerCase();
  if(!ROUTES[klass]) throw new Error("unsupported content class");
  const lane=safeText(payload.content_lane);
  if(lane&&!LANES.has(lane)) throw new Error("unsupported content lane");
  let units=klass==="post"?(Array.isArray(payload.value_units)?payload.value_units.map(safeText).filter(Boolean):[]):[];
  let productMode=klass==="post"?safeText(payload.product_mode||"brand").toLowerCase():"brand";
  let productId="", productUrl="", productName="";
  let bridge=payload.product_bridge_position?safeInt(payload.product_bridge_position):null;
  if(klass==="post"){
    const product=await resolveProduct(payload,db);
    if(product){
      productId=String(product.id); productUrl=safeText(product.marketplace_url); productName=safeText(product.name);
    }else{productMode="brand"; bridge=null;}
    if(bridge!==null){
      if(![2,3].includes(bridge)||bridge>units.length) throw new Error("product bridge must be at value unit 2 or 3");
      if(!productUrl.startsWith("https://")) throw new Error("a product bridge requires an HTTPS product URL");
      if(!units[bridge-1].includes(productUrl)) units[bridge-1]=units[bridge-1].replace(/\s+$/,"")+"\n"+productUrl;
    }
    if(units.length&& (units.length<3||units.length>4)) throw new Error("static posts require 3 to 4 related value units");
  }else{bridge=null;}

  const variants=Array.isArray(payload.variants)?payload.variants.map((v)=>({
    platform:safeText(v.platform).toLowerCase(),title:safeText(v.title),body:safeText(v.body),
    media_ref:safeText(v.media_ref)||null,parts:klass==="post"?units:(Array.isArray(v.parts)?v.parts.map(safeText).filter(Boolean):[])
  })):[];
  const unsupported=variants.map((v)=>v.platform).filter((p)=>!ROUTES[klass].includes(p));
  if(unsupported.length) throw new Error(`${klass} cannot route to: ${[...new Set(unsupported)].join(", ")}`);
  validateSchedule(payload,klass,variants,units);

  const id=crypto.randomUUID(), now=nowIso(), scheduled=safeText(payload.scheduled_at)||null;
  const status=scheduled?"scheduled":"draft", kind=klass==="post"?"social":"video";
  const master=safeText(payload.master_text)||(units.length?units.join("\n\n"):"");
  await db.prepare(`INSERT INTO content_posts
    (id,kind,content_class,title,master_text,weekly_theme,content_lane,value_units_json,product_bridge_position,product_url,product_mode,product_id,
     owner_voice_media_ref,media_approved,qa_approved,release_approved,status,scheduled_at,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`)
    .bind(id,kind,klass,safeText(payload.title),master,safeText(payload.weekly_theme),lane,JSON.stringify(units),bridge,productUrl,productMode,productId,
      safeText(payload.owner_voice_media_ref)||null,bool(payload.media_approved)?1:0,bool(payload.qa_approved)?1:0,bool(payload.release_approved)?1:0,
      status,scheduled,now,now).run();

  const refs=new Set();
  for(const v of variants){
    if(v.media_ref) refs.add(v.media_ref);
    await db.prepare(`INSERT INTO social_variants
      (id,post_id,platform,title,body,parts_json,media_ref,status,created_at,updated_at)
      VALUES (?,?,?,?,?,?,?,'pending',?,?)`)
      .bind(crypto.randomUUID(),id,v.platform,v.title,v.body,JSON.stringify(v.parts),v.media_ref,now,now).run();
  }
  const voice=safeText(payload.owner_voice_media_ref); if(voice) refs.add(voice);
  for(const ref of refs){
    let expiry=null;
    if(scheduled){const d=new Date(scheduled); if(!Number.isNaN(d.valueOf())) expiry=new Date(d.getTime()+24*3600*1000).toISOString();}
    if(expiry) await db.prepare(`UPDATE temporary_media SET post_id=?, expires_at=CASE WHEN expires_at<? THEN ? ELSE expires_at END WHERE object_key=?`).bind(id,expiry,expiry,ref).run();
    else await db.prepare(`UPDATE temporary_media SET post_id=? WHERE object_key=?`).bind(id,ref).run();
  }
  return {id,status,content_class:klass,product_mode:productMode,product_id:productId,product_name:productName};
}

async function listProductionJobs(db){
  const {results=[]}=await db.prepare(`SELECT job_id,format,status,stage,title,selected_topic,script,owner_voice_media_ref,
    generate_at,scheduled_at,actual_cost_usd,openai_cost_usd,run_url,release_url,error,claimed_at,created_at,updated_at
    FROM production_jobs ORDER BY COALESCE(scheduled_at,generate_at,created_at) DESC LIMIT 100`).all();
  return results;
}

async function registerProductionJob(db,payload){
  const jobId=safeText(payload.jobId);
  const spec=payload.spec;
  if(!jobId||!spec||typeof spec!=="object") throw new Error("jobId and spec are required");
  const now=nowIso();
  const existing=await db.prepare(`SELECT status,script,owner_voice_media_ref FROM production_jobs WHERE job_id=?`).bind(jobId).first();
  const voice=safeText(spec.owner_voice_media_ref)||safeText(existing?.owner_voice_media_ref)||null;
  if(voice) spec.owner_voice_media_ref=voice;
  let status=existing?.status||"queued";
  if(!existing) status="queued";
  else if(voice && status==="waiting_owner_voice") status="queued";
  await db.prepare(`INSERT INTO production_jobs
    (job_id,format,spec_json,status,stage,title,selected_topic,script,owner_voice_media_ref,generate_at,scheduled_at,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(job_id) DO UPDATE SET
      format=excluded.format,spec_json=excluded.spec_json,
      status=CASE WHEN production_jobs.status='waiting_owner_voice' AND excluded.owner_voice_media_ref IS NOT NULL THEN 'queued' ELSE production_jobs.status END,
      title=CASE WHEN excluded.title<>'' THEN excluded.title ELSE production_jobs.title END,
      owner_voice_media_ref=COALESCE(excluded.owner_voice_media_ref,production_jobs.owner_voice_media_ref),
      generate_at=excluded.generate_at,scheduled_at=excluded.scheduled_at,updated_at=excluded.updated_at`)
    .bind(
      jobId,safeText(spec.format)||"short",JSON.stringify(spec),status,"registered",
      safeText(spec.title),safeText(spec.brief),safeText(existing?.script),voice,
      safeText(spec.generate_at)||null,safeText(spec.release?.scheduled_at)||null,
      now,now
    ).run();
  return {jobId,status};
}

async function claimNextProduction(db,nowValue){
  const now=safeText(nowValue)||nowIso();
  const row=await db.prepare(`SELECT job_id,spec_json FROM production_jobs
    WHERE status IN ('queued','paused_funds')
      AND (generate_at IS NULL OR generate_at='' OR generate_at<=?)
    ORDER BY COALESCE(generate_at,created_at) ASC LIMIT 1`).bind(now).first();
  if(!row) return null;
  const claimed=nowIso();
  await db.prepare(`UPDATE production_jobs SET status='claimed',stage='claimed-by-engine',claimed_at=?,updated_at=? WHERE job_id=?`)
    .bind(claimed,claimed,row.job_id).run();
  return {jobId:row.job_id,spec:JSON.parse(row.spec_json)};
}

async function updateProductionStatus(db,jobId,payload){
  const current=await db.prepare(`SELECT spec_json FROM production_jobs WHERE job_id=?`).bind(jobId).first();
  if(!current) throw new Error("production job not found");
  const status=safeText(payload.status)||"running";
  const stage=safeText(payload.stage)||status;
  const title=safeText(payload.title);
  const script=safeText(payload.script);
  const topic=safeText(payload.selectedTopic);
  let spec=JSON.parse(current.spec_json);
  if(title) spec.title=title;
  if(topic) spec.brief=topic;
  await db.prepare(`UPDATE production_jobs SET
    spec_json=?,status=?,stage=?,
    title=CASE WHEN ?<>'' THEN ? ELSE title END,
    selected_topic=CASE WHEN ?<>'' THEN ? ELSE selected_topic END,
    script=CASE WHEN ?<>'' THEN ? ELSE script END,
    actual_cost_usd=?,openai_cost_usd=?,
    run_url=?,release_url=?,error=?,updated_at=?
    WHERE job_id=?`)
    .bind(
      JSON.stringify(spec),status,stage,
      title,title,topic,topic,script,script,
      Number(payload.actualCostUsd||0),Number(payload.providerUsage?.openAiCostUsd||0),
      safeText(payload.runUrl)||null,safeText(payload.releaseUrl)||null,safeText(payload.error)||null,
      nowIso(),jobId
    ).run();
  return {jobId,status,stage};
}

async function attachOwnerVoice(db,jobId,mediaRef){
  const ref=safeText(mediaRef);
  if(!ref.startsWith("r2://")) throw new Error("owner voice must be a temporary R2 media reference");
  const row=await db.prepare(`SELECT spec_json,scheduled_at FROM production_jobs WHERE job_id=?`).bind(jobId).first();
  if(!row) throw new Error("production job not found");
  const spec=JSON.parse(row.spec_json);
  spec.owner_voice_media_ref=ref;
  const scheduled=safeText(row.scheduled_at);
  if(scheduled){
    const d=new Date(scheduled);
    if(!Number.isNaN(d.valueOf())){
      const expiry=new Date(d.getTime()+24*3600*1000).toISOString();
      await db.prepare(`UPDATE temporary_media SET expires_at=CASE WHEN expires_at<? THEN ? ELSE expires_at END WHERE object_key=?`)
        .bind(expiry,expiry,ref).run();
    }
  }
  await db.prepare(`UPDATE production_jobs SET spec_json=?,owner_voice_media_ref=?,status='queued',stage='owner-voice-ready',error=NULL,updated_at=? WHERE job_id=?`)
    .bind(JSON.stringify(spec),ref,nowIso(),jobId).run();
  return {jobId,status:"queued",stage:"owner-voice-ready"};
}

async function syncEngineConnections(db,payload){
  const rows=Array.isArray(payload.connections)?payload.connections:[];
  const now=nowIso();
  for(const item of rows){
    const platform=safeText(item.platform).toLowerCase();
    if(!["instagram","facebook","linkedin","x","youtube"].includes(platform)) continue;
    await db.prepare(`INSERT INTO engine_connections(platform,connected,account_label,external_account_id,synced_at)
      VALUES(?,?,?,?,?)
      ON CONFLICT(platform) DO UPDATE SET connected=excluded.connected,account_label=excluded.account_label,
      external_account_id=excluded.external_account_id,synced_at=excluded.synced_at`)
      .bind(platform,item.connected?1:0,safeText(item.accountLabel),safeText(item.externalAccountId),now).run();
  }
  return {synced:rows.length};
}

let githubJwksCache={expires:0,keys:[]};
function b64urlBytes(value){
  const normalized=value.replace(/-/g,"+").replace(/_/g,"/");
  const padded=normalized+"=".repeat((4-normalized.length%4)%4);
  const binary=atob(padded);
  return Uint8Array.from(binary,(ch)=>ch.charCodeAt(0));
}
function b64urlJson(value){
  return JSON.parse(new TextDecoder().decode(b64urlBytes(value)));
}
async function githubJwks(){
  if(githubJwksCache.expires>Date.now()&&githubJwksCache.keys.length) return githubJwksCache.keys;
  const response=await fetch("https://token.actions.githubusercontent.com/.well-known/jwks");
  if(!response.ok) throw new Error("GitHub OIDC JWKS unavailable");
  const payload=await response.json();
  githubJwksCache={expires:Date.now()+3600_000,keys:payload.keys||[]};
  return githubJwksCache.keys;
}
async function machineAuthorized(request){
  const auth=request.headers.get("authorization")||"";
  if(!auth.startsWith("Bearer ")) return false;
  const token=auth.slice(7).trim();
  const parts=token.split(".");
  if(parts.length!==3) return false;
  try{
    const header=b64urlJson(parts[0]);
    const claims=b64urlJson(parts[1]);
    if(header.alg!=="RS256"||!header.kid) return false;
    if(claims.aud!=="golide-studio-engine") return false;
    if(claims.repository!=="risktacker/golide-content-engine") return false;
    const now=Math.floor(Date.now()/1000);
    if(Number(claims.exp||0)<=now||Number(claims.nbf||0)>now+60) return false;
    const keys=await githubJwks();
    const jwk=keys.find((key)=>key.kid===header.kid);
    if(!jwk) return false;
    const key=await crypto.subtle.importKey("jwk",jwk,{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
    const signed=new TextEncoder().encode(parts[0]+"."+parts[1]);
    return await crypto.subtle.verify("RSASSA-PKCS1-v1_5",key,b64urlBytes(parts[2]),signed);
  }catch{return false;}
}

async function handleMachineApi(request,env,url){
  await ensureSchema(env.DB);
  if(url.pathname==="/api/engine/next"&&request.method==="GET"){
    const claimed=await claimNextProduction(env.DB,url.searchParams.get("now"));
    return claimed?json(claimed):new Response(null,{status:204});
  }
  if(url.pathname==="/api/engine/jobs/register"&&request.method==="POST"){
    try{return json(await registerProductionJob(env.DB,await request.json()),201);}catch(e){return err(e?.message||String(e),400);}
  }
  const statusMatch=url.pathname.match(/^\/api\/engine\/jobs\/([^/]+)\/status$/);
  if(statusMatch&&request.method==="POST"){
    try{return json(await updateProductionStatus(env.DB,decodeURIComponent(statusMatch[1]),await request.json()));}catch(e){return err(e?.message||String(e),400);}
  }
  if(url.pathname==="/api/engine/connections"&&request.method==="POST"){
    try{return json(await syncEngineConnections(env.DB,await request.json()));}catch(e){return err(e?.message||String(e),400);}
  }
  if(url.pathname==="/api/engine/analytics"&&request.method==="POST"){
    return json({status:"accepted"});
  }
  return err("not found",404);
}

function safeFilename(name){
  const base=String(name||"").replace(/\\/g,"/").split("/").pop().trim().replace(/[^A-Za-z0-9._-]+/g,"-").replace(/^[-._]+|[-._]+$/g,"");
  return (base||"media.bin").slice(0,120);
}
function hex(bytes){return Array.from(bytes).map((b)=>b.toString(16).padStart(2,"0")).join("");}
async function sha256Bytes(data){return new Uint8Array(await crypto.subtle.digest("SHA-256",typeof data==="string"?new TextEncoder().encode(data):data));}
async function hmac(key,data){
  const cryptoKey=await crypto.subtle.importKey("raw",key,{name:"HMAC",hash:"SHA-256"},false,["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC",cryptoKey,new TextEncoder().encode(data)));
}
async function signatureKey(secret,dateStamp){
  const kDate=await hmac(new TextEncoder().encode("AWS4"+secret),dateStamp);
  const kRegion=await hmac(kDate,"auto");
  const kService=await hmac(kRegion,"s3");
  return hmac(kService,"aws4_request");
}
function rfc3986(value){return encodeURIComponent(value).replace(/[!'()*]/g,(c)=>"%"+c.charCodeAt(0).toString(16).toUpperCase());}
async function presign(env,method,key,expires=900,at=new Date()){
  if(!hasAll(env,["R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"])) throw new Error("temporary R2 storage is not configured");
  const dateStamp=at.toISOString().slice(0,10).replace(/-/g,"");
  const amzDate=dateStamp+"T"+at.toISOString().slice(11,19).replace(/:/g,"")+"Z";
  const scope=`${dateStamp}/auto/s3/aws4_request`;
  const host=`${env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`;
  const canonicalUri="/"+[env.R2_BUCKET,...key.split("/")].map(rfc3986).join("/");
  const params={
    "X-Amz-Algorithm":"AWS4-HMAC-SHA256",
    "X-Amz-Credential":`${env.R2_ACCESS_KEY_ID}/${scope}`,
    "X-Amz-Date":amzDate,
    "X-Amz-Expires":String(expires),
    "X-Amz-SignedHeaders":"host",
  };
  const canonicalQuery=Object.keys(params).sort().map((k)=>`${rfc3986(k)}=${rfc3986(params[k])}`).join("&");
  const canonicalRequest=[method.toUpperCase(),canonicalUri,canonicalQuery,`host:${host}\n`,"host","UNSIGNED-PAYLOAD"].join("\n");
  const requestHash=hex(await sha256Bytes(canonicalRequest));
  const stringToSign=["AWS4-HMAC-SHA256",amzDate,scope,requestHash].join("\n");
  const keyBytes=await signatureKey(env.R2_SECRET_ACCESS_KEY,dateStamp);
  const signature=hex(await hmac(keyBytes,stringToSign));
  return `https://${host}${canonicalUri}?${canonicalQuery}&X-Amz-Signature=${signature}`;
}

async function prepareMedia(env,payload){
  if(!hasAll(env,["R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET"])) throw new Error("temporary R2 storage is not configured");
  const kind=safeText(payload.media_kind);
  if(!["image","audio","video","render_asset"].includes(kind)) throw new Error("unsupported media kind");
  const filename=safeFilename(payload.filename);
  const at=new Date(), day=at.toISOString().slice(0,10).replace(/-/g,"/");
  const key=`temp/${day}/${crypto.randomUUID().replace(/-/g,"")}-${filename}`, ref=`r2://${key}`;
  const expiresAt=new Date(at.getTime()+24*3600*1000).toISOString();
  await env.DB.prepare(`INSERT INTO temporary_media (id,object_key,media_kind,status,expires_at,created_at) VALUES (?,?,?,'active',?,?)`)
    .bind(crypto.randomUUID(),ref,kind,expiresAt,at.toISOString()).run();
  return {media_ref:ref,upload_url:await presign(env,"PUT",key,900,at),expires_at:expiresAt};
}

async function handleApi(request,env,url){
  await ensureSchema(env.DB);
  if(url.pathname==="/api/health"&&request.method==="GET") return json({status:"ok"});
  if(url.pathname==="/api/overview"&&request.method==="GET") return json(await overview(env));
  if(url.pathname==="/api/policy"&&request.method==="GET") return json(POLICY);
  if(url.pathname==="/api/product-registry"&&request.method==="GET") return json(await liveRegistry(request));
  if(url.pathname==="/api/posts"&&request.method==="GET") return json({posts:await listPosts(env.DB,url.searchParams.get("status"))});
  if(url.pathname==="/api/posts"&&request.method==="POST"){
    try{return json(await createPost(env,await request.json()),201);}catch(e){return err(e?.message||String(e),400);}
  }
  if(url.pathname==="/api/inbox"&&request.method==="GET") return json({threads:await inbox(env.DB)});
  if(url.pathname==="/api/connections"&&request.method==="GET") return json({connections:await connectionRows(env.DB,env)});
  if(url.pathname==="/api/production-jobs"&&request.method==="GET") return json({jobs:await listProductionJobs(env.DB)});
  const voiceMatch=url.pathname.match(/^\/api\/production-jobs\/([^/]+)\/voice$/);
  if(voiceMatch&&request.method==="POST"){
    try{
      const payload=await request.json();
      return json(await attachOwnerVoice(env.DB,decodeURIComponent(voiceMatch[1]),payload.media_ref));
    }catch(e){return err(e?.message||String(e),400);}
  }
  const retryMatch=url.pathname.match(/^\/api\/production-jobs\/([^/]+)\/retry$/);
  if(retryMatch&&request.method==="POST"){
    const id=decodeURIComponent(retryMatch[1]);
    await env.DB.prepare(`UPDATE production_jobs SET status='queued',stage='manual-retry',error=NULL,updated_at=? WHERE job_id=?`).bind(nowIso(),id).run();
    return json({jobId:id,status:"queued"});
  }
  if(url.pathname==="/api/media/prepare"&&request.method==="POST"){
    try{return json(await prepareMedia(env,await request.json()),201);}catch(e){return err(e?.message||String(e),503);}
  }
  if(url.pathname==="/api/social-image/generate"&&request.method==="POST"){
    if(safeText(env.GOLIDE_ENABLE_PAID_PRODUCTION)!=="1") return err("paid image generation is locked; enable paid production only for an approved creative",503);
    return err("paid image generation is not enabled in the Worker runtime; upload an approved image manually",503);
  }
  return err("not found",404);
}

export default {
  async fetch(request,env){
    const url=new URL(request.url);
    if(url.pathname.startsWith("/api/engine/")){
      if(!(await machineAuthorized(request))) return err("engine authentication required",401);
      return handleMachineApi(request,env,url);
    }
    const user=await adminSession(request);
    if(!user){
      if(url.pathname.startsWith("/api/")) return err("admin authentication required",401);
      return Response.redirect("https://golidee.com/login?returnTo=%2Fstudio",302);
    }
    if(url.pathname.startsWith("/api/")) return handleApi(request,env,url);
    if(!env.ASSETS) return new Response("GOLIDE Studio assets binding is unavailable",{status:503});
    return env.ASSETS.fetch(request);
  }
};
