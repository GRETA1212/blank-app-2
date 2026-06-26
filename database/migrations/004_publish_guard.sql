create or replace function enforce_project_publish_approval()
returns trigger language plpgsql as $$
begin
  if new.status = 'PUBLISHED' and old.status is distinct from 'PUBLISHED' then
    if not exists (
      select 1 from approval_reviews
      where project_id = new.id and user_id = new.user_id and status = 'APPROVED'
    ) then
      raise exception 'Explicit approved human review is required before publishing';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists projects_publish_guard on projects;
create trigger projects_publish_guard
before update on projects
for each row execute function enforce_project_publish_approval();
