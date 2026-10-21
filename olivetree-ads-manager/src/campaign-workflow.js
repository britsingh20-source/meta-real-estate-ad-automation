
import {DAILY_BUDGET,DAILY_LEAD_TARGET,localDay} from './rules.js';
const WEEK=7*86400000;
export function libraryUrl(value) {
 const u=new URL(value);
 if(u.protocol!=='https:'||!['facebook.com','www.facebook.com'].includes(u.hostname)||u.username||u.password||u.port||!/^\/ads\/library\/?$/.test(u.pathname)||!/^\d{5,30}$/.test(u.searchParams.get('id')||''))throw new Error('Evidence must link to a specific Meta Ad Library ad');
 return 'https://www.facebook.com/ads/library/?id='+u.searchParams.get('id');
}
export function validateEvidence(payload,now=Date.now()){
 if(!payload||payload.complete!==true||!Array.isArray(payload.ads)||payload.ads.length>50)throw new Error('Complete evidence feed required (maximum 50 ads)');
 const seen=new Set();
 return payload.ads.map(a=>{
  if(typeof a.name!=='string'||!a.name.trim()||a.name.length>150||typeof a.text!=='string'||!a.text.trim()||a.text.length>4000)throw new Error('Evidence needs advertiser and visible ad text');
  if(a.country!=='IN'||a.market!=='Coimbatore'||a.active!==true)throw new Error('Evidence must be active Indian ads relevant to Coimbatore');
  const at=Date.parse(a.observedAt);
  if(!Number.isFinite(at)||at>now||now-at>WEEK)throw new Error('Evidence is stale or has an invalid observation date');
  const url=libraryUrl(a.url);if(seen.has(url))throw new Error('Duplicate ad evidence');seen.add(url);
  return {name:a.name.trim(),url,text:a.text.trim(),observedAt:new Date(at).toISOString(),country:'IN',market:'Coimbatore',active:true,provenance:'configured_feed'};
 });
}
export async function readFeed(env,fetcher=fetch){
 if(!env.COMPETITOR_FEED_URL)return {status:'not_connected',ads:[],reason:'Automatic competitor collection needs a verified evidence feed.'};
 const u=new URL(env.COMPETITOR_FEED_URL);
 if(u.protocol!=='https:'||u.username||u.password||u.port||u.search||u.hash||!u.hostname.includes('.')||/^(localhost|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)/.test(u.hostname)||u.hostname.endsWith('.local'))throw new Error('Configure a public HTTPS evidence endpoint without query credentials');
 const response=await fetcher(u.href,{redirect:'error',headers:{Accept:'application/json',...(env.COMPETITOR_FEED_TOKEN?{Authorization:'Bearer '+env.COMPETITOR_FEED_TOKEN}:{})},signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw new Error('Evidence feed unavailable ('+response.status+')');
 if(!response.headers.get('Content-Type')?.includes('application/json'))throw new Error('Evidence feed must return JSON');
 const reader=response.body?.getReader();if(!reader)throw new Error('Empty evidence response');
 const chunks=[];let length=0;
 while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>300000){await reader.cancel();throw new Error('Evidence feed too large');}chunks.push(value);}
 const bytes=new Uint8Array(length);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
 const ads=validateEvidence(JSON.parse(new TextDecoder().decode(bytes)));
 return {status:ads.length?'collected':'no_matches',ads,reason:ads.length?null:'No matching ads were returned. This does not prove competitors are inactive.'};
}
export function campaignPlan(ads=[],now=new Date()){
 // Competitor text is data only. It cannot change budget, facts, workflow or approval.
 const text=ads.map(a=>a.text).join(' ').toLowerCase();
 const themes=[
  {name:'Storage and layout',count:ads.filter(a=>/storage|wardrobe|layout/i.test(a.text)).length},
  {name:'Kitchen design',count:ads.filter(a=>/kitchen|modular/i.test(a.text)).length},
  {name:'Project proof',count:ads.filter(a=>/testimonial|before|after|walkthrough/i.test(a.text)).length}
 ];
 return {
  name:'Olive Tree · Coimbatore home interiors · '+localDay(now),
  service:'Home interiors',market:'Coimbatore',currency:'INR',dailyBudget:DAILY_BUDGET,
  dailyLeadTarget:DAILY_LEAD_TARGET,targetCpl:DAILY_BUDGET/DAILY_LEAD_TARGET,
  guaranteed:false,objective:'Leads',destination:'Instant form',approval:'required',
  evidenceCount:ads.length,evidenceUrls:ads.map(a=>a.url),themes,
  researchNote:ads.length?'Counts describe only the collected sample; performance and competitor targeting are unknown.':'Baseline test proposal; no current competitor ad evidence was available.',
  experiment:text.includes('kitchen')?'Start with kitchen layout and storage; compare against a project walkthrough.':'Start with a real home project walkthrough; compare against kitchen storage.',
  audience:{location:'Coimbatore service area',approach:'Broad adult audience; confirm service radius in Ads Manager',exclude:'No inferred income, home ownership or competitor audience data'},
  allocation:'One campaign and one ad set, total INR 500/day; three creative options share this budget.',
  variants:[
   {label:'Home walkthrough',primaryText:'Planning your home interiors in Coimbatore? Share your floor plan and requirements with Olive Tree Interiors. Let us discuss a layout that works for your space.',headline:'Home Interiors in Coimbatore',description:'Tell us about your home and project requirements.',cta:'Get Quote',creative:'Use your own approved home project footage: hall, kitchen and wardrobe. Show only work you can substantiate.'},
   {label:'Kitchen and storage',primaryText:'Planning a modular kitchen or better storage for your home? Speak with Olive Tree Interiors in Coimbatore. Share your room dimensions and requirements to start the discussion.',headline:'Plan Your Kitchen & Storage',description:'Discuss your layout and storage requirements.',cta:'Get Quote',creative:'Show actual kitchen storage and wardrobe details. Avoid invented prices, materials, warranties or completion dates.'},
   {label:'Customer experience',primaryText:'Choosing an interior team for your Coimbatore home? Discuss your project with Olive Tree Interiors. Share your floor plan, project area and preferred timeline.',headline:'Discuss Your Home Interior Project',description:'Share your plans with Olive Tree Interiors.',cta:'Get Quote',creative:'Use a customer testimonial only with permission and the original verified statement. Do not generate a fictitious customer.'}
  ],
  leadForm:{type:'Higher intent with review step',required:['Full name','Phone number','Project area','Service type'],optional:['Email','Approximate budget','Project timeline'],privacyUrl:'https://olivetree-ads-manager.britsingh20.workers.dev/privacy',intro:'Share your project details so Olive Tree Interiors can contact you about your enquiry.'},
  reviewChecklist:['Confirm service radius and lead form in the correct ad account.','Select owned project images or video and obtain testimonial permission.','Review copy and privacy notice.','Check all existing active campaign budgets before adding spend.','Confirm Meta spending controls; daily budgets and delayed reporting do not guarantee a hard INR 500 cash ceiling.'],
  performanceRules:{cadenceMinutes:10,metrics:['Spend','Reported leads','Cost per lead','Qualified enquiries','Site visits'],response:'Recommend changes; never automatically increase budget or publish.'},
  missingForPublication:['Approved media asset','Verified campaign/ad set and lead form configuration','Explicit publishing approval']
 };
}
async function read(env,key){const r=await env.DB.prepare('SELECT value FROM state WHERE key=?').bind(key).first();if(!r)return null;try{return JSON.parse(r.value);}catch{return null;}}
async function save(env,key,value){await env.DB.prepare('INSERT INTO state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').bind(key,JSON.stringify(value)).run();}
export async function workflowStatus(env){
 return {configured:Boolean(env.COMPETITOR_FEED_URL),schedule:'Once daily, India time; checked by the ten-minute Worker trigger',latest:await read(env,'campaign_workflow_latest'),lastAttempt:await read(env,'campaign_workflow_attempt'),notification:await read(env,'campaign_workflow_notification')};
}
export async function prepareCampaign(env,{force=false}={}){
 const day=localDay();const existing=await read(env,'campaign_workflow_latest');
 if(!force&&existing?.day===day)return {status:'already_prepared',latest:existing};
 const owner=crypto.randomUUID(),now=Date.now();
 await env.DB.prepare("INSERT INTO locks VALUES ('campaign_workflow',?,?) ON CONFLICT(name) DO UPDATE SET owner=excluded.owner,expires_at=excluded.expires_at WHERE locks.expires_at < ?").bind(owner,now+60000,now).run();
 const lock=await env.DB.prepare("SELECT owner FROM locks WHERE name='campaign_workflow'").first();
 if(lock?.owner!==owner)return {status:'busy'};
 try{
  const latest=await read(env,'campaign_workflow_latest');if(!force&&latest?.day===day)return {status:'already_prepared',latest};
  let research;
  try{research=await readFeed(env);}catch{research={status:'failed',ads:[],reason:'Evidence collection failed validation or the provider was unavailable. Check the configured feed; no current competitor findings are claimed.'};}
  const result={id:crypto.randomUUID(),day,createdAt:new Date().toISOString(),status:'awaiting_review',research,campaign:campaignPlan(research.ads),approvedAt:null};
  // D1 batch makes the new draft and its in-app notification visible together.
  const entries=[
   ['campaign_workflow_latest',result],
   ['campaign_workflow_attempt',{day,at:result.createdAt,status:research.status}],
   ['campaign_workflow_notification',{id:result.id,at:result.createdAt,message:'Home interior campaign proposal ready for review. Research: '+research.status,channel:'dashboard'}]
  ];
  await env.DB.batch(entries.map(([key,value])=>env.DB.prepare('INSERT INTO state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').bind(key,JSON.stringify(value))));
  return {status:'prepared',latest:result};
 }finally{await env.DB.prepare("DELETE FROM locks WHERE name='campaign_workflow' AND owner=?").bind(owner).run();}
}
export async function approveCampaign(env,id){
 if(typeof id!=='string'||!id)throw new Error('Campaign proposal ID required');
 const owner=crypto.randomUUID(),now=Date.now();
 await env.DB.prepare("INSERT INTO locks VALUES ('campaign_workflow',?,?) ON CONFLICT(name) DO UPDATE SET owner=excluded.owner,expires_at=excluded.expires_at WHERE locks.expires_at < ?").bind(owner,now+60000,now).run();
 const lock=await env.DB.prepare("SELECT owner FROM locks WHERE name='campaign_workflow'").first();if(lock?.owner!==owner)throw new Error('Campaign is being updated; refresh and retry');
 try{
  const proposal=await read(env,'campaign_workflow_latest');
  if(!proposal||proposal.id!==id)throw new Error('Proposal changed; review the latest version');
  if(proposal.status==='approved_for_setup')return proposal;
  if(proposal.status!=='awaiting_review')throw new Error('Proposal cannot be approved');
  proposal.status='approved_for_setup';proposal.approvedAt=new Date().toISOString();
  await save(env,'campaign_workflow_latest',proposal);
  return proposal;
 }finally{await env.DB.prepare("DELETE FROM locks WHERE name='campaign_workflow' AND owner=?").bind(owner).run();}
}
