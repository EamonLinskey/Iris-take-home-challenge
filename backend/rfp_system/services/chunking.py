"""
Text chunking service - splits documents into manageable chunks with overlap
"""
from typing import List, Dict
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken


class TextChunker:
    """Split text into chunks for embedding and retrieval"""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 200,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize text chunker

        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            encoding_name: Tokenizer encoding to use
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

        # LangChain splitter that respects paragraph boundaries
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self._token_length,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def _token_length(self, text: str) -> int:
        """Calculate token length of text"""
        return len(self.encoding.encode(text))

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text into chunks

        Args:
            text: Text content to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text or not text.strip():
            return []

        # Split text using LangChain
        chunks = self.splitter.split_text(text)

        # Create chunk dictionaries with metadata
        chunk_list = []
        for idx, chunk_content in enumerate(chunks):
            chunk_dict = {
                'content': chunk_content,
                'chunk_index': idx,
                'token_count': self._token_length(chunk_content),
                'metadata': metadata or {}
            }
            chunk_list.append(chunk_dict)

        return chunk_list

    def chunk_with_page_tracking(
        self,
        text: str,
        page_breaks: List[int] = None,
        metadata: Dict = None
    ) -> List[Dict]:
        """
        Chunk text while tracking which page each chunk comes from

        Args:
            text: Text content to chunk
            page_breaks: List of character positions where pages break
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with page information
        """
        chunks = self.chunk_text(text, metadata)

        # Add page tracking if page breaks provided
        if page_breaks:
            current_pos = 0
            for chunk in chunks:
                chunk_text = chunk['content']
                chunk_start = text.find(chunk_text, current_pos)

                # Find which page this chunk starts on
                page_num = 1
                for break_pos in page_breaks:
                    if chunk_start >= break_pos:
                        page_num += 1
                    else:
                        break

                chunk['metadata']['page_number'] = page_num
                current_pos = chunk_start + len(chunk_text)

        return chunks
