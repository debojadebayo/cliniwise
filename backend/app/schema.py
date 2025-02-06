"""
Pydantic Schemas for the API
"""
from pydantic import BaseModel, Field, validator
from enum import Enum
from typing import List, Optional, Dict, Union, Any
from uuid import UUID
from datetime import datetime
from llama_index.schema import BaseNode, NodeWithScore
from llama_index.callbacks.schema import EventPayload
from llama_index.query_engine.sub_question_query_engine import SubQuestionAnswerPair
from app.models.db import (
    MessageRoleEnum,
    MessageStatusEnum,
    MessageSubProcessSourceEnum,
    MessageSubProcessStatusEnum,
)
from app.chat.constants import DB_DOC_ID_KEY


def build_uuid_validator(*field_names: str):
    return validator(*field_names)(lambda x: str(x) if x else x)


class Base(BaseModel):
    id: Optional[UUID] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(None, description="Creation datetime")
    updated_at: Optional[datetime] = Field(None, description="Update datetime")

    class Config:
        orm_mode = True


class BaseMetadataObject(BaseModel):
    class Config:
        orm_mode = True


class Citation(BaseMetadataObject):
    document_id: UUID
    text: str
    page_number: int
    score: Optional[float]

    @validator("document_id")
    def validate_document_id(cls, value):
        if value:
            return str(value)
        return value

    @classmethod
    def from_node_with_score(cls, node: NodeWithScore, **kwargs) -> "Citation":
        """Create a Citation from a NodeWithScore object"""
        return cls(
            document_id=node.node.metadata[DB_DOC_ID_KEY],
            text=node.node.text,
            page_number=node.node.metadata.get("page_number", 1),
            score=node.score,
            **kwargs,
        )


class QuestionAnswerPair(BaseModel):
    """A question-answer pair that is used to store the sub-questions and answers"""

    question: str
    answer: Optional[str]
    citations: Optional[List[Citation]] = None

    @classmethod
    def from_sub_question_answer_pair(
        cls, sub_question_answer_pair: SubQuestionAnswerPair
    ) -> "QuestionAnswerPair":
        """Create a QuestionAnswerPair from a SubQuestionAnswerPair object"""
        citations = None
        if (
            sub_question_answer_pair.answer is not None
            and sub_question_answer_pair.answer.source_nodes is not None
        ):
            citations = [
                Citation.from_node_with_score(node)
                for node in sub_question_answer_pair.answer.source_nodes
            ]

        return cls(
            question=sub_question_answer_pair.sub_q.sub_question,
            answer=sub_question_answer_pair.answer.response
            if sub_question_answer_pair.answer
            else None,
            citations=citations,
        )


class SubProcessMetadataKeysEnum(str, Enum):
    SUB_QUESTION = EventPayload.SUB_QUESTION.value


# keeping the typing pretty loose here, in case there are changes to the metadata data formats.
SubProcessMetadataMap = Dict[Union[SubProcessMetadataKeysEnum, str], Any]


class MessageSubProcess(BaseModel):
    message_id: UUID
    source: MessageSubProcessSourceEnum
    status: MessageSubProcessStatusEnum
    metadata_map: Optional[SubProcessMetadataMap]


class Message(BaseModel):
    conversation_id: UUID
    content: str
    role: MessageRoleEnum
    status: MessageStatusEnum
    sub_processes: List[MessageSubProcess]


class UserMessageCreate(BaseModel):
    content: str


class DocumentMetadataKeysEnum(str, Enum):
    """Enum for the keys of the metadata map for a document"""
    CLINICAL_GUIDELINE = "clinical_guideline"


class EvidenceGradeEnum(str, Enum):
    """Enum for clinical guideline evidence grades"""
    GRADE_A = "A"
    GRADE_B = "B"
    GRADE_C = "C"
    GRADE_D = "D"
    GRADE_I = "I"
    GOOD_PRACTICE = "GPP"
    EXPERT_OPINION = "EO"
    NOT_GRADED = "NG"


class ClinicalGuidelineMetadata(BaseModel):
    """Metadata for a clinical guideline document"""
    title: str
    issuing_organization: str
    publication_date: Optional[datetime]
    version: Optional[str]
    condition: Optional[str]
    specialty: Optional[str]
    target_population: Optional[str]
    evidence_grading_system: Optional[str]
    recommendation_count: Optional[int]
    last_update: Optional[datetime]
    next_review: Optional[datetime]
    guideline_id: Optional[str]

    class Config:
        orm_mode = True


DocumentMetadataMap = Dict[Union[DocumentMetadataKeysEnum, str], Any]


class Document(Base):
    url: str
    metadata_map: Optional[DocumentMetadataMap] = None


class Conversation(Base):
    messages: List[Message]
    documents: List[Document]


class ConversationCreate(BaseModel):
    document_ids: List[UUID]
