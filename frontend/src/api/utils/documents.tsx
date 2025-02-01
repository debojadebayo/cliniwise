import type {
  BackendDocument,
  BackendMetadataMap,
} from "~/types/backend/document";
import type { ClinicalDocument } from "~/types/document";
import { DocumentType } from "~/types/document";

export const fromBackendDocumentToFrontend = (
  backendDocuments: BackendDocument[]
): ClinicalDocument[] => {
  return backendDocuments
    .filter(
      (
        doc
      ): doc is BackendDocument & {
        metadata_map: {
          clinical_guideline: NonNullable<
            BackendMetadataMap["clinical_guideline"]
          >;
        };
      } => !!doc.metadata_map?.clinical_guideline
    )
    .map((doc) => {
      const metadata = doc.metadata_map.clinical_guideline;
      return {
        id: doc.id, // Database UUID
        title: metadata.title,
        issuingOrganization: metadata.issuing_organization,
        publicationDate: metadata.publication_date,
        version: metadata.version,
        condition: metadata.condition,
        specialty: metadata.specialty,
        targetPopulation: metadata.target_population,
        evidenceGradingSystem: metadata.evidence_grading_system,
        recommendationCount: metadata.recommendation_count,
        lastUpdate: metadata.last_update,
        nextReview: metadata.next_review,
        guidelineId: metadata.guideline_id, // External ID if available
        documentType: DocumentType.CLINICAL_GUIDELINE,
        url: doc.url, // URL for PDF viewer
      };
    });
};
