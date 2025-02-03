"""
Clinical guideline document processor using LlamaIndex.
Handles the parsing and chunking of clinical guideline PDFs into indexable nodes.
"""
from pathlib import Path
from typing import Dict, List, Optional, Any

from llama_index.readers import PDFReader
from llama_index.schema import Document as LlamaIndexDocument
from llama_index.node_parser import SentenceSplitter

from app.schema import DocumentMetadataKeysEnum, EvidenceGradeEnum


class GuidelineProcessor:
    """
    Processor for clinical guideline documents.
    
    Features:
        - Specialized PDF processing for clinical guidelines
        - Smart chunking with sentence-level splitting
        - Metadata preservation across chunks
        - Configurable chunk sizes for optimal retrieval
    """
    
    def __init__(self):
        """
        Initialize processor with PDF reader and chunking settings.
        
        Process:
            1. Sets up PDFReader for document loading
            2. Configures SentenceSplitter with:
               - 512 token chunk size for precise retrieval
               - 50 token overlap for context preservation
        """
        self.reader = PDFReader()
        self.node_parser = SentenceSplitter.from_defaults(
            chunk_size=512,  # Smaller chunks for more precise retrieval
            chunk_overlap=50
        )
    
    def process_document(
        self,
        file_path: Path,
        metadata: Dict[str, Any]
    ) -> List[LlamaIndexDocument]:
        """
        Process a clinical guideline document into searchable chunks.
        
        Process:
            1. Reads PDF into raw document objects
            2. Extracts clinical guideline metadata
            3. For each document section:
               - Adds metadata (title, org, date)
               - Splits into semantic chunks
               - Preserves clinical context
            4. Returns list of processed nodes
        """
        # Read the PDF file
        raw_docs = self.reader.load_data(file_path)
        
        # Extract guideline metadata
        guideline_metadata = metadata.get(DocumentMetadataKeysEnum.CLINICAL_GUIDELINE, {})
        
        # Parse into nodes with metadata
        nodes = []
        for doc in raw_docs:
            # Add guideline metadata to each node
            doc.metadata.update({
                "doc_id": metadata.get("doc_id"),
                "guideline_title": guideline_metadata.get("title"),
                "issuing_org": guideline_metadata.get("issuing_organization"),
                "publication_date": guideline_metadata.get("publication_date"),
                "document_type": "clinical_guideline"
            })
            
            # Split into smaller chunks while preserving metadata
            sub_nodes = self.node_parser.get_nodes_from_documents([doc])
            nodes.extend(sub_nodes)
        
        return nodes
