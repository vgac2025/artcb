"""Async PDF text extraction (Optimisation #4)."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import aiofiles
from pypdf import PdfReader
from pypdf.errors import PdfReadError


async def extract_pdf_text_async(
    path: Path,
    max_pages: int | None = None,
    parallel: bool = True,
) -> str:
    """Extract text from PDF asynchronously with parallel page processing.

    Args:
        path: Path to PDF file
        max_pages: Maximum number of pages to extract
        parallel: Whether to process pages in parallel

    Returns:
        Extracted text from PDF
    """
    # Read PDF file asynchronously
    async with aiofiles.open(path, 'rb') as f:
        pdf_bytes = await f.read()

    # Parse PDF (sync operation, but fast) - wrap bytes in BytesIO
    pdf_stream = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_stream)
    total_pages = len(reader.pages)
    num_pages = min(max_pages, total_pages) if max_pages else total_pages

    if not parallel or num_pages < 4:
        # Sequential extraction for small PDFs
        chunks = []
        for i in range(num_pages):
            try:
                text = reader.pages[i].extract_text() or ""
            except PdfReadError:
                text = ""
            if text.strip():
                chunks.append(text.strip())
        return "\n\n".join(chunks)

    # Parallel extraction for large PDFs
    async def extract_page(page_num: int) -> tuple[int, str]:
        """Extract text from a single page."""
        # Run sync extraction in executor
        loop = asyncio.get_event_loop()
        def _extract() -> str:
            try:
                return reader.pages[page_num].extract_text() or ""
            except PdfReadError:
                return ""
        text = await loop.run_in_executor(None, _extract)
        return (page_num, text.strip() if text.strip() else "")

    # Process all pages concurrently
    tasks = [extract_page(i) for i in range(num_pages)]
    results = await asyncio.gather(*tasks)

    # Sort by page number and join
    results.sort(key=lambda x: x[0])
    chunks = [text for _, text in results if text]
    return "\n\n".join(chunks)


async def extract_pdf_chunks_async(
    path: Path,
    chunk_size: int = 2000,
    max_chunks: int = 5,
    parallel: bool = True,
) -> list[str]:
    """Split PDF text into chunks asynchronously.

    Args:
        path: Path to PDF file
        chunk_size: Size of each chunk in characters
        max_chunks: Maximum number of chunks to return
        parallel: Whether to use parallel extraction

    Returns:
        List of text chunks
    """
    full_text = await extract_pdf_text_async(path, parallel=parallel)
    if not full_text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(full_text) and len(chunks) < max_chunks:
        end = min(start + chunk_size, len(full_text))
        piece = full_text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end

    return chunks

