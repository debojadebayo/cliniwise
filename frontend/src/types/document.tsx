import { SelectOption } from "./selection";

export enum DocumentType {
  CLINICAL_GUIDELINE = "clinical_guideline",
}

// main document type
export interface ClinicalDocument {
  id: string;
  title: string;
  issuingOrganization: string;
  publicationDate?: string;
  version?: string;
  condition?: string;
  specialty?: string;
  evidenceGradingSystem?: string;
  recommendationCount?: number;
  lastUpdate?: string;
  nextReview?: string;
  guidelineId?: string;
  documentType: DocumentType;
  url: string;
}

// dropdown type- minimal types needed for dropdown
export interface GuidelineOption extends SelectOption {
  document: ClinicalDocument;
}

export const createGuidelineOption = (
  doc: ClinicalDocument
): GuidelineOption => ({
  value: doc.id,
  label: `${doc.title} - ${doc.issuingOrganization}`,
  document: doc,
});

export const getAllGuidelines = (
  documents: ClinicalDocument[]
): GuidelineOption[] => {
  const guidelines = documents
    .filter((doc) => doc.documentType === DocumentType.CLINICAL_GUIDELINE)
    .map(createGuidelineOption);

  return Array.from(new Set(guidelines));
};
