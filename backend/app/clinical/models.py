from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base_class import Base

class ClinicalGuideline(Base):
    """Model for storing clinical guideline metadata and content."""
    __tablename__ = "clinical_guidelines"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core Identification
    title = Column(String, index=True, nullable=False)
    issuing_organization = Column(String, index=True, nullable=False)
    publication_date = Column(DateTime)
    version = Column(String)
    
    # Clinical Context
    condition = Column(String, index=True)
    specialty = Column(String, index=True)
    target_population = Column(String)
    
    # Document Structure
    evidence_grading_system = Column(String)
    has_recommendations = Column(Boolean, default=False)
    has_evidence_tables = Column(Boolean, default=False)
    has_algorithms = Column(Boolean, default=False)
    recommendation_count = Column(Integer, default=0)
    
    # Content Statistics
    page_count = Column(Integer)
    table_count = Column(Integer)
    figure_count = Column(Integer)
    
    # Storage
    s3_url = Column(String, unique=True)
    file_hash = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Organization-specific
    guideline_number = Column(String)  # e.g., "NG157" for NICE
    guideline_type = Column(String)  # e.g., "Clinical Practice Guideline"
    
    # Raw extracted content
    raw_text = Column(String)  # Full text content
    metadata = Column(JSONB)  # Additional metadata as JSON
    
    # Relationships
    sections = relationship("GuidelineSection", back_populates="guideline")
    recommendations = relationship("GuidelineRecommendation", back_populates="guideline")

class GuidelineSection(Base):
    """Model for storing sections of a clinical guideline."""
    __tablename__ = "guideline_sections"

    id = Column(Integer, primary_key=True, index=True)
    guideline_id = Column(Integer, ForeignKey("clinical_guidelines.id"))
    
    title = Column(String, index=True)
    content = Column(String)
    section_type = Column(String)  # e.g., "introduction", "methods", "recommendations"
    page_number = Column(Integer)
    sequence_number = Column(Integer)  # For ordering sections
    
    # Location tracking
    start_offset = Column(Integer)  # Character offset in the document where section starts
    end_offset = Column(Integer)    # Character offset where section ends
    
    # Relationships
    guideline = relationship("ClinicalGuideline", back_populates="sections")
    recommendations = relationship("GuidelineRecommendation", back_populates="section")

class GuidelineRecommendation(Base):
    """Model for storing individual recommendations from guidelines."""
    __tablename__ = "guideline_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    guideline_id = Column(Integer, ForeignKey("clinical_guidelines.id"))
    section_id = Column(Integer, ForeignKey("guideline_sections.id"))
    
    content = Column(String, nullable=False)
    evidence_grade = Column(String)  # e.g., "1A", "Strong", "Grade B"
    recommendation_type = Column(String)  # e.g., "diagnostic", "therapeutic"
    strength = Column(String)  # e.g., "strong", "weak", "conditional"
    
    # Detailed location tracking
    page_number = Column(Integer)
    paragraph_number = Column(Integer)  # Number of the paragraph within the page
    start_offset = Column(Integer)  # Character offset in the document where recommendation starts
    end_offset = Column(Integer)    # Character offset where recommendation ends
    surrounding_context = Column(String)  # Text before and after the recommendation for context
    
    # Additional context
    context = Column(JSONB)  # Store related conditions, populations, etc.
    
    # Relationships
    guideline = relationship("ClinicalGuideline", back_populates="recommendations")
    section = relationship("GuidelineSection", back_populates="recommendations")
