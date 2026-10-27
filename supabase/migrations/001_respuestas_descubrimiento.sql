-- Respuestas del form de descubrimiento.
-- Acceso: SOLO con service role (función de Vercel para insertar, n8n para leer).
-- RLS activado y sin políticas para anon/authenticated = nadie más puede leer ni escribir.

create table if not exists public.respuestas_descubrimiento (
  id             bigint generated always as identity primary key,
  created_at     timestamptz not null default now(),
  version        text not null,
  codigo         text check (codigo ~ '^[A-Za-z0-9]{6,12}$'),
  fuente         text check (fuente ~ '^[a-z0-9_-]{1,30}$'),
  segundos       integer check (segundos >= 0),
  nombre         text not null check (char_length(nombre) between 2 and 100),
  email          text not null check (char_length(email) <= 150),
  whatsapp       text check (whatsapp ~ '^[0-9]{8,15}$'),
  estudio        text not null check (char_length(estudio) <= 150),
  rol            text not null check (char_length(rol) <= 100),
  interes_charla text not null check (interes_charla in ('agendar', 'contactar', 'ahora_no')),
  respuestas     jsonb not null,
  ip_hash        text
);

create index if not exists respuestas_descubrimiento_codigo_idx on public.respuestas_descubrimiento (codigo);
create index if not exists respuestas_descubrimiento_email_idx on public.respuestas_descubrimiento (lower(email));

alter table public.respuestas_descubrimiento enable row level security;
-- Intencionalmente sin políticas: anon y authenticated quedan bloqueados.
revoke all on public.respuestas_descubrimiento from anon, authenticated;
