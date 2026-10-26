import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createSupabaseAPI } from '../js/supabase-api.js';
import { validateSubmission, validateSource, canonicalURL } from '../supabase/functions/source-culture/validation.mjs';

const config = { url:'https://source-test.supabase.co', publishableKey:'sb_publishable_public_test_key_1234567890' };
const json = (data,status=200) => new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
const memory = () => { const data=new Map();return {getItem:key=>data.get(key),setItem:(key,value)=>data.set(key,value),removeItem:key=>data.delete(key)}; };
const submission = overrides => ({ kind:'practice',title:'Rice',summary:'A practice',relationship:'personal experience',account:'A firsthand account',
  publication_permission:true,rights_confirmation:true,tags:[],...overrides });

test('public requests use a publishable key and never same-origin cookies',async()=>{
  const requests=[];
  const api=createSupabaseAPI(config,{storage:memory(),request:async(url,options)=>{requests.push({url,options});return json({mode:'supabase'});}});
  assert.deepEqual(await api('/config'),{mode:'supabase'});
  assert.equal(requests[0].options.credentials,'omit');
  assert.equal(requests[0].options.headers.apikey,config.publishableKey);
  assert.equal(requests[0].options.headers.Authorization,undefined);
  assert.equal(new URL(requests[0].url).searchParams.get('path'),'/config');
});
test('verified sessions stay in session storage and bearer headers, with no tokens in URLs',async()=>{
  const storage=memory(),requests=[];
  const api=createSupabaseAPI(config,{storage,clock:()=>100000,request:async(url,options)=>{
    requests.push({url,options});return json(new URL(url).searchParams.get('path')==='/auth/verify'?
      {access_token:'private-access-token',expires_at:200,message:'Signed in.'}:{user:{email:'owner@example.test'},csrf:null});
  }});
  assert.deepEqual(await api('/auth/verify',{token:'single-use-hash'}),{message:'Signed in.'});
  await api('/session');
  assert.equal(requests[1].options.headers.Authorization,'Bearer private-access-token');
  assert.ok(requests.every(({url})=>!url.includes('private-access-token')&&!url.includes('single-use-hash')));
  const reloaded=createSupabaseAPI(config,{storage,clock:()=>100000,request:async(url,options)=>{
    assert.equal(options.headers.Authorization,'Bearer private-access-token');return json({user:{email:'owner@example.test'}});
  }});
  await reloaded('/session');
});
test('expired and rejected sessions are cleared instead of exposing another account',async()=>{
  let time=100000;const storage=memory();
  const api=createSupabaseAPI(config,{storage,clock:()=>time,request:async(url,options)=>{
    if(new URL(url).searchParams.get('path')==='/auth/verify')return json({access_token:'old',expires_at:200});
    if(time>200000){assert.equal(options.headers.Authorization,undefined);return json({user:null});}
    return json({error:'Expired'},401);
  }});
  await api('/auth/verify',{token:'hash'});
  assert.deepEqual(await api('/session'),{user:null,csrf:null});
  await api('/auth/verify',{token:'hash'});time=300000;
  assert.deepEqual(await api('/session'),{user:null});
});
test('public media uses a live proxy and private previews use authenticated blob fetches',async()=>{
  const requests=[];
  const api=createSupabaseAPI(config,{storage:memory(),request:async(url,options)=>{
    const path=new URL(url).searchParams.get('path');requests.push({path,options});
    if(path==='/auth/verify')return json({access_token:'owner',expires_at:Math.floor(Date.now()/1000)+60});
    if(path.startsWith('/media/')){assert.equal(options.headers.Authorization,'Bearer owner');return new Response(new Uint8Array([1,2,3]),{headers:{'Content-Type':'image/webp'}});}
    return json([{id:'entry',media:[{id:'private-image',alt:'Rice'}]}]);
  }});
  const publicEntry=(await api('/practices'))[0];
  assert.match(publicEntry.media[0].url,/functions\/v1\/source-culture/);
  assert.equal(requests.length,1);
  await api('/auth/verify',{token:'hash'});
  const privateEntry = (await api('/mine'))[0];
  assert.equal(privateEntry.media[0].url,'');
  assert.ok(!requests.some(request=>request.path.startsWith('/media/')));
  assert.match((await api.loadPrivateMedia(privateEntry)).media[0].url,/^blob:/);
  assert.equal(requests.at(-1).path,'/media/private-image');
});
test('failed writes preserve the payload and do not retry or use a public snapshot',async()=>{
  let calls=0;const payload=submission();
  const api=createSupabaseAPI(config,{storage:memory(),request:async()=>{calls++;return json({error:'Could not save'},503);}});
  await assert.rejects(api('/submissions',payload),/Could not save/);
  assert.equal(calls,1);assert.equal(payload.title,'Rice');
});
test('submission validation excludes identity, editor, and storage fields',()=>{
  const result=validateSubmission(submission({editor:true,verified:true,email:'private@example.test',owner_id:'spoof',media:[{storage_key:'spoof'}],external_url:'javascript:alert(1)'}));
  for(const key of ['editor','verified','email','owner_id','media','external_url'])assert.equal(result.content[key],undefined);
  assert.equal(result.content.display_name,'anonymous contributor');
});
test('firsthand accounts need no citation while research accounts do',()=>{
  assert.equal(validateSubmission(submission()).content.references.length,0);
  assert.throws(()=>validateSubmission(submission({relationship:'source-based research'})),/identified source/);
  assert.throws(()=>validateSubmission(submission({publication_permission:'true'})),/permission/);
});
test('print and oral sources work without URLs and retain permission checks',()=>{
  assert.equal(validateSource({type:'book or chapter',title:'A print reference'}).url,'');
  assert.throws(()=>validateSource({type:'interview or oral account',title:'A conversation'}),/permission/);
  assert.equal(validateSource({type:'interview or oral account',title:'A conversation',oral_permission:true}).oral_permission,true);
  for(const url of ['javascript:alert(1)','https://user:password@example.test/file'])assert.throws(()=>validateSource({type:'blog or essay',title:'Source',url}),/HTTP/);
});
test('citations must point at existing passages and deduplication strips tracking',()=>{
  assert.throws(()=>validateSubmission(submission({references:[{type:'book or chapter',title:'A book',block_id:'story'}]})),/empty passage/);
  assert.equal(canonicalURL('https://example.test/read/?utm_source=tracking&edition=2#page'),'https://example.test/read?edition=2');
});
test('images need permissions, descriptions, and a combined limit of four',()=>{
  for(const images of [[{data:'AAAA',alt:'Rice'}],[{data:'AAAA',permission:true}]])assert.throws(()=>validateSubmission(submission({images})),/permission|alt/);
  assert.throws(()=>validateSubmission(submission({images:[{data:'AAAA',alt:'Rice',permission:true}],keep_media:['1','2','3','4']})),/four/);
});
