-- Ejecuta esto en Supabase SQL Editor (una vez): añade el campo "ciudad" a
-- los filtros de usuario, necesario para expandir a toda España.
-- Los usuarios que ya tenías registrados quedan con ciudad = 'valencia'.

alter table usuarios_filtros
    add column if not exists ciudad text not null default 'valencia';
