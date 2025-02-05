// ViewPdf.tsx
import usePDFViewer from "~/hooks/usePdfViewer";
import { PDFOptionsBar } from "./PdfOptionsBar";
import React from "react";
import MemoizedVirtualizedPDF from "./VirtualizedPdf";
import type { ClinicalDocument } from "~/types/document";

interface ViewPdfProps {
  file: ClinicalDocument;
}

export const ViewPdf: React.FC<ViewPdfProps> = ({ file }) => {
  console.log("ViewPdf rendering with file:", file);

  // Use the S3 URL directly from the file object
  const {
    scrolledIndex,
    setCurrentPageNumber,
    scale,
    setScaleFit,
    numPages,
    setNumPages,
    handleZoomIn,
    handleZoomOut,
    nextPage,
    prevPage,
    scaleText,
    pdfFocusRef,
    goToPage,
    setZoomLevel,
    zoomInEnabled,
    zoomOutEnabled,
  } = usePDFViewer(file);

  const getAssetUrl = (url: string) => {
    // In development, proxy through backend
    if (process.env.NODE_ENV === "development") {
      const filename = url.split("/").pop();
      return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/document/assets/${filename}`;
    }

    // In production, use the URL directly (will be a CloudFront/CDN URL)
    return url;
  };

  if (!file || !file.url) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-gray-500">No PDF available</p>
      </div>
    );
  }

  const assetUrl = getAssetUrl(file.url);

  return (
    <div className="relative flex h-full flex-col">
      {scaleText && (
        <PDFOptionsBar
          file={file}
          scrolledIndex={scrolledIndex}
          numPages={numPages}
          scaleText={scaleText}
          nextPage={nextPage}
          prevPage={prevPage}
          handleZoomIn={handleZoomIn}
          handleZoomOut={handleZoomOut}
          goToPage={goToPage}
          setZoomLevel={setZoomLevel}
          zoomInEnabled={zoomInEnabled}
          zoomOutEnabled={zoomOutEnabled}
        />
      )}

      <div className="flex-1 overflow-hidden">
        <MemoizedVirtualizedPDF
          key={`${file.id}-${file.url}`}
          ref={pdfFocusRef}
          file={{ url: assetUrl }}
          setIndex={setCurrentPageNumber}
          scale={scale}
          setScaleFit={setScaleFit}
          setNumPages={setNumPages}
        />
      </div>

      {/* Document Info Panel */}
      <div className="absolute bottom-0 left-0 right-0 border-t bg-white bg-opacity-90 p-4">
        <h3 className="font-medium text-gray-900">{file.title}</h3>
        <div className="mt-1 text-sm text-gray-600">
          <p>Organization: {file.issuingOrganization}</p>
          <p>
            Published:{" "}
            {file.publicationDate
              ? new Date(file.publicationDate).toLocaleDateString()
              : "Not available"}
          </p>
          {file.version && <p>Version: {file.version}</p>}
        </div>
      </div>
    </div>
  );
};
