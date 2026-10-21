
import {ACCOUNT} from './rules.js';
export function ready(env) { return Boolean(env.META_ACCESS_TOKEN && /^v\d+\.0$/.test(env.META_API_VERSION||'')); }
export async function graph(env,path,params={},method='GET',token=env.META_ACCESS_TOKEN) {
  if(!ready(env)||!token)throw new Error('Direct Meta connection is not configured');
  const url=new URL('https://graph.facebook.com/'+env.META_API_VERSION+'/'+path);
  const headers={Authorization:'Bearer '+token};
  const opts={method,headers,signal:AbortSignal.timeout(20000)};
  const form=new URLSearchParams();
  for(const [k,v]of Object.entries(params))form.set(k,typeof v==='object'?JSON.stringify(v):String(v));
  if(method==='GET')url.search=form.toString();else opts.body=form;
  const res=await fetch(url,opts); const body=await res.json();
  if(!res.ok||body.error)throw new Error('Meta request failed: '+(body.error?.code||res.status));
  return body;
}
export async function list(env,path,params={}) {
  const data=[];let after;
  for(let page=0;page<100;page++){
    const body=await graph(env,path,{...params,limit:100,...(after?{after}:{})});
    if(!Array.isArray(body.data))throw new Error('Incomplete Meta list response');
    data.push(...body.data);
    if(!body.paging?.next)return data;
    after=body.paging?.cursors?.after;
    if(!after)throw new Error('Meta pagination cursor missing');
  }
  throw new Error('Meta pagination limit reached; do not use partial data');
}
export async function accountInfo(env) {
  const a=await graph(env,'act_'+ACCOUNT,{fields:'account_id,name,currency,timezone_name,account_status'});
  if(String(a.account_id)!==ACCOUNT)throw new Error('Wrong Meta account');
  if(a.currency!=='INR'||a.timezone_name!=='Asia/Kolkata')throw new Error('Account must report INR in Asia/Kolkata');
  return a;
}
