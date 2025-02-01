export interface BackendDocument {
  id: string; // UUID from database
  created_at: string;
  updated_at: string;
  url: string;
  metadata_map: BackendMetadataMap;
}

export interface BackendMetadataMap {
  clinical_guideline?: ClinicalGuideline;
}

// Matches backend schema.py ClinicalGuidelineMetadata
export interface ClinicalGuideline {
  title: string;
  issuing_organization: string;
  publication_date?: string; // datetime from backend
  version?: string;
  condition?: string;
  specialty?: string;
  target_population?: string;
  evidence_grading_system?: string;
  recommendation_count?: number; // integer
  last_update?: string; // datetime
  next_review?: string; // datetime
  guideline_id?: string; // Optional external ID
}
