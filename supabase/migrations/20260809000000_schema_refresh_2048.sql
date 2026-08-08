-- ============================================================================
-- PDF Chat Bot — complete schema (refresh, 2048-dim embeddings)
-- Targets the CURRENT app config: EMBED_MODEL=nvidia/nemotron-3-embed-1b
-- (2048-dim native output).
--
-- Idempotent: drops any previous documents table / match_documents function
-- and recreates everything fresh. Existing rows are lost by design — re-ingest
-- your PDFs in the app afterwards.
--
-- Run: Supabase dashboard -> SQL Editor -> paste -> Run.
-- ============================================================================

-- 1. Enable the pgvector extension (safe to run repeatedly).
create extension if not exists vector;

-- 2. Drop any previous objects so the refresh is clean. The table is dropped
--    with CASCADE to also remove its indexes.
drop table if exists public.documents cascade;
drop function if exists public.match_documents(vector(1024), integer, jsonb);
drop function if exists public.match_documents(vector(2048), integer, jsonb);

-- 3. Vector documents table.
--    - id        : primary key; auto-generated (PostgREST upsert support).
--    - content   : the chunk text (read back as page_content).
--    - metadata  : JSON metadata (source filename, page, ...).
--    - embedding : 2048-dim pgvector column (cosine distance).
create table public.documents (
    id        uuid primary key default gen_random_uuid(),
    content   text not null,
    metadata  jsonb not null default '{}'::jsonb,
    embedding vector(2048) not null
);

-- 4. Approximate-nearest-neighbor index (cosine). Ops MUST match the <=>
--    operator used in match_documents.
create index documents_embedding_idx
    on public.documents using hnsw (embedding vector_cosine_ops);

-- 5. GIN index on metadata for fast JSONB filtering (metadata @> filter).
create index documents_metadata_idx
    on public.documents using gin (metadata jsonb_path_ops);

-- 6. Similarity search function called via PostgREST RPC
--    (client.rpc("match_documents", {query_embedding, filter})).
--    `#variable_conflict use_column` is required because the OUT parameters
--    collide with the table columns.
create or replace function public.match_documents (
    query_embedding vector(2048),
    match_count     int default null,
    filter          jsonb default '{}'
) returns table (
    id         uuid,
    content    text,
    metadata   jsonb,
    embedding  vector(2048),
    similarity float
)
language plpgsql
security invoker
as $$
#variable_conflict use_column
begin
    return query
    select
        documents.id,
        documents.content,
        documents.metadata,
        documents.embedding,
        1 - (documents.embedding <=> query_embedding) as similarity
    from documents
    where documents.metadata @> filter
    order by documents.embedding <=> query_embedding
    limit match_count;
end;
$$;

-- 7. Security. The app talks to the DB with the service_role key (bypasses
--    RLS), so RLS is on with no permissive policies and anon/authenticated
--    cannot call the search function or read uploaded content.
alter table public.documents enable row level security;

grant select, insert, update, delete on table public.documents to service_role;

revoke execute on function public.match_documents (vector(2048), integer, jsonb)
    from anon, authenticated;
grant execute on function public.match_documents (vector(2048), integer, jsonb)
    to service_role;
