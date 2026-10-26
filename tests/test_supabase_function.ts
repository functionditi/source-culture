// The real handler and Supabase client run against deterministic Auth/REST/Storage
// responses. No production credentials, actual emails, or remote writes are used.
const app='https://functionditi.github.io';
Deno.env.set('SUPABASE_URL','https://source-test.supabase.co');
Deno.env.set('SUPABASE_SERVICE_ROLE_KEY','sb_secret_synthetic_test');
Deno.env.set('SUPABASE_ANON_KEY','sb_publishable_synthetic_test');
Deno.env.set('APP_URL',app+'/source-culture/');
Deno.env.set('EDITOR_EMAILS','editor@example.test');
const {handleRequest}=await import('../supabase/functions/source-culture/handler.ts');
function assert(value:unknown,message='Assertion failed'){if(!value)throw new Error(message);}
const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
const calls:{path:string,url:string,body:Record<string,any>}[]=[];
function mock() {
  const original=globalThis.fetch;calls.length=0;
  globalThis.fetch=async(input,options)=>{
    const url=String(input),path=new URL(url).pathname;
    const body=JSON.parse(String(options?.body||'{}'));calls.push({path,url,body});
    if(path.endsWith('/source_culture_rate_limit'))return json(true);
    if(path==='/auth/v1/user'){
      const token=new Headers(options?.headers).get('authorization');
      if(token==='Bearer valid-editor')return json({id:'editor-id',email:'editor@example.test',email_confirmed_at:'2026-10-26T00:00:00Z',user_metadata:{}});
      if(token==='Bearer forged-role')return json({id:'owner-id',email:'owner@example.test',email_confirmed_at:'2026-10-26T00:00:00Z',user_metadata:{editor:true}});
      return json({message:'Invalid JWT',code:'bad_jwt'},401);
    }
    if(path==='/auth/v1/otp')return json({});
    if(path==='/auth/v1/verify')return json({access_token:'synthetic-session',refresh_token:'never-return-this',expires_in:3600,expires_at:2000000000,token_type:'bearer',user:{id:'owner-id',email:'owner@example.test'}});
    if(path.endsWith('/source_culture_api'))return json({message:'Saved'});
    return json({message:'Unexpected test request'},500);
  };
  return ()=>{globalThis.fetch=original;};
}
function request(path:string,body?:unknown,token?:string,origin=app){
  return new Request('https://source-test.supabase.co/functions/v1/source-culture?path='+encodeURIComponent(path),{
    method:body===undefined?'GET':'POST',headers:{Origin:origin,...(body===undefined?{}:{'Content-Type':'application/json'}),...(token?{Authorization:'Bearer '+token}:{})},
    ...(body===undefined?{}:{body:JSON.stringify(body)})});
}
Deno.test('cross-origin writes and preflight checks happen before Auth or database access',async()=>{
  const restore=mock();try{
    const denied=await handleRequest(request('/submissions',{},undefined,'https://other.test'));
    assert(denied.status===403);assert(!denied.headers.has('Access-Control-Allow-Origin'));assert(calls.length===0);
    const preflight=await handleRequest(new Request('https://source-test.supabase.co/functions/v1/source-culture',{method:'OPTIONS',headers:{Origin:app}}));
    assert(preflight.status===204);assert(preflight.headers.get('Access-Control-Allow-Origin')===app);
  }finally{restore();}
});
Deno.test('invalid bearer tokens are rejected and profile metadata cannot grant editor access',async()=>{
  const restore=mock();try{
    assert((await handleRequest(request('/admin',undefined,'bad-token'))).status===401);
    assert(!calls.some(call=>call.path.endsWith('/source_culture_api')));
    await handleRequest(request('/admin',undefined,'forged-role'));
    const user=calls.findLast(call=>call.path.endsWith('/source_culture_api'))!;
    assert(user.body.p_email==='owner@example.test'&&user.body.p_editor===false);
    await handleRequest(request('/admin',undefined,'valid-editor'));
    assert(calls.at(-1)!.body.p_editor===true);
  }finally{restore();}
});
Deno.test('anonymous submissions ignore claimed roles and identities',async()=>{
  const restore=mock();try{
    const result=await handleRequest(request('/submissions',{kind:'practice',title:'Rice',summary:'A practice',account:'An account',relationship:'personal experience',
      email:'owner@example.test',publication_permission:true,rights_confirmation:true,editor:true,owner_id:'spoof',verified:true,media:[{storage_key:'spoof'}]}));
    assert(result.status===201);
    const transaction=calls.at(-1)!.body;
    assert(transaction.p_email===null&&transaction.p_editor===false);
    assert(!transaction.p_payload.content.editor&&!transaction.p_payload.content.owner_id);
    assert(transaction.p_payload.media.length===0);
  }finally{restore();}
});
Deno.test('sign-in uses the project redirect and never returns a refresh token',async()=>{
  const restore=mock();try{
    assert((await handleRequest(request('/auth/request',{email:'owner@example.test'}))).status===200);
    const otp=calls.find(call=>call.path==='/auth/v1/otp')!;
    assert(new URL(otp.url).searchParams.get('redirect_to')===app+'/source-culture/manage/');
    const result=await (await handleRequest(request('/auth/verify',{token:'single-use-hash'}))).json();
    assert(result.access_token==='synthetic-session');
    assert(!('refresh_token' in result));
  }finally{restore();}
});
Deno.test('a blocked caller does not consume global request allowances',async()=>{
  const original=globalThis.fetch;let chargedGlobal=false;
  globalThis.fetch=async(_url,options)=>{
    const body=JSON.parse(String(options?.body||'{}'));
    if(String(body.p_key).startsWith('global:'))chargedGlobal=true;
    return json(false);
  };
  try{
    const result=await handleRequest(request('/auth/request',{email:'owner@example.test'}));
    assert(result.status===429);assert(!chargedGlobal);
  }finally{globalThis.fetch=original;}
});
