/**
 * DOCTORPET NEWS R4 / isolated DEV implementation candidate. NOT DEPLOYED.
 * Does not create or modify a table/cron/collector/Storage policy.
 * Default response is an empty list until the designated responsible party
 * separately verifies RSS title/link metadata rights and sets the exact
 * DPN_NEWS_RSS_METADATA_PUBLIC_OK=true environment variable.
 * Images, excerpts, full texts, private reference trials and other sources
 * are never queried or returned, regardless of that flag.
 */
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import postgres from "npm:postgres@3.4.7";

const PROJECT_REF = "mabvxdcpmfdzrqlgkxqn";
const ORIGINS = new Set([
  "https://doctorpetadmin7-maker.github.io",
  "https://doctorpet-032-review.suppoess77.chatgpt.site",
]);
const COMPILE_TIME_RELEASE_ENABLED = false; // DEV installation holds all news rows closed until a separate release review.
const metadataReady = () => COMPILE_TIME_RELEASE_ENABLED && Deno.env.get("DPN_NEWS_RSS_METADATA_PUBLIC_OK") === "true";

function responseHeaders(origin: string | null) {
  const headers: Record<string,string> = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store, max-age=0",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, nofollow",
  };
  if (origin && ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers.Vary = "Origin";
    headers["Access-Control-Allow-Methods"] = "GET, OPTIONS";
    headers["Access-Control-Allow-Headers"] = "content-type";
  }
  return headers;
}
const jsonResponse = (data: unknown, status: number, origin: string | null) =>
  new Response(JSON.stringify(data), {status, headers:responseHeaders(origin)});

function verifyDevDatabase(value: string) {
  const url = new URL(value);
  const username = decodeURIComponent(url.username);
  if (url.protocol !== "postgres:" && url.protocol !== "postgresql:") throw Error("BAD_DB_PROTOCOL");
  if (url.hostname === `db.${PROJECT_REF}.supabase.co`) return;
  if (url.hostname.endsWith(".pooler.supabase.com") && username.endsWith(`.${PROJECT_REF}`)) return;
  throw Error("DEV_DATABASE_REQUIRED");
}

Deno.serve(async req => {
  const origin=req.headers.get("origin");
  if (origin && !ORIGINS.has(origin)) return jsonResponse({error:"ORIGIN_DENIED"},403,null);
  if (req.method === "OPTIONS") return new Response(null,{status:204,headers:responseHeaders(origin)});
  if (req.method !== "GET") return jsonResponse({error:"METHOD_NOT_ALLOWED"},405,origin);
  const pathname = new URL(req.url).pathname;
  if (!["/doctorpet-vet-news-public-safe-v1","/functions/v1/doctorpet-vet-news-public-safe-v1"].includes(pathname))
    return jsonResponse({error:"NOT_FOUND"},404,origin);

  // Holding state is the default: absolutely no SQL/collector/request is performed.
  if (!metadataReady()) {
    return jsonResponse({
      schemaVersion:"NEWS_PUBLIC_SAFE_V1",
      rightsGate:"REVIEW_PENDING",
      items:[],
    },200,origin);
  }

  try {
    const db=Deno.env.get("SUPABASE_DB_URL");
    if (!db) throw Error("DB_URL_REQUIRED");
    verifyDevDatabase(db);
    const sql=postgres(db,{
      max:1,ssl:"verify-full",prepare:false,idle_timeout:5,max_lifetime:30,
      connect_timeout:10,connection:{application_name:"doctorpet-vet-news-public-safe-v1"},
    });
    let rows: Array<{id:string,title:string,url:string,published_at:Date|null}> = [];
    try {
      rows=await sql.begin("isolation level repeatable read read only",async tx => {
        await tx.unsafe("set local statement_timeout='8s'");
        // Only publisher-approved RSS metadata, never reference trials or image/body fields.
        return await tx.unsafe(`
          select a.id,a.title,a.url,a.published_at
          from doctorpet_domestic_news.articles a
          join doctorpet_domestic_news.sources s on s.id=a.source_id
          where a.source_id='FEED_DAILYGAEWON'
            and s.approved is true
            and s.rights_checked_at is not null
            and s.policy_url='https://www.dailygaewon.com/rssIndex.html'
            and a.rights_evidence=s.policy_url
            and a.withdrawn is false
            and a.url like 'https://www.dailygaewon.com/%'
            and a.title is not null and length(trim(a.title)) between 1 and 500
          order by a.published_at desc nulls last,a.id
          limit 2000
        `);
      });
    } finally {await sql.end({timeout:1}).catch(()=>{});}

    return jsonResponse({
      schemaVersion:"NEWS_PUBLIC_SAFE_V1",
      rightsGate:"APPROVED_METADATA_ONLY",
      generatedAt:new Date().toISOString(),
      items:rows.map(row=>({
        id:row.id,sourceId:"FEED_DAILYGAEWON",title:row.title,
        publishedAt:row.published_at?new Date(row.published_at).toISOString():null,
        url:row.url,releaseEligible:true,
      })),
    },200,origin);
  } catch {
    // Do not expose DB errors or fallback to legacy/publicly unsafe endpoints.
    return jsonResponse({error:"NEWS_PUBLIC_SAFE_DATA_UNAVAILABLE"},503,origin);
  }
});
