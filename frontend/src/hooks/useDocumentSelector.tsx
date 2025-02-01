import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/router";
import type { ClinicalDocument, GuidelineOption } from "~/types/document";
import { DocumentType, getAllGuidelines } from "~/types/document";
import { backendClient } from "~/api/backend";

export const useDocumentSelector = () => {
  const [availableDocuments, setAvailableDocuments] = useState<
    ClinicalDocument[]
  >([]);
  const [availableGuidelines, setAvailableGuidelines] = useState<
    GuidelineOption[]
  >([]);
  const [selectedGuideline, setSelectedGuideline] =
    useState<GuidelineOption | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const documents = await backendClient.fetchDocuments();
        setAvailableDocuments(documents);
        setAvailableGuidelines(getAllGuidelines(documents));
      } catch (error) {
        console.error("Error fetching documents:", error);
      } finally {
        setIsLoading(false);
      }
    };

    void fetchDocuments();
  }, []);

  const selectedDocuments = useMemo(() => {
    if (!selectedGuideline) return [];

    return availableDocuments.filter(
      (doc) =>
        doc.documentType === DocumentType.CLINICAL_GUIDELINE &&
        (doc.guidelineId === selectedGuideline.value ||
          doc.id === selectedGuideline.value)
    );
  }, [selectedGuideline, availableDocuments]);

  const handleGuidelineChange = (guideline: GuidelineOption) => {
    setSelectedGuideline(guideline);
  };

  return {
    availableGuidelines,
    selectedGuideline,
    selectedDocuments,
    handleGuidelineChange,
    isLoading,
  };
};
