import fitz  # PyMuPDF
import sys
from pathlib import Path
import re
from collections import defaultdict
from typing import Dict, List, Set

class GuidelineAnalyzer:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        
        # Common patterns across different guideline formats
        self.recommendation_patterns = [
            r'(?i)recommendation',
            r'(?i)we recommend',
            r'(?i)should be',
            r'(?i)must be',
            r'(?i)is recommended',
            r'(?i)guidelines recommend',
            r'•\s+',  # Bullet points
            r'^\d+\.\d+\s+',  # Numbered recommendations like 1.1, 1.2
            r'(?i)grade \d+',
            r'(?i)class \d+',
            r'(?i)level \d+',
        ]
        
        # Evidence grading systems used by different organizations
        self.evidence_patterns = [
            r'(?i)grade[:\s]+([A-D]|\d+)',
            r'(?i)level[:\s]+([A-D]|\d+)',
            r'(?i)class[:\s]+([A-D]|\d+)',
            r'(?i)\((?:level|grade|class)\s+([A-D]|\d+)\)',
            r'\(([I]+,\s*[1-3])\)',  # EASL style (I,1)
            r'\[([1-5][A-C])\]',     # Some guidelines use [1A], [2B] etc.
        ]
        
        # Common section headers in guidelines
        self.section_patterns = [
            r'(?i)introduction',
            r'(?i)background',
            r'(?i)methods',
            r'(?i)recommendations',
            r'(?i)discussion',
            r'(?i)conclusion',
            r'(?i)references',
            r'(?i)appendix',
            r'(?i)summary',
            r'(?i)assessment',
            r'(?i)treatment',
            r'(?i)management',
        ]

    def analyze_structure(self):
        """Analyze the document structure and patterns."""
        print(f"\nAnalyzing PDF: {self.pdf_path}")
        
        # Basic document info
        print("\n=== Document Information ===")
        print(f"Number of pages: {len(self.doc)}")
        print(f"Metadata: {self.doc.metadata}")
        
        # Analyze document structure
        self.analyze_sections()
        self.analyze_recommendations()
        self.analyze_evidence_grading()
        self.detect_tables_and_figures()
        
    def analyze_sections(self):
        """Identify main sections and their organization."""
        print("\n=== Document Sections ===")
        sections = defaultdict(list)
        
        for page_num, page in enumerate(self.doc):
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line matches section patterns
                for pattern in self.section_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        sections[pattern].append((page_num + 1, line))
        
        print("\nDetected Sections:")
        for pattern, occurrences in sections.items():
            if occurrences:
                print(f"\nPattern '{pattern}':")
                for page, line in occurrences:
                    print(f"  Page {page}: {line[:100]}...")

    def analyze_recommendations(self):
        """Identify recommendation patterns and their format."""
        print("\n=== Recommendation Patterns ===")
        recommendations = defaultdict(list)
        
        for page_num, page in enumerate(self.doc):
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                for pattern in self.recommendation_patterns:
                    if re.search(pattern, line):
                        recommendations[pattern].append((page_num + 1, line))
        
        print("\nDetected Recommendation Formats:")
        for pattern, occurrences in recommendations.items():
            if occurrences:
                print(f"\nPattern '{pattern}':")
                # Show first occurrence as example
                page, line = occurrences[0]
                print(f"  Example (Page {page}): {line[:100]}...")
                print(f"  Total occurrences: {len(occurrences)}")

    def analyze_evidence_grading(self):
        """Identify evidence grading system used."""
        print("\n=== Evidence Grading System ===")
        evidence_levels = defaultdict(set)
        
        for page_num, page in enumerate(self.doc):
            text = page.get_text()
            
            for pattern in self.evidence_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    evidence_levels[pattern].add(match.group(1))
        
        print("\nDetected Evidence Grading:")
        for pattern, levels in evidence_levels.items():
            if levels:
                print(f"\nPattern '{pattern}':")
                print(f"  Levels found: {sorted(levels)}")

    def detect_tables_and_figures(self):
        """Analyze tables and figures in the document."""
        print("\n=== Tables and Figures ===")
        
        table_count = 0
        figure_count = 0
        
        for page_num, page in enumerate(self.doc):
            # Check for tables using layout analysis
            blocks = page.get_text("blocks")
            potential_tables = [b for b in blocks if len(b[4].split('\n')) > 2 and '\t' in b[4]]
            table_count += len(potential_tables)
            
            # Check for images
            images = page.get_images()
            figure_count += len(images)
        
        print(f"\nPotential Tables detected: {table_count}")
        print(f"Figures detected: {figure_count}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_pdf.py <path_to_pdf>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"Error: File {pdf_path} does not exist")
        sys.exit(1)
        
    analyzer = GuidelineAnalyzer(pdf_path)
    analyzer.analyze_structure()

if __name__ == "__main__":
    main()
