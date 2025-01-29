import os
from pathlib import Path
from analyze_pdf import GuidelineAnalyzer

def analyze_all_guidelines(directory_path: str):
    """Analyze all PDF files in the given directory."""
    pdf_files = [f for f in os.listdir(directory_path) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        print("\n" + "="*80)
        print(f"Analyzing: {pdf_file}")
        print("="*80)
        
        full_path = os.path.join(directory_path, pdf_file)
        try:
            analyzer = GuidelineAnalyzer(full_path)
            analyzer.analyze_structure()
        except Exception as e:
            print(f"Error analyzing {pdf_file}: {str(e)}")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    directory = "/Users/deboadebayo/Dev_Folder/github.com/debojadebayo/sec-insights copy/backend/example_guidelines"
    analyze_all_guidelines(directory)
