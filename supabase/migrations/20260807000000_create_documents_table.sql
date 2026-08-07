-- ============================================================================
-- PDF Chat Bot — Supabase database migration
-- Creates the pgvector schema required by src/vector_store.py.
--
-- The app connects with LangChain's `SupabaseVectorStore` (table_name
-- "documents", query_name "match_documents") and embeds chunks with NVIDIA
-- `nvidia/nv-embedqa-e5-v5` (1024-dimensional vectors).
--
-- Embedding dimension warning:
--   `vector(1024)` MUST match the output dimension of `EMBED_MODEL`
--   (1024 for `nvidia/nv-embedqa-e5-v5`). If you change EMBED_MODEL to a
--   model with a different dimension, update this column AND the function
--   signature, then re-ingest your documents.
--
-- How to run:
--   Option A (manual): Supabase dashboard -> SQL Editor -> paste this file
--                      -> Run.
--   Option B (CLI):    `supabase db push` (migrations auto-applied from
--                      supabase/migrations/).
-- ============================================================================

-- 1. Enable the pgvector extension (safe to run repeatedly).
create extension if not exists vector;

-- 2. Vector documents table.
--    - id        : primary key; auto-generated. Required by PostgREST upsert
--                  (`Prefer: resolution=merge-duplicates`) used by
--                  SupabaseVectorStore.add_documents().
--    - content   : the chunk text (LangChain reads this back as page_content).
--    - metadata  : JSON metadata (source filename, page, ...). LangChain reads
--                  this back as Document.metadata.
--    - embedding : 1024-dim pgvector column (cosine distance).
create table if not exists public.documents (
    id        uuid primary key default gen_random_uuid(),
    content   text not null,
    metadata  jsonb not null default '{}'::jsonb,
    embedding vector(1024) not null
);

-- 3. Approximate-nearest-neighbor index on the embedding (cosine distance).
--    Index ops MUST match the operator used in match_documents (<=> cosine).
create index if not exists documents_embedding_idx
    on public.documents using hnsw (embedding vector_cosine_ops);

-- 4. GIN index on metadata for fast JSONB filtering in match_documents
--    (`where documents.metadata @> filter`).
create index if not exists documents_metadata_idx
    on public.documents using gin (metadata jsonb_path_ops);

-- 5. Similarity search function called via PostgREST RPC
--    (`client.rpc("match_documents", {"query_embedding": ..., "filter": ...})`).
--    The client applies `.limit(k)` on the returned rows, so match_count is
--    only an optional server-side cap.
--    `#variable_conflict use_column` is required because the OUT parameters
--    (id, content, metadata, embedding) collide with the table columns.
create or replace function public.match_documents (
    query_embedding vector(1024),
    match_count     int default null,
    filter          jsonb default '{}'
) returns table (
    id         uuid,
    content    text,
    metadata   jsonb,
    embedding  vector(1024),
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

-- 6. Security.
--    The app only ever talks to the database with the `service_role` key,
--    which bypasses RLS, so enable RLS but add no permissive policies.
--    Block the `anon` / `authenticated` roles from calling the search
--    function (and the table) so uploaded PDF content is not exposed to the
--    public internet. Grant the service_role the privileges it needs (also
--    makes the migration self-contained if default privileges differ).
alter table public.documents enable row level security;

grant select, insert, update, delete on table public.documents to service_role;

revoke execute on function public.match_documents (vector(1024), integer, jsonb)
    from anon, authenticated;
grant execute on function public.match_documents (vector(1024), integer, jsonb)
    to service_role;
