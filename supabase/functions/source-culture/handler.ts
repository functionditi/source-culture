import { createClient } from 'npm:@supabase/supabase-js@2.118.0';
import { ACTIVITIES, SOURCE_TYPES, RELATIONSHIPS, APIError, object, email, validateSubmission } from './validation.mjs';
import { cleanImage } from './images.ts';

const url = Deno.env.get('SUPABASE_URL')!;
const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS') || '{}').default;
const publicKey = Deno.env.get('SUPABASE_ANON_KEY') || JSON.parse(Deno.env.get('SUPABASE_PUBLISHABLE_KEYS') || '{}').default;
const appURL = new URL(Deno.env.get('APP_URL') || 'http://127.0.0.1:8001/source-culture/');
if (!appURL.pathname.endsWith('/')) throw new Error('APP_URL must end with /.');
const editors = new Set((Deno.env.get('EDITOR_EMAILS') || '').split(',').map(value=>value.trim().toLowerCase()).filter(Boolean));
const clientOptions = { auth: { persistSession:false, autoRefreshToken:false, detectSessionInUrl:false } };
const db = createClient(url,serviceKey,clientOptions);
const bucket = db.storage.from('source-culture-media');

async function rpc(name: string, params: Record<string,unknown>) {
  const { data,error } = await db.rpc(name,params);
  if (error) {
    const status=Number(error.details);
    if (error.code==='P0001' && status>=400 && status<=499) throw new APIError(status,error.message);
    // Never print SQL details, request bodies, auth tokens, or email addresses.
    console.error('Source Culture database request failed',error.code);
    throw new APIError(503,'The notebook could not be reached. Please try again.');
  }
  return data;
}
function headers(origin: string|null) {
  return {
    ...(origin===appURL.origin ? {'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Headers':'authorization, apikey, content-type','Access-Control-Allow-Methods':'GET, POST, OPTIONS'}:{}),
    'Vary':'Origin','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'
  };
}
async function readJSON(req: Request) {
  if (req.headers.get('content-type')?.split(';')[0]!=='application/json') throw new APIError(415,'Use a JSON request.');
  const reader=req.body?.getReader();
  if (!reader) throw new APIError(400,'Expected a request object.');
  const chunks:Uint8Array[]=[];let length=0;
  try {
    while (true) {
      const {value,done}=await reader.read();if(done)break;
      length+=value.length;if(length>29*1024*1024){await reader.cancel();throw new APIError(413,'This request is too large.');}chunks.push(value);
    }
    const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    return object(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
  } catch(error) {
    if(error instanceof APIError)throw error;
    throw new APIError(400,'The request could not be read. Your input has been preserved.');
  } finally {reader.releaseLock();}
}
async function checkRate(req: Request,path:string,identity:string|null) {
  const group=path.startsWith('/auth/')?'auth':'write';
  const address=req.headers.get('x-forwarded-for')?.split(',').at(-1)?.trim() || 'anonymous';
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`${group}:${identity||address}`));
  const key=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  if(!await rpc('source_culture_rate_limit',{p_key:key,p_limit:group==='auth'?12:40,p_seconds:600})) throw new APIError(429,'Too many requests. Please wait a few minutes and try again.');
  // A blocked caller must not keep consuming the shared allowance.
  if (!await rpc('source_culture_rate_limit',{p_key:`global:${group}`,p_limit:group==='auth'?200:120,p_seconds:600})) throw new APIError(429,'Too many requests. Please wait a few minutes and try again.');
}

