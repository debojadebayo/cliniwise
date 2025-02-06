import type { ClinicalDocument, DocumentType } from "~/types/document";
import type { SelectOption } from "~/types/selection";

export function getAllConditions(documents: ClinicalDocument[]): string[] {
  const result: string[] = [];
  const seen: { [key: string]: boolean } = {};

  for (const doc of documents) {
    if (!doc.condition || seen[doc.condition]) {
      continue;
    }

    seen[doc.condition] = true;
    result.push(doc.condition);
  }

  return result;
}

export function filterByConditionAndType(
  condition: string,
  docType: DocumentType,
  documents: ClinicalDocument[]
): ClinicalDocument[] {
  if (!condition) {
    return [];
  }
  return documents.filter(
    (document) =>
      document.condition === condition && document.documentType === docType
  );
}

export function findDocumentById(
  id: string,
  documents: ClinicalDocument[]
): ClinicalDocument | null {
  return documents.find((val) => val.id === id) || null;
}

export function sortDocuments(
  selectedDocuments: ClinicalDocument[]
): ClinicalDocument[] {
  return selectedDocuments.sort((a, b) => {
    // Sort by title
    const nameComparison = a.title.localeCompare(b.title);
    if (nameComparison !== 0) return nameComparison;

    // If titles are equal, sort by publication date
    return (a.publicationDate || "").localeCompare(b.publicationDate || "");
  });
}

export function sortSelectOptions(
  options: SelectOption[] | null = []
): SelectOption[] {
  if (!options) return [];
  return options.sort((a, b) => a.label.localeCompare(b.label));
}
