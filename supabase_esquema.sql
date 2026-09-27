-- Ejecuta esto UNA VEZ en Supabase: panel de tu proyecto -> SQL Editor -> New query -> pegar -> Run

-- Anuncios ya notificados (sustituye a vistos.json)
create table if not exists vistos (
    clave text primary key,
    creado_en timestamptz not null default now()
);

-- Filtro de cada persona registrada en el bot
create table if not exists usuarios_filtros (
    chat_id bigint primary key,
    zona text,
    precio_min integer,
    precio_max integer,
    activo boolean not null default true,
    creado_en timestamptz not null default now(),
    actualizado_en timestamptz not null default now()
);

-- Para no releer desde el principio los mensajes del bot en cada ejecución
create table if not exists bot_estado (
    id integer primary key default 1,
    ultimo_update_id bigint not null default 0
);
insert into bot_estado (id, ultimo_update_id) values (1, 0)
    on conflict (id) do nothing;
