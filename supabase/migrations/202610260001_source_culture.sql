-- Raw records are deliberately outside PostgREST's exposed public schema.
-- The only API RPC is executable by service_role, never a browser key.
create schema if not exists source_culture;
revoke all on schema source_culture from public, anon, authenticated;

create table source_culture.contributors (
  id text primary key default gen_random_uuid()::text,
  email text not null unique check (email = lower(email)),
  verified boolean not null default false,
  created_at timestamptz not null default now()
);
create table source_culture.entities (
  id text primary key default gen_random_uuid()::text,
  kind text not null check (kind in ('practice','variation','source','correction')),
  slug text not null unique,
  owner_id text references source_culture.contributors,
  parent_id text references source_culture.entities,
  target_id text references source_culture.entities,
  status text not null default 'submitted' check (status in ('submitted','needs changes','published','declined','withdrawn')),
  published_revision_id text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table source_culture.revisions (
  id text primary key default gen_random_uuid()::text,
  entity_id text not null references source_culture.entities,
  number integer not null, content jsonb not null,
  state text not null default 'submitted' check (state in ('submitted','needs changes','published','declined')),
  created_at timestamptz not null default now(), unique (entity_id, number), unique(entity_id, id)
);
alter table source_culture.entities add constraint published_revision_belongs_to_entity
  foreign key (id, published_revision_id) references source_culture.revisions(entity_id, id);
create table source_culture.citations (
  id text primary key default gen_random_uuid()::text,
  revision_id text not null references source_culture.revisions,
  source_id text not null references source_culture.entities,
  block_id text check (block_id in ('story','account','judgement')), relationship text not null,
  locator text not null default '', annotation text not null default ''
);
create table source_culture.media (
  id text primary key default gen_random_uuid()::text,
  revision_id text not null references source_culture.revisions,
  owner_id text not null references source_culture.contributors,
  storage_key text not null, alt text not null, caption text not null default '',
  credit text not null default '', licence text not null default 'no additional reuse licence'
);
create table source_culture.permissions (
  revision_id text primary key references source_culture.revisions,
  owner_id text not null references source_culture.contributors,
  consent_version text not null default '2026-10-v1', publication boolean not null default true,
  reuse text not null, created_at timestamptz not null default now()
);
create table source_culture.confirmations (
  revision_id text primary key references source_culture.revisions,
  owner_id text not null references source_culture.contributors, created_at timestamptz not null default now()
);
create table source_culture.reviews (
  id text primary key default gen_random_uuid()::text,
  entity_id text not null references source_culture.entities,
  revision_id text not null references source_culture.revisions,
  editor_id text not null references source_culture.contributors,
  action text not null, feedback text not null, created_at timestamptz not null default now()
);
create table source_culture.messages (
  id text primary key default gen_random_uuid()::text,
  entity_id text not null references source_culture.entities,
  author_id text not null references source_culture.contributors,
  body text not null, created_at timestamptz not null default now()
);
create table source_culture.rate_limits (
  key text primary key, count integer not null, expires timestamptz not null
);
create index on source_culture.entities(status, kind);
create index on source_culture.revisions(entity_id, number desc);
create index on source_culture.citations(revision_id);
create index on source_culture.media(revision_id);

-- RLS has no browser policies. Even accidental table grants remain closed.
do $$ declare t text; begin
  foreach t in array array['contributors','entities','revisions','citations','media','permissions','confirmations','reviews','messages','rate_limits'] loop
    execute format('alter table source_culture.%I enable row level security', t);
  end loop;
end $$;

create function source_culture.fail(code integer, message text) returns void
language plpgsql set search_path = source_culture, pg_temp as $$
begin raise exception using message = message, detail = code::text, errcode = 'P0001'; end $$;

create function source_culture.visible(ident text) returns boolean
language sql stable set search_path = source_culture, pg_temp as $$
  with recursive ancestors as (
    select id,parent_id,status,published_revision_id,array[id] trail,false cycle from entities where id=ident
    union all
    select e.id,e.parent_id,e.status,e.published_revision_id,a.trail||e.id,e.id=any(a.trail)
      from ancestors a join entities e on e.id=a.parent_id
      where not a.cycle and cardinality(a.trail)<100
  ) select exists(select 1 from ancestors where parent_id is null)
      and not exists(select 1 from ancestors where status<>'published' or published_revision_id is null or cycle);
$$;

create function source_culture.public_content(content jsonb) returns jsonb
language sql immutable set search_path = source_culture, pg_temp as $$
  select coalesce(jsonb_object_agg(key, value), '{}'::jsonb) from jsonb_each(content)
  where key = any(array['title','summary','original_name','language','context','place','community',
    'relationship','account','materials','steps','judgement','similar','changes','prompt','display_name',
    'reuse','entry_type','tags','editorial','project_status','account_heading','placeholder','external_url','source']);
$$;

create function source_culture.media_json(revision text) returns jsonb
language sql stable set search_path = source_culture, pg_temp as $$
  select coalesce(jsonb_agg(jsonb_build_object('id',id,'alt',alt,'caption',caption,'credit',credit,'licence',licence) order by id),'[]')
  from media where revision_id=revision;
$$;

create function source_culture.public_entry(ident text) returns jsonb
language sql stable set search_path = source_culture, pg_temp as $$
  select public_content(r.content) || jsonb_build_object('id',e.id,'slug',e.slug,'kind',e.kind,
    'parent_id',e.parent_id,'demo',false,'revision',r.number,'created_at',e.created_at,'updated_at',r.created_at,
    'media',media_json(r.id),'citations',coalesce((select jsonb_agg(jsonb_build_object(
      'id',c.id,'source_id',c.source_id,'block_id',c.block_id,'relationship',c.relationship,
      'locator',c.locator,'annotation',c.annotation) order by c.id) from citations c
      where c.revision_id=r.id and visible(c.source_id)), '[]'::jsonb))
  from entities e join revisions r on r.id=e.published_revision_id where e.id=ident and visible(e.id);
$$;

create function source_culture.private_entry(ident text, actor text, editor boolean) returns jsonb
language plpgsql stable set search_path = source_culture, pg_temp as $$
declare e entities; r revisions; c jsonb; refs jsonb;
begin
  select * into e from entities where id=ident;
  select * into r from revisions where entity_id=ident order by number desc limit 1;
  c := r.content;
  if e.kind in ('practice','variation') then
    select coalesce(jsonb_agg(s.content->'source' || jsonb_build_object('source_id',ref.source_id,
      'relation',ref.relationship,'locator',ref.locator,'annotation',ref.annotation,'block_id',coalesce(ref.block_id,'')) order by ref.id),'[]')
    into refs from citations ref join entities se on se.id=ref.source_id
    join lateral (select content from revisions where entity_id=se.id and
      (editor or se.owner_id=actor or (id=se.published_revision_id and visible(se.id))) order by number desc limit 1) s on true
    where ref.revision_id=r.id;
    c := jsonb_set(c,'{references}',refs);
  end if;
  return jsonb_build_object('id',e.id,'kind',e.kind,'slug',e.slug,'parent_id',e.parent_id,'target_id',e.target_id,
    'status',e.status,'published_revision_id',e.published_revision_id,'demo',false,'created_at',e.created_at,
    'updated_at',e.updated_at,'content',c,'revision_id',r.id,'number',r.number,'revision_state',r.state,
    'email',(select email from contributors where id=e.owner_id),
    'email_verified',coalesce((select verified from contributors where id=e.owner_id),false),
    'permission',(select jsonb_build_object('publication',publication,'reuse',reuse,'consent_version',consent_version,'created_at',created_at)
      from permissions where revision_id=r.id), 'confirmed',exists(select 1 from confirmations where revision_id=r.id),
    'published_content',(select content from revisions where id=e.published_revision_id), 'media',media_json(r.id),
    'feedback',coalesce((select jsonb_agg(jsonb_build_object('action',action,'feedback',feedback,'created_at',created_at) order by created_at desc,id desc)
      from reviews where entity_id=e.id),'[]'),
    'messages',coalesce((select jsonb_agg(jsonb_build_object('body',body,'created_at',created_at,'author_id',author_id) order by created_at,id)
      from messages where entity_id=e.id),'[]'));
end $$;

create function source_culture.insert_entity(actor text, kind text, content jsonb, parent text default null, target text default null)
returns source_culture.revisions language plpgsql set search_path = source_culture, pg_temp as $$
declare ident text := gen_random_uuid()::text; r revisions;
begin
  insert into entities(id,kind,slug,owner_id,parent_id,target_id) values(ident,kind,
    coalesce(nullif(left(trim(both '-' from regexp_replace(lower(content->>'title'),'[^a-z0-9]+','-','g')),70),''),'practice')||'-'||left(ident,8),actor,parent,target);
  insert into revisions(entity_id,number,content) values(ident,1,content) returning * into r;
  return r;
end $$;

create function source_culture.confirm_revision(revision text, actor text) returns void
language plpgsql set search_path = source_culture, pg_temp as $$
begin
  insert into confirmations(revision_id,owner_id) values(revision,actor) on conflict do nothing;
  insert into confirmations(revision_id,owner_id)
    select r.id,actor from citations c join entities e on e.id=c.source_id
    join lateral(select id from revisions where entity_id=e.id order by number desc limit 1) r on true
    where c.revision_id=revision and e.owner_id=actor on conflict do nothing;
end $$;

create function source_culture.save_revision(r source_culture.revisions, actor text, payload jsonb) returns void
language plpgsql set search_path = source_culture, pg_temp as $$
declare item jsonb; m media; s entities; metadata jsonb; sid text; sr revisions; changed boolean;
  bibliographic text[] := array['type','title','creators','date','url','doi','venue','volume','pages','publisher','edition','chapter','isbn','platform','duration','interviewer','recording','translation','custom_type'];
begin
  insert into permissions(revision_id,owner_id,reuse) values(r.id,actor,coalesce(r.content->>'reuse','credit; no additional reuse licence'));
  for item in select value from jsonb_array_elements(coalesce(payload->'media','[]')) loop
    insert into media(id,revision_id,owner_id,storage_key,alt,caption,credit,licence) values(
      item->>'id',r.id,actor,item->>'storage_key',item->>'alt',item->>'caption',item->>'credit',item->>'licence');
  end loop;
  for item in select value from jsonb_array_elements(coalesce(payload->'keep_media','[]')) loop
    select * into m from media where id=item#>>'{}' and owner_id=actor;
    if not found then perform fail(403,'You cannot attach that image.'); end if;
    insert into media(revision_id,owner_id,storage_key,alt,caption,credit,licence)
      values(r.id,actor,m.storage_key,m.alt,m.caption,m.credit,m.licence);
  end loop;
  for item in select value from jsonb_array_elements(coalesce(r.content->'references','[]')) loop
    sid := null; changed := false;
    if coalesce(item->>'source_id','')<>'' then
      select * into s from entities where id=item->>'source_id' and kind='source';
      if not found or s.status='withdrawn' or not (visible(s.id) or s.owner_id=actor) then perform fail(422,'A linked source is unavailable. Remove it or ask an editor to clarify the reference.'); end if;
      select content->'source' into metadata from revisions where entity_id=s.id and (s.owner_id=actor or id=s.published_revision_id) order by number desc limit 1;
      select exists(select 1 from unnest(bibliographic) k where coalesce(item->>k,'')<>coalesce(metadata->>k,'')) into changed;
      if not changed then sid := s.id; end if;
    end if;
    if sid is null and not changed and (coalesce(item->>'canonical_url','')<>'' or coalesce(item->>'canonical_doi','')<>'') then
      select e.id into sid from entities e join revisions rev on rev.id=e.published_revision_id
      where e.kind='source' and visible(e.id) and
        ((coalesce(item->>'canonical_url','')<>'' and item->>'canonical_url'=rev.content#>>'{source,canonical_url}') or
         (coalesce(item->>'canonical_doi','')<>'' and item->>'canonical_doi'=rev.content#>>'{source,canonical_doi}'))
        and not exists(select 1 from unnest(array['edition','title','creators','date']) k
          where coalesce(item->>k,'')<>coalesce(rev.content->'source'->>k,'')) limit 1;
    end if;
    if sid is null then
      sr := insert_entity(actor,'source',jsonb_build_object('title',item->>'title','source',item,
        'display_name',r.content->>'display_name','tags',r.content->'tags','reuse',r.content->>'reuse'));
      sid := sr.entity_id;
      insert into permissions(revision_id,owner_id,reuse) values(sr.id,actor,r.content->>'reuse');
    end if;
    insert into citations(revision_id,source_id,block_id,relationship,locator,annotation)
      values(r.id,sid,nullif(item->>'block_id',''),item->>'relation',item->>'locator',item->>'annotation');
  end loop;
end $$;

create function source_culture.link_sources(source text, links jsonb) returns void
language plpgsql set search_path = source_culture, pg_temp as $$
declare item jsonb; e entities; content jsonb; block text;
begin
  if jsonb_typeof(links)<>'array' or jsonb_array_length(links)>50 then perform fail(422,'Use at most 50 source connections.'); end if;
  for item in select value from jsonb_array_elements(links) loop
    select * into e from entities where id=item->>'practice_id' for share;
    if not found or not visible(e.id) or e.kind not in ('practice','variation') then perform fail(422,'Source connections need published practices.'); end if;
    if coalesce(item->>'relationship','') not in ('documents this practice','supports this specific claim','informs this interpretation','offers a related example','further reading or viewing')
      or length(trim(coalesce(item->>'annotation','')))=0 then perform fail(422,'Explain how the source relates to each practice.'); end if;
    block := nullif(item->>'block_id','');
    if block is not null and block not in ('story','account','judgement') then perform fail(422,'Choose a stable passage identifier.'); end if;
    select r.content into content from revisions r where r.id=e.published_revision_id;
    if block is not null and coalesce(content->>(case block when 'story' then 'context' else block end),'')='' then perform fail(422,'That practice has no text in the selected passage.'); end if;
    insert into citations(revision_id,source_id,block_id,relationship,locator,annotation)
      values(e.published_revision_id,source,block,item->>'relationship',left(coalesce(item->>'locator',''),1000),left(item->>'annotation',4000));
  end loop;
end $$;

create function public.source_culture_rate_limit(p_key text, p_limit integer, p_seconds integer)
returns boolean language plpgsql security definer set search_path = source_culture, pg_temp as $$
declare n integer;
begin
  insert into rate_limits(key,count,expires) values(p_key,1,now()+make_interval(secs=>p_seconds))
  on conflict(key) do update set count=case when rate_limits.expires<now() then 1 else rate_limits.count+1 end,
    expires=case when rate_limits.expires<now() then excluded.expires else rate_limits.expires end returning count into n;
  delete from rate_limits where expires<now()-interval '1 hour';
  return n<=p_limit;
end $$;

create function public.source_culture_unused_media(p_keys text[]) returns text[]
language sql security definer set search_path = source_culture, pg_temp as $$
  select coalesce(array_agg(key),'{}'::text[]) from unnest(p_keys) key
    where not exists(select 1 from media where storage_key=key);
$$;

-- Identity and role arguments are trusted ONLY because browser roles cannot
-- execute this function. The Edge Function verifies Auth and sets these values.
create function public.source_culture_api(p_path text, p_method text default 'GET', p_payload jsonb default '{}',
  p_email text default null, p_editor boolean default false)
returns jsonb language plpgsql security definer set search_path = source_culture, pg_temp as $$
declare actor text; e entities; r revisions; result jsonb; ident text; kind text; action text; feedback text; m media;
begin
  if p_email is not null then
    insert into contributors(email,verified) values(lower(p_email),true)
      on conflict(email) do update set verified=true returning id into actor;
  end if;
  if p_method='GET' then
    if p_path='/session' then
      return jsonb_build_object('user',case when actor is null then null else jsonb_build_object('email',p_email,'editor',p_editor) end,'csrf',null);
    end if;
    if p_path in ('/practices','/sources') then
      select coalesce(jsonb_agg(public_entry(id) order by updated_at desc,id),'[]') into result from entities
        where visible(id) and (case when p_path='/sources' then entities.kind='source' else entities.kind in ('practice','variation') end);
      return result;
    end if;
    if p_path ~ '^/(practices|sources)/[^/]+$' then
      select * into e from entities where (id=split_part(p_path,'/',3) or slug=split_part(p_path,'/',3)) and
        (case when p_path like '/sources/%' then entities.kind='source' else entities.kind in ('practice','variation') end);
      if not found or not visible(e.id) then perform fail(404,'This entry is unavailable. It may have been withdrawn or is not published.'); end if;
      return public_entry(e.id);
    end if;
    if p_path ~ '^/media/[^/]+$' then
      select * into m from media where id=split_part(p_path,'/',3);
      if found then select en.* into e from entities en join revisions rev on rev.entity_id=en.id where rev.id=m.revision_id; end if;
      if m.id is null or not (coalesce(visible(e.id) and e.published_revision_id=m.revision_id,false)
        or (actor is not null and (m.owner_id=actor or p_editor))) then perform fail(404,'Image unavailable.'); end if;
      return jsonb_build_object('storage_key',m.storage_key);
    end if;
    if p_path in ('/mine','/admin') or p_path ~ '^/submissions/[^/]+$' then
      if actor is null or (p_path='/admin' and not p_editor) then perform fail(403,'Sign in with an authorised account to continue.'); end if;
      if p_path like '/submissions/%' then
        select * into e from entities where id=split_part(p_path,'/',3) and owner_id=actor;
        if not found then perform fail(404,'Contribution not found in your account.'); end if;
        return private_entry(e.id,actor,p_editor);
      end if;
      select coalesce(jsonb_agg(private_entry(id,actor,p_editor) order by updated_at desc,id),'[]') into result
        from entities where owner_id=actor or (p_path='/admin' and p_editor);
      return result;
    end if;
    perform fail(404,'API route not found.');
  end if;
  if p_method<>'POST' then perform fail(405,'Use GET or POST.'); end if;
  if p_path='/submissions' or p_path ~ '^/submissions/[^/]+/revisions$' then
    kind := p_payload->>'kind';
    if p_path='/submissions' then
      if actor is null then
        insert into contributors(email) values(lower(p_payload->>'email')) on conflict(email) do update set email=excluded.email returning id into actor;
      end if;
      if kind='variation' and p_payload->>'parent_id' is null then perform fail(422,'A variation needs a published parent practice.'); end if;
      foreach ident in array array[p_payload->>'parent_id',p_payload->>'target_id'] loop
        if ident is not null and not visible(ident) then perform fail(422,'The entry you are responding to is unavailable.'); end if;
      end loop;
      if p_payload->>'parent_id' is not null and not exists(select 1 from entities where id=p_payload->>'parent_id' and entities.kind in ('practice','variation')) then perform fail(422,'A variation must refer to a practice.'); end if;
      r := insert_entity(actor,kind,p_payload->'content',p_payload->>'parent_id',p_payload->>'target_id');
    else
      select * into e from entities where id=split_part(p_path,'/',3) for update;
      if actor is null or e.id is null or e.owner_id is distinct from actor then perform fail(403,'You can only revise your own contribution.'); end if;
      if e.status='withdrawn' or e.kind<>kind then perform fail(409,'This contribution cannot be revised.'); end if;
      insert into revisions(entity_id,number,content) select e.id,max(number)+1,p_payload->'content' from revisions where entity_id=e.id returning * into r;
      update entities set updated_at=now() where id=e.id;
    end if;
    perform save_revision(r,actor,p_payload);
    if p_email is not null then perform confirm_revision(r.id,actor); end if;
    return jsonb_build_object('id',r.entity_id,'message','Saved to the review queue. It is not public.','email_delivery','not requested');
  end if;
  if actor is null then perform fail(401,'Sign in first.'); end if;
  ident := split_part(p_path,'/',3);
  select * into e from entities where id=ident for update;
  if not found then perform fail(404,'This contribution is unavailable.'); end if;
  select * into r from revisions where entity_id=e.id order by number desc limit 1;
  if p_path ~ '^/submissions/[^/]+/(confirm|withdraw|messages)$' then
    action := split_part(p_path,'/',4);
    if e.owner_id is distinct from actor and not (action='messages' and p_editor) then perform fail(403,'You can only manage your own contribution.'); end if;
    if action='confirm' then
      if e.status='withdrawn' then perform fail(403,'You can only confirm your own active contribution.'); end if;
      if p_payload->'publication_permission' is distinct from 'true'::jsonb or p_payload->'rights_confirmation' is distinct from 'true'::jsonb then perform fail(422,'Confirm this account and its recorded sharing permissions.'); end if;
      perform confirm_revision(r.id,actor);
      return jsonb_build_object('message','Your account and sharing permissions are confirmed. An editor can now review it for publication.');
    elsif action='withdraw' then
      update entities set status='withdrawn',updated_at=now() where id=e.id;
      return jsonb_build_object('message','Withdrawn. The contribution and its media are no longer public.');
    else
      feedback := trim(coalesce(p_payload->>'body',''));
      if feedback='' or length(feedback)>12000 then perform fail(422,'Write a private response of at most 12,000 characters.'); end if;
      insert into messages(entity_id,author_id,body) values(e.id,actor,feedback);
      return jsonb_build_object('message','Your private response has been saved for editorial review.');
    end if;
  end if;
  if p_path ~ '^/admin/[^/]+/(review|connections)$' then
    if not p_editor then perform fail(403,'Only explicitly authorised editors can review contributions.'); end if;
    if e.status='withdrawn' then perform fail(404,'This contribution is unavailable.'); end if;
    if p_path like '%/connections' then
      if e.kind<>'source' or not visible(e.id) then perform fail(404,'The source is unavailable.'); end if;
      if jsonb_array_length(coalesce(p_payload->'links','[]'))=0 then perform fail(422,'Add at least one source connection.'); end if;
      perform link_sources(e.id,p_payload->'links');
      insert into reviews(entity_id,revision_id,editor_id,action,feedback) values(e.id,e.published_revision_id,actor,'connections','Editor added annotated source connections.');
      return jsonb_build_object('message','Source connections saved.');
    end if;
    action := p_payload->>'action'; feedback := left(trim(coalesce(p_payload->>'feedback','')),12000);
    if coalesce(action,'') not in ('published','needs changes','declined') or (action<>'published' and feedback='') then perform fail(422,'Choose a review decision and explain requested changes or a decline.'); end if;
    if p_payload->>'revision_id' is distinct from r.id or r.state not in ('submitted','needs changes') then perform fail(409,'The contribution changed or was already reviewed. Refresh before reviewing.'); end if;
    if action='published' then
      if e.kind='correction' or not exists(select 1 from contributors where id=e.owner_id and verified) then perform fail(422,'Verify the contributor email before publishing. Corrections must be applied through an approved contributor revision.'); end if;
      if not exists(select 1 from confirmations where revision_id=r.id and owner_id=e.owner_id) then perform fail(422,'The contributor must confirm this specific account and its sharing permissions before publication.'); end if;
      if exists(select 1 from citations where revision_id=r.id and not visible(source_id)) then perform fail(422,'Review and publish the linked source suggestions before publishing this practice.'); end if;
      if e.kind='source' then
        if e.target_id is not null and jsonb_array_length(coalesce(p_payload->'links','[]'))=0 then perform fail(422,'Explain the suggested source connection before publishing.'); end if;
        perform link_sources(e.id,coalesce(p_payload->'links','[]'));
      end if;
      update entities set published_revision_id=r.id,status='published',updated_at=now() where id=e.id;
    elsif e.published_revision_id is null then
      update entities set status=action,updated_at=now() where id=e.id;
    end if;
    update revisions set state=action where id=r.id;
    insert into reviews(entity_id,revision_id,editor_id,action,feedback) values(e.id,r.id,actor,action,feedback);
    return jsonb_build_object('message','Review recorded: '||action||'.');
  end if;
  perform fail(404,'API route not found.');
end $$;

revoke all on all tables in schema source_culture from public, anon, authenticated;
revoke all on all functions in schema source_culture from public, anon, authenticated;
revoke all on function public.source_culture_api(text,text,jsonb,text,boolean) from public, anon, authenticated;
revoke all on function public.source_culture_rate_limit(text,integer,integer) from public, anon, authenticated;
revoke all on function public.source_culture_unused_media(text[]) from public, anon, authenticated;
grant execute on function public.source_culture_api(text,text,jsonb,text,boolean) to service_role;
grant execute on function public.source_culture_rate_limit(text,integer,integer) to service_role;
grant execute on function public.source_culture_unused_media(text[]) to service_role;

-- No public URL, SELECT, INSERT, or UPDATE policies are added for this bucket.
-- Only the Edge Function accesses it, after checking current database visibility.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
  values('source-culture-media','source-culture-media',false,5242880,array['image/webp'])
  on conflict(id) do nothing;
