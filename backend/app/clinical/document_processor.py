"""
Clinical guideline document processor using LlamaIndex.
"""
from pathlib import Path
from typing import Dict, List, Optional, Any

from llama_index.readers import PDFReader
from llama_index.schema import Document as LlamaIndexDocument
from llama_index.node_parser import SentenceSplitter

from app.schema import DocumentMetadataKeysEnum, EvidenceGradeEnum


class GuidelineProcessor:
    """Processor for clinical guideline documents."""
    
    def __init__(self):
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
        Process a clinical guideline document.
        
        Args:
            file_path: Path to the PDF file
            metadata: Document metadata including guideline information
            
        Returns:
            List of LlamaIndex Document objects with appropriate metadata
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
