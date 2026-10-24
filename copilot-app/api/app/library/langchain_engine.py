"""LangChain RAG Engine using InMemoryVectorStore, init_chat_model, and init_embeddings."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Mapping, Sequence
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .engine import (
    Answer,
    Delta,
    MetadataValue,
    RagEvent,
    Source,
    StoreInfo,
    Turn,
)

load_dotenv()


class LangChainCustomRagEngine:
    name: str = "langchain"
    label: str = "LangChain InMemory RAG"
    local: bool = False

    def __init__(
        self,
        *,
        ai_provider: str | None = None,
        ai_model: str | None = None,
        embedding_model: str | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        top_k: int = 3,
    ) -> None:
        self.top_k = top_k
        self.ai_provider = ai_provider or os.getenv("AI_PROVIDER", "openai")
        self.ai_model = ai_model or os.getenv("AI_MODEL", "gpt-4o-mini")
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", "500"))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", "50"))
        self.model = self.ai_model

        # splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        # embeddings initializer
        self.embeddings = init_embeddings(
            model=self.embedding_model,
            provider=self.ai_provider,
        )

        # In-Memory Vector Store
        self.vs = InMemoryVectorStore(embedding=self.embeddings)

        # LLM initializer
        self.llm = init_chat_model(
            model=self.ai_model,
            model_provider=self.ai_provider,
        )

    async def ensure_store(self, display_name: str) -> str:
        return "in_memory_store"

    async def store_info(self, store_id: str) -> StoreInfo | None:
        # Returns number of indexed chunks
        count = len(getattr(self.vs, "store", {}))
        return StoreInfo(id=store_id, active=count)

    async def add_document(
        self,
        store_id: str,
        path: Path,
        *,
        title: str,
        mime_type: str,
        metadata: Mapping[str, MetadataValue],
    ) -> str:
        """Runs your exact document loading and splitting logic."""
        doc_id = str(uuid.uuid4())

        # Load document (handles txt, pdf, etc.)
        if path.suffix.lower() == ".pdf":
            docs = PyPDFLoader(str(path)).load()
        else:
            # loader
            docs = TextLoader(file_path=str(path), encoding="utf-8").load()

        # splitting
        chunks = self.splitter.split_documents(documents=docs)

        # Tag each chunk with document metadata and our unique ID
        for c in chunks:
            c.metadata["title"] = title
            c.metadata["engine_doc_id"] = doc_id
            for k, v in metadata.items():
                c.metadata[k] = str(v)

        # insertion into InMemoryVectorStore
        self.vs.add_documents(documents=chunks)
        return doc_id

    async def delete_document(self, engine_document_id: str) -> None:
        """Delete document from InMemoryVectorStore if user deletes it."""
        if hasattr(self.vs, "store"):
            keys_to_delete = [
                k
                for k, v in self.vs.store.items()
                if v.get("metadata", {}).get("engine_doc_id") == engine_document_id
            ]
            for k in keys_to_delete:
                self.vs.delete([k])

    async def purge(self, store_id: str, doc_key: str) -> int:
        return 0

    async def stream(
        self, turns: Sequence[Turn], store_ids: Sequence[str], metadata_filter: str | None
    ) -> AsyncIterator[RagEvent]:
        """Runs your exact query retrieval and prompt template logic with live streaming."""
        if not turns:
            return

        query = turns[-1].text

        # similarity search: vs.similarity_search(query, k=3)
        retrieved_docs = self.vs.similarity_search(query, k=self.top_k)

        # Build context string and source citations for the UI
        sources: list[Source] = []
        context_snippets: list[str] = []

        for i, doc in enumerate(retrieved_docs, start=1):
            title = doc.metadata.get("title", f"Document {i}")
            snippet = doc.page_content.strip()
            page = doc.metadata.get("page", None)
            sources.append(Source(number=i, title=title, text=snippet, page=page))
            context_snippets.append(f"[{i}] {snippet}")

        ctx = "\n\n".join(context_snippets)

        # prompt_template
        prompt_template = [
            {
                "role": "system",
                "content": (
                    "Answer only from this context. Include citation numbers "
                    "like [1] or [2] when referencing facts."
                ),
            },
            {"role": "user", "content": f"Context: {ctx}\n\nQuestion: {query}"},
        ]

        # Stream tokens to the frontend to get the live typewriter effect
        full_text = []
        async for chunk in self.llm.astream(prompt_template):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            full_text.append(token)
            yield Delta(text=token)

        final_answer = "".join(full_text)

        # Return the Answer with citation badges for the UI
        yield Answer(
            text=final_answer,
            cited_text=final_answer,
            sources=sources,
            model=self.ai_model,
            grounded=bool(sources),
        )
