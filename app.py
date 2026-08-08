"""Streamlit entry point for the PDF Chat Bot.

Run locally with ``streamlit run app.py`` or inside Docker
(see Dockerfile). Uses ``$PORT`` from the environment (Render
default: 10000).
"""

from __future__ import annotations

import logging

import streamlit as st
from src.config import get_settings
from src.document_processor import process_pdf_bytes
from src.llm_chain import ask_question
from src.vector_store import get_vector_store, host_from_url, save_chunks_to_database

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

st.set_page_config(page_title="PDF Chat Bot", page_icon="📄")
st.title("📄 PDF Chat Bot")

try:
    get_settings()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()


@st.cache_resource(show_spinner="Connecting to vector store…")
def cached_vector_store():
    """Cached connection so we don't rebuild Supabase/NVIDIA clients per rerun."""
    return get_vector_store()


# ----- Sidebar: PDF upload -----
with st.sidebar:
    st.header("Upload a PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None and st.button("Process PDF"):
        try:
            with st.spinner("Processing PDF…"):
                docs = process_pdf_bytes(uploaded_file.read(), source=uploaded_file.name)
            save_chunks_to_database(docs)
        except Exception:
            settings = get_settings()
            supabase_host = host_from_url(settings.supabase_url)
            embed_host = host_from_url(settings.embed_base_url)
            logger.exception(
                "PDF processing failed. Supabase host=%s, NVIDIA embed host=%s.",
                supabase_host,
                embed_host,
            )
            st.error(
                "Failed to process PDF. Could not reach one or more services "
                f"(Supabase: {supabase_host}, NVIDIA embeddings: {embed_host}). "
                "Check the environment variables SUPABASE_URL and EMBED_BASE_URL "
                "and view the logs for the full traceback."
            )
        else:
            st.success(f"Processed {len(docs)} chunks from {uploaded_file.name}")
            st.session_state.pdf_processed = uploaded_file.name

# ----- Chat UI -----
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if not st.session_state.get("pdf_processed"):
    st.info("Upload and process a PDF in the sidebar before asking questions.")

if prompt := st.chat_input("Ask a question about the PDF…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    answer = ""
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking…"):
                retriever = cached_vector_store().as_retriever()
                answer = ask_question(prompt, retriever)
        except Exception as exc:
            st.error(f"Failed to generate an answer: {exc}")
        else:
            st.markdown(answer)

    if answer:
        st.session_state.messages.append({"role": "assistant", "content": answer})
