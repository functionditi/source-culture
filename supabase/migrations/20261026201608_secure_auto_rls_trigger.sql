-- Supabase's optional automatic-RLS helper is an event trigger, not a browser
-- API. Keep the trigger enabled while removing its default PUBLIC execution.
-- The helper is absent in local databases and projects without automatic RLS.
do $migration$
begin
  if to_regprocedure('public.rls_auto_enable()') is not null then
    revoke execute on function public.rls_auto_enable()
      from public, anon, authenticated;
  end if;
end;
$migration$;
