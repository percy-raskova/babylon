#!/usr/bin/env python3
"""Corpus ingestion tool for Babylon's RAG "Memory" pipeline.

This tool imports and ingests the vertical slice corpus into ChromaDB's
THEORY_COLLECTION. It supports importing from external libraries (like
marxists.org) and handles chunking for optimal RAG retrieval.

Usage:
    # Import texts from external library and ingest
    poetry run python tools/ingest_corpus.py --import-from /media/user/marxists.org/

    # Ingest existing corpus files
    poetry run python tools/ingest_corpus.py

    # Reset collection before ingesting
    poetry run python tools/ingest_corpus.py --reset
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Final

from tqdm import tqdm

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.config.chromadb_config import ChromaDBConfig
from babylon.data.chroma_manager import ChromaManager
from babylon.rag.chunker import DocumentChunk, DocumentProcessor, TextChunker

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# MVP VERTICAL SLICE CORPUS
# =============================================================================
# These 7 texts form the minimal viable corpus for testing the RAG pipeline.
# They cover the key theoretical foundations: exploitation, imperialism, and
# revolutionary consciousness.


@dataclass(frozen=True)
class CorpusText:
    """A text in the MVP corpus with metadata for fuzzy matching."""

    title: str
    author: str
    keywords: tuple[str, ...]  # For fuzzy filename matching
    year: int | None = None


MVP_CORPUS: Final[tuple[CorpusText, ...]] = (
    CorpusText(
        title="Wage Labour and Capital",
        author="Marx",
        keywords=("wage", "labour", "capital", "wage-labour"),
        year=1849,
    ),
    CorpusText(
        title="Value, Price and Profit",
        author="Marx",
        keywords=("value", "price", "profit"),
        year=1865,
    ),
    CorpusText(
        title="Principles of Communism",
        author="Engels",
        keywords=("principles", "communism"),
        year=1847,
    ),
    CorpusText(
        title="Imperialism, the Highest Stage of Capitalism",
        author="Lenin",
        keywords=("imperialism", "highest", "stage", "capitalism", "imp-hsc"),
        year=1916,
    ),
    CorpusText(
        title="The Wretched of the Earth",
        author="Fanon",
        keywords=("wretched", "earth", "damnes", "terre"),
        year=1961,
    ),
    CorpusText(
        title="On Contradiction",
        author="Mao",
        keywords=("contradiction", "mswv1_17"),
        year=1937,
    ),
    CorpusText(
        title="Analysis of the Classes in Chinese Society",
        author="Mao",
        keywords=("analysis", "classes", "chinese", "society", "mswv1_1"),
        year=1926,
    ),
)


# =============================================================================
# FILE DISCOVERY AND IMPORT
# =============================================================================


def fuzzy_match_score(filename: str, text: CorpusText) -> float:
    """Calculate fuzzy match score between filename and corpus text.

    Args:
        filename: The filename to check (lowercase, without extension)
        text: The corpus text to match against

    Returns:
        A score between 0.0 and 1.0, higher is better match
    """
    filename_lower = filename.lower()

    # Direct keyword match gets highest priority
    for keyword in text.keywords:
        if keyword.lower() in filename_lower:
            return 0.9 + (0.1 * len(keyword) / len(filename_lower))

    # Title similarity as fallback
    title_lower = text.title.lower().replace(",", "").replace("'", "")
    title_words = title_lower.split()

    # Check how many title words appear in filename
    word_matches = sum(1 for word in title_words if word in filename_lower)
    if word_matches > 0:
        return 0.5 * (word_matches / len(title_words))

    # Sequence matcher for partial matches
    return SequenceMatcher(None, filename_lower, title_lower).ratio() * 0.3


def find_matching_files(
    source_dir: Path,
    extensions: tuple[str, ...] = (".txt", ".md", ".htm", ".html"),
) -> dict[CorpusText, list[Path]]:
    """Recursively scan directory for files matching MVP corpus texts.

    Args:
        source_dir: Directory to scan
        extensions: File extensions to consider

    Returns:
        Dict mapping each corpus text to list of matching file paths
    """
    matches: dict[CorpusText, list[Path]] = {text: [] for text in MVP_CORPUS}

    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        return matches

    # Scan all files with matching extensions
    all_files: list[Path] = []
    for ext in extensions:
        all_files.extend(source_dir.rglob(f"*{ext}"))

    logger.info(f"Scanning {len(all_files)} files in {source_dir}...")

    # Score each file against each corpus text
    for file_path in tqdm(all_files, desc="Matching files", disable=len(all_files) < 100):
        filename = file_path.stem  # filename without extension

        for text in MVP_CORPUS:
            score = fuzzy_match_score(filename, text)
            if score > 0.5:  # Threshold for considering a match
                matches[text].append((file_path, score))  # type: ignore[arg-type]

    # Sort matches by score and keep only paths
    result: dict[CorpusText, list[Path]] = {}
    for text, file_scores in matches.items():
        # file_scores is list of (Path, float) tuples
        scored_list: list[tuple[Path, float]] = file_scores  # type: ignore[assignment]
        if scored_list:
            # Sort by score descending, then by path length ascending (prefer shorter)
            sorted_matches = sorted(
                scored_list,
                key=lambda x: (-x[1], len(str(x[0]))),
            )
            result[text] = [path for path, _ in sorted_matches]
        else:
            result[text] = []

    return result


def import_corpus_files(source_dir: Path, corpus_dir: Path) -> tuple[int, list[str]]:
    """Import matching files from external library to corpus directory.

    Args:
        source_dir: External library path to import from
        corpus_dir: Local corpus directory to copy files to

    Returns:
        Tuple of (number imported, list of missing text titles)
    """
    corpus_dir.mkdir(parents=True, exist_ok=True)

    matches = find_matching_files(source_dir)

    imported = 0
    missing: list[str] = []

    for text, paths in matches.items():
        if not paths:
            missing.append(f"{text.title} ({text.author})")
            continue

        # Take the best match (first after sorting)
        source_path = paths[0]

        # Create destination filename: author_title.ext
        safe_title = re.sub(r"[^\w\s-]", "", text.title).replace(" ", "_").lower()
        safe_author = text.author.lower()
        ext = source_path.suffix
        dest_filename = f"{safe_author}_{safe_title}{ext}"
        dest_path = corpus_dir / dest_filename

        try:
            shutil.copy2(source_path, dest_path)
            logger.info(f"Imported: {text.title} -> {dest_filename}")
            imported += 1
        except Exception as e:
            logger.error(f"Failed to copy {source_path}: {e}")
            missing.append(f"{text.title} ({text.author})")

    return imported, missing


# =============================================================================
# CORPUS INGESTION
# =============================================================================


def extract_metadata_from_file(file_path: Path) -> dict[str, str]:
    """Extract metadata from file path and content.

    Args:
        file_path: Path to the corpus file

    Returns:
        Dict of metadata fields
    """
    # Try to match against MVP corpus for rich metadata
    filename = file_path.stem.lower()
    for text in MVP_CORPUS:
        if fuzzy_match_score(filename, text) > 0.5:
            return {
                "title": text.title,
                "author": text.author,
                "year": str(text.year) if text.year else "",
                "source_file": file_path.name,
                "corpus": "mvp_vertical_slice",
            }

    # Fallback: extract from filename
    parts = file_path.stem.replace("_", " ").replace("-", " ").title()
    return {
        "title": parts,
        "author": "Unknown",
        "source_file": file_path.name,
        "corpus": "mvp_vertical_slice",
    }


def read_file_with_fallback(file_path: Path) -> str:
    """Read file content with encoding fallback for legacy files.

    Args:
        file_path: Path to file

    Returns:
        File content as string

    Raises:
        IOError: If file cannot be read
    """
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

    for encoding in encodings:
        try:
            with open(file_path, encoding=encoding, errors="replace") as f:
                content = f.read()
                # Strip HTML tags if it's an HTML file
                if file_path.suffix.lower() in (".htm", ".html"):
                    content = strip_html_tags(content)
                return content
        except UnicodeDecodeError:
            continue

    # Last resort: read as binary and decode with errors ignored
    with open(file_path, "rb") as f:
        return f.read().decode("utf-8", errors="ignore")


def strip_html_tags(html: str) -> str:
    """Remove HTML tags and decode entities, keeping text content.

    Args:
        html: HTML content

    Returns:
        Plain text content
    """
    import html as html_module

    # Remove script and style elements
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

    # Remove all HTML tags
    html = re.sub(r"<[^>]+>", " ", html)

    # Decode HTML entities
    html = html_module.unescape(html)

    # Normalize whitespace
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r"\n\s*\n", "\n\n", html)

    return html.strip()


def generate_chunk_id(source_file: str, chunk_index: int) -> str:
    """Generate deterministic chunk ID.

    Args:
        source_file: Source filename
        chunk_index: Index of chunk in document

    Returns:
        Deterministic ID string
    """
    safe_name = re.sub(r"[^\w]", "_", source_file.lower())
    return f"{safe_name}_chunk_{chunk_index:04d}"


def ingest_corpus(corpus_dir: Path, reset: bool = False) -> int:
    """Ingest corpus files into ChromaDB THEORY_COLLECTION.

    Args:
        corpus_dir: Directory containing corpus files
        reset: If True, clear collection before ingesting

    Returns:
        Number of chunks ingested
    """
    if not corpus_dir.exists():
        logger.error(f"Corpus directory does not exist: {corpus_dir}")
        return 0

    # Get all corpus files
    extensions = (".txt", ".md", ".htm", ".html")
    corpus_files = [f for ext in extensions for f in corpus_dir.glob(f"*{ext}")]

    if not corpus_files:
        logger.warning(f"No corpus files found in {corpus_dir}")
        return 0

    logger.info(f"Found {len(corpus_files)} corpus files")

    # Initialize ChromaDB
    manager = ChromaManager()
    collection = manager.get_or_create_collection(ChromaDBConfig.THEORY_COLLECTION)

    if reset:
        logger.info("Resetting collection...")
        # Delete all documents in collection
        existing = collection.get()
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            logger.info(f"Deleted {len(existing['ids'])} existing chunks")

    # Initialize chunker with recommended settings
    chunker = TextChunker(
        chunk_size=1000,
        overlap_size=100,
        preserve_paragraphs=True,
        preserve_sentences=True,
    )
    processor = DocumentProcessor(chunker=chunker)

    total_chunks = 0
    all_chunks: list[DocumentChunk] = []
    all_ids: list[str] = []
    all_documents: list[str] = []
    all_metadatas: list[dict[str, str]] = []

    for file_path in tqdm(corpus_files, desc="Processing files"):
        try:
            # Read content
            content = read_file_with_fallback(file_path)
            if not content or len(content.strip()) < 100:
                logger.warning(f"Skipping {file_path.name}: content too short")
                continue

            # Extract metadata
            metadata = extract_metadata_from_file(file_path)

            # Chunk the document
            chunks = processor.process_text(
                content=content,
                source_file=str(file_path),
                metadata=metadata,
            )

            for chunk in chunks:
                chunk_id = generate_chunk_id(file_path.name, chunk.chunk_index)
                chunk_metadata = {
                    **(chunk.metadata or {}),
                    "chunk_index": str(chunk.chunk_index),
                    "start_char": str(chunk.start_char),
                    "end_char": str(chunk.end_char),
                }

                all_ids.append(chunk_id)
                all_documents.append(chunk.content)
                all_metadatas.append(chunk_metadata)
                all_chunks.append(chunk)

            total_chunks += len(chunks)
            logger.debug(f"Processed {file_path.name}: {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            continue

    # Batch upsert to ChromaDB
    if all_ids:
        logger.info(f"Upserting {len(all_ids)} chunks to ChromaDB...")

        # ChromaDB has batch size limits, process in batches
        batch_size = ChromaDBConfig.BATCH_SIZE
        for i in tqdm(range(0, len(all_ids), batch_size), desc="Upserting"):
            batch_end = min(i + batch_size, len(all_ids))
            collection.upsert(
                ids=all_ids[i:batch_end],
                documents=all_documents[i:batch_end],
                metadatas=all_metadatas[i:batch_end],  # type: ignore[arg-type]
            )

        logger.info(f"Successfully ingested {total_chunks} chunks from {len(corpus_files)} files")

    return total_chunks


# =============================================================================
# VERIFICATION
# =============================================================================


def verify_ingestion() -> bool:
    """Verify the RAG pipeline works by running a test query.

    Returns:
        True if verification passes
    """
    logger.info("Running verification query...")

    manager = ChromaManager()
    collection = manager.get_or_create_collection(ChromaDBConfig.THEORY_COLLECTION)

    # Check collection has data
    count = collection.count()
    if count == 0:
        logger.error("Collection is empty!")
        return False

    logger.info(f"Collection has {count} chunks")

    # Run a theory-relevant query
    test_query = "What is the principal contradiction?"
    results = collection.query(
        query_texts=[test_query],
        n_results=3,
    )

    if not results["documents"] or not results["documents"][0]:
        logger.error("Query returned no results!")
        return False

    logger.info(f"\nQuery: '{test_query}'")
    logger.info("=" * 60)

    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []

    for i, (doc, metadata) in enumerate(zip(documents, metadatas, strict=False)):
        meta_dict = dict(metadata) if metadata else {}
        title = meta_dict.get("title", "Unknown")
        author = meta_dict.get("author", "Unknown")
        preview = doc[:200] + "..." if len(doc) > 200 else doc
        logger.info(f"\n[{i + 1}] {title} ({author})")
        logger.info(f"    {preview}")

    logger.info("\n" + "=" * 60)
    logger.info("Verification PASSED")
    return True


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest corpus into Babylon's RAG Memory pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Import from external library and ingest
    %(prog)s --import-from /media/user/marxists.org/www.marxists.org/

    # Ingest existing corpus files
    %(prog)s

    # Reset and re-ingest
    %(prog)s --reset

    # Skip verification
    %(prog)s --no-verify
        """,
    )

    parser.add_argument(
        "--import-from",
        type=Path,
        metavar="PATH",
        help="External library path to import texts from",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the collection before ingesting",
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification query after ingestion",
    )

    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path(__file__).parent.parent / "src" / "babylon" / "data" / "corpus",
        metavar="PATH",
        help="Local corpus directory (default: src/babylon/data/corpus/)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Print MVP corpus info
    logger.info("=" * 60)
    logger.info("Babylon Corpus Ingestion Tool")
    logger.info("=" * 60)
    logger.info("\nMVP Vertical Slice Corpus (7 texts):")
    for i, text in enumerate(MVP_CORPUS, 1):
        logger.info(f"  {i}. {text.title} ({text.author}, {text.year})")
    logger.info("")

    # Import from external library if specified
    if args.import_from:
        logger.info(f"\nImporting from: {args.import_from}")
        imported, missing = import_corpus_files(args.import_from, args.corpus_dir)

        logger.info(f"\nImport Summary: Found {imported}/{len(MVP_CORPUS)} texts")
        if missing:
            logger.warning(f"Missing texts: {', '.join(missing)}")

    # Ingest corpus
    logger.info(f"\nIngesting from: {args.corpus_dir}")
    chunks = ingest_corpus(args.corpus_dir, reset=args.reset)

    if chunks == 0:
        logger.error("No chunks ingested!")
        return 1

    logger.info(f"\nIngestion complete: {chunks} chunks")

    # Verify
    if not args.no_verify and not verify_ingestion():
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