export async function handleRequest(req: Request): Promise<Response> {
  const origin=req.headers.get('origin');
  const common=headers(origin);
  const uploaded:string[]=[];
  try {
    if (origin && origin!==appURL.origin) throw new APIError(403,'This request must come from this website.');
    if(req.method==='OPTIONS')return new Response(null,{status:204,headers:common});
    if(!['GET','POST'].includes(req.method))throw new APIError(405,'Use GET or POST.');
    if(req.method==='POST' && origin!==appURL.origin)throw new APIError(403,'This request must come from this website.');
    const path=new URL(req.url).searchParams.get('path') || '/config';
    if(path.length>250 || !/^\/[a-zA-Z0-9_\/-]+$/.test(path))throw new APIError(404,'API route not found.');
    let person:null|{id:string,email:string}=null;
    const authorization=req.headers.get('authorization');
    if(authorization){
      const token=authorization.match(/^Bearer (.+)$/i)?.[1];
      if(!token)throw new APIError(401,'Sign in again to continue.');
      const {data,error}=await db.auth.getUser(token);
      if(error || !data.user?.email || !data.user.email_confirmed_at)throw new APIError(401,'Your session has expired. Request a new sign-in link.');
      person={id:data.user.id,email:data.user.email.toLowerCase()};
    }
    if(req.method==='GET' && path==='/config')return Response.json({mode:'supabase',activities:ACTIVITIES,source_types:SOURCE_TYPES,relationships:RELATIONSHIPS},{headers:common});
    let payload:Record<string,any>={};
    if(req.method==='POST'){
      await checkRate(req,path,person?.id||null);
      payload=await readJSON(req);
      if(path==='/auth/request'){
        const auth=createClient(url,publicKey,clientOptions);
        const {error}=await auth.auth.signInWithOtp({email:email(payload.email),options:{emailRedirectTo:new URL('manage/',appURL).href}});
        if(error)throw new APIError(error.status===429?429:503,'The sign-in email could not be sent. Please try again shortly.');
        return Response.json({message:'Check your inbox for a single-use link. It expires in 15 minutes.'},{headers:common});
      }
      if(path==='/auth/verify'){
        if(typeof payload.token!=='string' || payload.token.length>200)throw new APIError(400,'This sign-in link is invalid.');
        const auth=createClient(url,publicKey,clientOptions);
        const {data,error}=await auth.auth.verifyOtp({token_hash:payload.token,type:'email'});
        if(error || !data.session)throw new APIError(401,'This link has expired or was already used. Request a new link.');
        // Never return or persist a refresh token. Access lasts only this session.
        return Response.json({access_token:data.session.access_token,expires_at:data.session.expires_at,message:'Signed in.'},{headers:common});
      }
      if(path==='/auth/logout'){
        if(person){
          const {error}=await db.auth.admin.signOut(authorization!.slice(7),'local');
          if(error)throw new APIError(503,'Sign-out could not be completed. Please try again.');
        }
        return Response.json({message:'Signed out.'},{headers:common});
      }
      if(path==='/submissions' || /^\/submissions\/[^/]+\/revisions$/.test(path)){
        // Validation returns an allowlist; identity, editor roles and storage keys
        // supplied by a caller are discarded before the transaction starts.
        const validated=validateSubmission(payload);
        const privateEmail=person?.email || email(payload.email);
        const media=[];
        for(const image of validated.images){
          const bytes=await cleanImage(image.data),id=crypto.randomUUID(),key=`${id}.webp`;
          const {error}=await bucket.upload(key,bytes,{contentType:'image/webp',upsert:false,cacheControl:'0'});
          if(error)throw new APIError(503,'The image could not be saved. Please try again.');
          uploaded.push(key);
          const {data:discard,...metadata}=image;
          media.push({...metadata,id,storage_key:key});
        }
        const {images:discard,...safe}=validated;
        payload={...safe,media,email:privateEmail};
      }
    }
    const result=await rpc('source_culture_api',{p_path:path,p_method:req.method,p_payload:payload,
      p_email:person?.email||null,p_editor:!!person && editors.has(person.email)});
    if(req.method==='GET' && /^\/media\/[^/]+$/.test(path)){
      // A proxy rechecks live publication on every request. Signed storage URLs
      // would continue working after withdrawal, so they are never returned.
      const {data,error}=await bucket.download(result.storage_key);
      if(error || !data)throw new APIError(404,'Image unavailable.');
      return new Response(data,{headers:{...common,'Content-Type':'image/webp'}});
    }
    return Response.json(result,{status:req.method==='POST' && path==='/submissions'?201:200,headers:common});
  }catch(error){
    if(uploaded.length){
      // A network error can occur after a transaction committed. Check database
      // references before deleting so an uncertain response cannot lose images.
      try {
        const unused=await rpc('source_culture_unused_media',{p_keys:uploaded});
        if(unused.length)await bucket.remove(unused);
      }catch{/* Preserve private objects for later cleanup if the DB is offline. */}
    }
    const known=error instanceof APIError;
    if(!known)console.error('Source Culture request failed',error instanceof Error?error.name:'UnknownError');
    return Response.json({error:known?error.message:'The server could not complete the request. Your input has been preserved.'},{status:known?error.status:500,headers:common});
  }
}
