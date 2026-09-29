-- Ejecuta UNA VEZ en Supabase (SQL Editor). Añade habitaciones y m² mínimos.
alter table usuarios_filtros add column if not exists habs_min integer;
alter table usuarios_filtros add column if not exists m2_min integer;
