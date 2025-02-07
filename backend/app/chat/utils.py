from app.schema import (
    Document as DocumentSchema,
    DocumentMetadataKeysEnum,
    ClinicalGuidelineMetadata
)


def build_title_for_document(document: DocumentSchema) -> str:
    if DocumentMetadataKeysEnum.CLINICAL_GUIDELINE not in document.metadata_map:
        return "No Title Document"

    clinical_metadata = ClinicalGuidelineMetadata.parse_obj(
        document.metadata_map[DocumentMetadataKeysEnum.CLINICAL_GUIDELINE]
    )
    
    return f"{clinical_metadata.title}-{clinical_metadata.issuing_organization}"