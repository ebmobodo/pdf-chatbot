-- ============================================================================
-- PDF Chat Bot — Supabase migration (grow embeddings to 2048 dimensions)
-- Grows the pgvector dimension from 1024 to 2048 to match
--   `nvidia/nemotron-3-embed-1b`
-- (native 2048-dimensional output; reduced dimensions are NOT supported by
-- this model). Requires migration `20260807000000_create_documents_table`.
--
-- IMPORTANT: re-ingest your documents after applying this migration — any
-- rows already stored still hold 1024-dim vectors and must be dropped before
-- saving new chunks.
-- ============================================================================

-- 1. Drop indexes relying on the old vector(1024) column type. The metadata
--    GIN index is type-agnostic, so only the HNSW embedding index is affected.
drop index if exists public.documents_embedding_idx;

-- 2. Widen the embedding column to vector(2048).
alter table public.documents
    alter column embedding type vector(2048)
    using embedding::vector(2048);

-- 3. Recreate the approximate-nearest-neighbor index (cosine distance).
create index if not exists documents_embedding_idx
    on public.documents using hnsw (embedding vector_cosine_ops);

-- 4. Update the similarity search function signatures to vector(2048).
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

-- 5. Regrant privileges against the new function signature. The existing
--    grants attached to the old vector(1024) signature no longer apply, so
--    revoke from anon/authenticated and re-grant to service_role.
revoke execute on function public.match_documents (vector(2048), integer, jsonb)
    from anon, authenticated;
grant execute on function public.match_documents (vector(2048), integer, jsonb)
    to service_role;