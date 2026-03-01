#!/usr/bin/env python3
"""Corpus ingestion tool for Babylon's RAG pipeline.

This tool imports texts from external libraries (like marxists.org) and
prepares them as chunked Markdown files for RAG ingestion.

NOTE: ChromaDB has been removed. Vector storage is now handled by
pgvector via PgVectorStore (Feature 037). This tool can still import
and prepare corpus files; ingestion into the vector store requires
a running PostgreSQL instance with pgvector.

Usage:
    # Import texts from external library
    poetry run python tools/ingest_corpus.py --import-from /media/user/marxists.org/

    # List corpus status
    poetry run python tools/ingest_corpus.py --list
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Final

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
    # Subdirectories to search in (relative to source root) for targeted scanning
    search_paths: tuple[str, ...] = ()


MVP_CORPUS: Final[tuple[CorpusText, ...]] = (
    CorpusText(
        title="Wage Labour and Capital",
        author="Marx",
        keywords=("wage", "labour", "capital", "wage-labour"),
        year=1849,
        search_paths=("archive/marx/works/1847/wage-labour",),
    ),
    CorpusText(
        title="Value, Price and Profit",
        author="Marx",
        keywords=("value", "price", "profit", "value-price-profit"),
        year=1865,
        search_paths=("archive/marx/works/1865/value-price-profit",),
    ),
    CorpusText(
        title="Principles of Communism",
        author="Engels",
        keywords=("principles", "communism", "prin-com"),
        year=1847,
        search_paths=("archive/marx/works/1847/11",),
    ),
    CorpusText(
        title="Imperialism, the Highest Stage of Capitalism",
        author="Lenin",
        keywords=("imperialism", "highest", "stage", "capitalism", "imp-hsc"),
        year=1916,
        search_paths=("archive/lenin/works/1916/imp-hsc",),
    ),
    CorpusText(
        title="On National Culture",
        author="Fanon",
        keywords=("national", "culture", "national-culture"),
        year=1961,
        search_paths=("subject/africa/fanon",),
    ),
    CorpusText(
        title="On Contradiction",
        author="Mao",
        keywords=("contradiction", "mswv1_17"),
        year=1937,
        search_paths=("reference/archive/mao/selected-works/volume-1",),
    ),
    CorpusText(
        title="Analysis of the Classes in Chinese Society",
        author="Mao",
        keywords=("analysis", "classes", "chinese", "society", "mswv1_1"),
        year=1926,
        search_paths=("reference/archive/mao/selected-works/volume-1",),
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


def convert_html_to_markdown(html_content: str) -> str:
    """Convert HTML content to Markdown format.

    Args:
        html_content: Raw HTML content

    Returns:
        Converted Markdown content
    """
    from markdownify import markdownify

    markdown = markdownify(
        html_content,
        heading_style="atx",
        bullets="-",
        strip=["script", "style", "nav", "footer", "header"],
    )

    # Clean up excessive whitespace
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r" +", " ", markdown)

    return markdown.strip()


def import_multi_chapter_work(
    search_dir: Path,
    text: CorpusText,
    dest_path: Path,
) -> bool:
    """Import a multi-chapter work by concatenating all chapter files.

    Args:
        search_dir: Directory containing chapter files (ch01.htm, ch02.htm, etc.)
        text: The corpus text metadata
        dest_path: Destination path for the combined Markdown file

    Returns:
        True if successful, False otherwise
    """
    chapter_files = sorted(search_dir.glob("ch*.htm"))
    if not chapter_files:
        chapter_files = sorted(search_dir.glob("ch*.html"))

    if not chapter_files:
        return False

    logger.info(f"Found {len(chapter_files)} chapters for '{text.title}'")

    # Also look for intro/preface files
    intro_files: list[Path] = []
    for name in ["intro.htm", "introduction.htm", "pref01.htm", "pref02.htm", "preface.htm"]:
        intro_path = search_dir / name
        if intro_path.exists():
            intro_files.append(intro_path)

    all_files = sorted(intro_files) + chapter_files
    combined_content: list[str] = []

    for file_path in all_files:
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                raw_html = f.read()
            chapter_md = convert_html_to_markdown(raw_html)
            if chapter_md.strip():
                combined_content.append(chapter_md)
        except Exception as e:
            logger.warning(f"Failed to read chapter {file_path.name}: {e}")

    if not combined_content:
        return False

    full_content = f"# {text.title}\n\n**Author:** {text.author}\n\n---\n\n"
    full_content += "\n\n---\n\n".join(combined_content)

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    logger.info(f"Combined {len(all_files)} files -> {dest_path.name}")
    return True


def import_corpus_files(source_dir: Path, corpus_dir: Path) -> tuple[int, list[str]]:
    """Import matching files from external library to corpus directory.

    Args:
        source_dir: External library path to import from
        corpus_dir: Local corpus directory to copy files to

    Returns:
        Tuple of (number imported, list of missing text titles)
    """
    corpus_dir.mkdir(parents=True, exist_ok=True)

    imported = 0
    missing: list[str] = []

    for text in MVP_CORPUS:
        safe_title = re.sub(r"[^\w\s-]", "", text.title).replace(" ", "_").lower()
        safe_author = text.author.lower()
        dest_filename = f"{safe_author}_{safe_title}.md"
        dest_path = corpus_dir / dest_filename

        success = False

        for subpath in text.search_paths:
            search_dir = source_dir / subpath
            if not search_dir.exists():
                continue

            chapter_files = list(search_dir.glob("ch*.htm")) + list(search_dir.glob("ch*.html"))
            if chapter_files:
                success = import_multi_chapter_work(search_dir, text, dest_path)
                if success:
                    logger.info(f"Imported multi-chapter: {text.title}")
                    break
            else:
                for ext in (".htm", ".html", ".txt", ".md"):
                    for file_path in search_dir.glob(f"*{ext}"):
                        filename = file_path.stem
                        score = fuzzy_match_score(filename, text)
                        if score > 0.5:
                            try:
                                with open(file_path, encoding="utf-8", errors="replace") as f:
                                    raw_html = f.read()
                                content = convert_html_to_markdown(raw_html)

                                with open(dest_path, "w", encoding="utf-8") as f:
                                    f.write(content)

                                logger.info(f"Imported: {text.title} -> {dest_filename}")
                                success = True
                                break
                            except Exception as e:
                                logger.error(f"Failed to import {file_path}: {e}")
                    if success:
                        break
            if success:
                break

        if success:
            imported += 1
        else:
            missing.append(f"{text.title} ({text.author})")

    return imported, missing


def list_corpus(corpus_dir: Path) -> None:
    """List corpus files and their status.

    Args:
        corpus_dir: Directory containing corpus files
    """
    if not corpus_dir.exists():
        logger.info(f"Corpus directory does not exist: {corpus_dir}")
        return

    extensions = (".txt", ".md", ".htm", ".html")
    corpus_files = sorted(f for ext in extensions for f in corpus_dir.glob(f"*{ext}"))

    if not corpus_files:
        logger.info("No corpus files found.")
        return

    logger.info(f"Corpus directory: {corpus_dir}")
    logger.info(f"Files found: {len(corpus_files)}")
    for f in corpus_files:
        size_kb = f.stat().st_size / 1024
        logger.info(f"  {f.name} ({size_kb:.1f} KB)")


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import corpus texts for Babylon's RAG pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Import from external library
    %(prog)s --import-from /media/user/marxists.org/www.marxists.org/

    # List corpus status
    %(prog)s --list

Note: Vector ingestion requires pgvector (Feature 037).
        """,
    )

    parser.add_argument(
        "--import-from",
        type=Path,
        metavar="PATH",
        help="External library path to import texts from",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List corpus files and their status",
    )

    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "corpus",
        metavar="PATH",
        help="Local corpus directory (default: data/corpus/)",
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
    logger.info("Babylon Corpus Tool")
    logger.info("=" * 60)
    logger.info("\nMVP Vertical Slice Corpus (7 texts):")
    for i, text in enumerate(MVP_CORPUS, 1):
        logger.info(f"  {i}. {text.title} ({text.author}, {text.year})")
    logger.info("")

    if args.list:
        list_corpus(args.corpus_dir)
        return 0

    # Import from external library if specified
    if args.import_from:
        logger.info(f"\nImporting from: {args.import_from}")
        imported, missing = import_corpus_files(args.import_from, args.corpus_dir)

        logger.info(f"\nImport Summary: Found {imported}/{len(MVP_CORPUS)} texts")
        if missing:
            logger.warning(f"Missing texts: {', '.join(missing)}")
        return 0

    # No action specified
    logger.info("No action specified. Use --import-from to import, or --list to view status.")
    logger.info("Vector ingestion requires pgvector backend (Feature 037).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
