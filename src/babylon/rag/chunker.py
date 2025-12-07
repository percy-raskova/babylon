"""Document chunking and preprocessing for the RAG system."""

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from babylon.rag.exceptions import ChunkingError, PreprocessingError

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """Represents a chunk of a document with metadata."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = ""
    content: str
    source_file: str | None = None
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    metadata: dict[str, Any] | None = None
    embedding: list[float] | None = None

    @model_validator(mode="after")
    def generate_id_if_empty(self) -> "DocumentChunk":
        """Generate ID if not provided."""
        if not self.id:
            content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:12]
            object.__setattr__(self, "id", f"chunk_{content_hash}_{self.chunk_index}")
        return self


class Preprocessor:
    """Preprocesses documents for chunking and embedding."""

    def __init__(
        self,
        min_content_length: int = 50,
        max_content_length: int = 100000,
        remove_extra_whitespace: bool = True,
        normalize_unicode: bool = True,
    ):
        """Initialize the preprocessor.

        Args:
            min_content_length: Minimum acceptable content length
            max_content_length: Maximum acceptable content length
            remove_extra_whitespace: Whether to normalize whitespace
            normalize_unicode: Whether to normalize unicode characters
        """
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
        self.remove_extra_whitespace = remove_extra_whitespace
        self.normalize_unicode = normalize_unicode

    def preprocess(self, content: str, content_id: str | None = None) -> str:
        """Preprocess content for chunking.

        Args:
            content: Raw content to preprocess
            content_id: Optional identifier for error reporting

        Returns:
            Preprocessed content

        Raises:
            PreprocessingError: If content fails validation or preprocessing
        """
        if not content or not content.strip():
            raise PreprocessingError(
                message="Content is empty or contains only whitespace",
                error_code="RAG_401",
                content_id=content_id,
            )

        # Normalize unicode if requested
        if self.normalize_unicode:
            import unicodedata

            content = unicodedata.normalize("NFKC", content)

        # Remove extra whitespace if requested
        if self.remove_extra_whitespace:
            # Replace multiple whitespace with single space
            content = re.sub(r"\s+", " ", content)
            # Remove leading/trailing whitespace from lines
            content = "\n".join(line.strip() for line in content.split("\n"))
            # Remove excessive newlines
            content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        content = content.strip()

        # Validate content length
        if len(content) < self.min_content_length:
            raise PreprocessingError(
                message=f"Content too short: {len(content)} < {self.min_content_length} characters",
                error_code="RAG_401",
                content_id=content_id,
            )

        if len(content) > self.max_content_length:
            raise PreprocessingError(
                message=f"Content too long: {len(content)} > {self.max_content_length} characters",
                error_code="RAG_402",
                content_id=content_id,
            )

        return content


class TextChunker:
    """Chunks text into smaller, contextually meaningful pieces."""

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap_size: int = 100,
        preserve_paragraphs: bool = True,
        preserve_sentences: bool = True,
    ):
        """Initialize the chunker.

        Args:
            chunk_size: Target size for each chunk in characters
            overlap_size: Number of overlapping characters between chunks
            preserve_paragraphs: Try to avoid splitting paragraphs
            preserve_sentences: Try to avoid splitting sentences
        """
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if overlap_size < 0:
            raise ValueError("Overlap size must be non-negative")
        if overlap_size >= chunk_size:
            raise ValueError("Overlap size must be less than chunk size")

        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.preserve_paragraphs = preserve_paragraphs
        self.preserve_sentences = preserve_sentences

    def chunk_text(
        self, content: str, source_file: str | None = None, metadata: dict[str, Any] | None = None
    ) -> list[DocumentChunk]:
        """Chunk text content into DocumentChunk objects.

        Args:
            content: Text content to chunk
            source_file: Optional source file path
            metadata: Optional metadata to attach to chunks

        Returns:
            List of DocumentChunk objects

        Raises:
            ChunkingError: If chunking fails
        """
        if not content:
            raise ChunkingError(
                message="Cannot chunk empty content",
                error_code="RAG_421",
                content_id=source_file,
            )

        try:
            chunks = []
            start_pos = 0
            chunk_index = 0

            while start_pos < len(content):
                end_pos = min(start_pos + self.chunk_size, len(content))

                # Try to find a good breaking point
                if end_pos < len(content):
                    end_pos = self._find_break_point(content, start_pos, end_pos)

                chunk_content = content[start_pos:end_pos].strip()

                if chunk_content:
                    chunk = DocumentChunk(
                        id="",  # Will be generated in __post_init__
                        content=chunk_content,
                        source_file=source_file,
                        chunk_index=chunk_index,
                        start_char=start_pos,
                        end_char=end_pos,
                        metadata=metadata.copy() if metadata else None,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # Move to next chunk with overlap
                start_pos = max(start_pos + 1, end_pos - self.overlap_size)

                # Prevent infinite loop
                if start_pos >= end_pos:
                    start_pos = end_pos

            logger.info(f"Created {len(chunks)} chunks from content of length {len(content)}")
            return chunks

        except Exception as e:
            raise ChunkingError(
                message=f"Failed to chunk content: {str(e)}",
                error_code="RAG_424",
                content_id=source_file,
            ) from e

    def _find_break_point(self, content: str, start_pos: int, end_pos: int) -> int:
        """Find the best position to break a chunk."""
        search_start = max(start_pos, end_pos - 200)  # Look back up to 200 chars

        # Try to break at paragraph boundary
        if self.preserve_paragraphs:
            paragraph_break = content.rfind("\n\n", search_start, end_pos)
            if paragraph_break > search_start:
                return paragraph_break + 2  # Include the double newline

        # Try to break at sentence boundary
        if self.preserve_sentences:
            sentence_break = self._find_sentence_break(content, search_start, end_pos)
            if sentence_break > search_start:
                return sentence_break

        # Fall back to word boundary
        word_break = content.rfind(" ", search_start, end_pos)
        if word_break > search_start:
            return word_break + 1

        # If no good break point found, use original end position
        return end_pos

    def _find_sentence_break(self, content: str, start_pos: int, end_pos: int) -> int:
        """Find the last sentence break in the given range."""
        sentence_endings = ".!?"
        best_break = -1

        for i in range(end_pos - 1, start_pos - 1, -1):
            if (
                content[i] in sentence_endings
                and i + 1 < len(content)
                and (content[i + 1].isspace() or content[i + 1] == '"')
                and not self._is_abbreviation(content, i)
            ):
                best_break = i + 1
                break

        return best_break if best_break > start_pos else -1

    def _is_abbreviation(self, content: str, pos: int) -> bool:
        """Check if a period is likely part of an abbreviation."""
        if pos < 1:
            return False

        # Common abbreviations to avoid breaking on
        abbrevs = {"Dr", "Mr", "Mrs", "Ms", "Prof", "Sr", "Jr", "etc", "vs", "e.g", "i.e"}

        # Look for word before the period
        start = pos - 1
        while start >= 0 and content[start].isalnum():
            start -= 1
        start += 1

        if start < pos:
            word = content[start:pos]
            return word in abbrevs or (len(word) <= 3 and word.isupper())

        return False


class DocumentProcessor:
    """High-level document processor that combines preprocessing and chunking."""

    def __init__(
        self,
        preprocessor: Preprocessor | None = None,
        chunker: TextChunker | None = None,
    ):
        """Initialize the document processor.

        Args:
            preprocessor: Optional custom preprocessor (uses default if None)
            chunker: Optional custom chunker (uses default if None)
        """
        self.preprocessor = preprocessor or Preprocessor()
        self.chunker = chunker or TextChunker()

    def process_text(
        self, content: str, source_file: str | None = None, metadata: dict[str, Any] | None = None
    ) -> list[DocumentChunk]:
        """Process raw text into document chunks.

        Args:
            content: Raw text content
            source_file: Optional source file path
            metadata: Optional metadata to attach to chunks

        Returns:
            List of processed DocumentChunk objects

        Raises:
            PreprocessingError: If preprocessing fails
            ChunkingError: If chunking fails
        """
        # Preprocess the content
        processed_content = self.preprocessor.preprocess(content, source_file)

        # Chunk the processed content
        chunks = self.chunker.chunk_text(processed_content, source_file, metadata)

        return chunks

    def process_file(self, file_path: str, encoding: str = "utf-8") -> list[DocumentChunk]:
        """Process a text file into document chunks.

        Args:
            file_path: Path to the text file
            encoding: File encoding (default: utf-8)

        Returns:
            List of processed DocumentChunk objects

        Raises:
            FileNotFoundError: If file doesn't exist
            PreprocessingError: If preprocessing fails
            ChunkingError: If chunking fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(path, encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError as e:
            raise PreprocessingError(
                message=f"Failed to decode file with encoding {encoding}: {str(e)}",
                error_code="RAG_403",
                content_id=file_path,
            ) from e

        metadata = {
            "source_type": "file",
            "file_path": str(path.absolute()),
            "file_name": path.name,
            "file_size": path.stat().st_size,
        }

        return self.process_text(content, file_path, metadata)
