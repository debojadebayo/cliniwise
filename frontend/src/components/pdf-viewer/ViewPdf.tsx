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

  const getProxiedUrl = (url: string) => {
    const filename = url.split('/').pop();
    const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, '') || 'http://localhost:8000';
    return `${baseUrl}/api/document/assets/${filename}`;
  };

  if (!file || !file.url) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-gray-500">No PDF available</p>
      </div>
    );
  }

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
          key={`${file.id}`}
          ref={pdfFocusRef}
          file={{ ...file, url: getProxiedUrl(file.url) }}
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
