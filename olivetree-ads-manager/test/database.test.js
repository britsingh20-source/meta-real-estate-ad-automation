import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {metricNumber,actionCount} from '../src/rules.js';
import {HTML} from '../src/ui.js';
test('real metrics schema accepts and upserts the Worker insert',async()=>{
 const db=new DatabaseSync(':memory:');
 try {
  db.exec(readFileSync(new URL('../schema.sql',import.meta.url),'utf8'));
  const source=readFileSync(new URL('../src/worker.js',import.meta.url),'utf8');
  const start=source.indexOf('async function saveMetric('),end=source.indexOf('\nasync function sync(',start);
  assert.ok(start>=0&&end>start);
  const saveMetric=new Function('metricNumber','actionCount','stamp',source.slice(start,end)+';return saveMetric;')(metricNumber,actionCount,()=>new Date().toISOString());
  const env={DB:{prepare(sql){return {bind(...args){return {run:async()=>db.prepare(sql).run(...args)}}}}}};
  await saveMetric(env,'2026-10-20','account','test-account','Test',{spend:'500',impressions:'100',clicks:'10',actions:[{action_type:'lead',value:'10'}]});
  await saveMetric(env,'2026-10-20','account','test-account','Test',{spend:'450',impressions:'90',clicks:'9',actions:[{action_type:'lead',value:'9'}]});
  const row=db.prepare('SELECT spend,leads FROM metrics').get();
  assert.equal(row.spend,450);assert.equal(row.leads,9);assert.equal(db.prepare('SELECT count(*) AS n FROM metrics').get().n,1);
 }finally{db.close();}
});
test('embedded browser script parses',()=>{const script=HTML.match(/<script>([\s\S]*?)<\/script>/)[1];assert.doesNotThrow(()=>new Function(script));});
