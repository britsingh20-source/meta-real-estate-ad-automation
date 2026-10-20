
export const ACCOUNT = '464678014577329';
export const DAILY_BUDGET = 500;
export const DAILY_LEAD_TARGET = 10;
export const STAGES = ['new','contacted','qualified','site_visit','quotation','won','lost','invalid'];
export function localDay(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
}
export function metricNumber(value) {
  if (value === undefined || value === null || value === '') throw new Error('Incomplete Meta metric');
  const n=Number(value); if(!Number.isFinite(n)||n<0)throw new Error('Invalid Meta metric'); return n;
}
export function actionCount(actions, type) {
  if(actions===undefined)return 0;
  if(!Array.isArray(actions))throw new Error('Invalid action data');
  const a=actions.find(a=>a.action_type===type); return a?metricNumber(a.value):0;
}
export function assessment(rows) {
  const total=rows.reduce((a,r)=>({spend:a.spend+metricNumber(r.spend),leads:a.leads+metricNumber(r.leads)}),{spend:0,leads:0});
  return {...total,cpl:total.leads?total.spend/total.leads:null,needed:Math.max(0,DAILY_LEAD_TARGET-total.leads),targetCpl:DAILY_BUDGET/DAILY_LEAD_TARGET};
}
export function guardDecision({mode,currency,timezone,spend,fresh,managed}) {
  if(mode!=='budget_guard')return {action:'observe',reason:'Observation mode'};
  if(currency!=='INR'||timezone!=='Asia/Kolkata')return {action:'block',reason:'Validate INR currency and India reporting timezone'};
  if(!fresh||!Number.isFinite(spend)||spend<0)return {action:'block',reason:'Missing or stale spend'};
  if(spend>=DAILY_BUDGET&&managed)return {action:'pause',reason:'Account reported spend reached INR 500; pause only app-managed ads'};
  return {action:'observe',reason:'No budget guard action required'};
}
export function validateDraft(d) {
  if(typeof d.name!=='string'||!d.name.trim()||d.name.length>150)throw new Error('Enter a draft name');
  if(!/^\d+$/.test(d.adset_id)||!/^\d+_\d+$/.test(d.post_id))throw new Error('Use a valid ad set ID and Page post ID');
  return {name:d.name.trim(),adset_id:d.adset_id,post_id:d.post_id};
}
