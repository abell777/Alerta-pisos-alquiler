-- Ejecuta UNA VEZ en Supabase (SQL Editor).
alter table usuarios_filtros add column if not exists plan text not null default 'gratis';

create table if not exists cola_retardo (
    id bigserial primary key,
    chat_id bigint not null,
    mensaje text not null,
    enviar_a timestamptz not null
);
create index if not exists cola_retardo_enviar_a on cola_retardo (enviar_a);
