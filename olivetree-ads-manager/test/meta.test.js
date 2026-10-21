import test from 'node:test';
import assert from 'node:assert/strict';
import {list,accountInfo,ready} from '../src/meta.js';
const env={META_ACCESS_TOKEN:'test-only',META_API_VERSION:'v26.0'};
test('missing connection never calls Meta',()=>{assert.equal(ready({}),false);});
test('pagination collects every page and uses bearer auth',async()=>{const prev=globalThis.fetch;let calls=0;globalThis.fetch=async(url,opts)=>{assert.equal(opts.headers.Authorization,'Bearer test-only');assert.equal(url.searchParams.has('access_token'),false);calls++;return Response.json(calls===1?{data:[{id:'1'}],paging:{next:'https://ignored.example/',cursors:{after:'cursor'}}}:{data:[{id:'2'}]});};try{assert.deepEqual(await list(env,'act_464678014577329/ads'),[{id:'1'},{id:'2'}]);assert.equal(calls,2);}finally{globalThis.fetch=prev;}});
test('partial pagination fails closed',async()=>{const prev=globalThis.fetch;globalThis.fetch=async()=>Response.json({data:[{id:'1'}],paging:{next:'https://ignored.example/'}});try{await assert.rejects(()=>list(env,'ads'),/cursor missing/);}finally{globalThis.fetch=prev;}});
test('wrong account is rejected',async()=>{const prev=globalThis.fetch;globalThis.fetch=async()=>Response.json({account_id:'999',currency:'INR',timezone_name:'Asia/Kolkata'});try{await assert.rejects(()=>accountInfo(env),/Wrong Meta account/);}finally{globalThis.fetch=prev;}});
