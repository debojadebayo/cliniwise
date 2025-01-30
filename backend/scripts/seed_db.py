from typing import List
import asyncio
from tempfile import TemporaryDirectory
from pathlib import Path
from fire import Fire
import s3fs
from app.core.config import settings, AppEnvironment
import upsert_db_sec_documents
import download_sec_pdf
from download_sec_pdf import DEFAULT_CIKS, DEFAULT_FILING_TYPES
import seed_storage_context
import upsert_clinical_documents 


def copy_to_s3(dir_path: str, s3_bucket: str = settings.S3_ASSET_BUCKET_NAME):
    """
    Copy all files in dir_path to S3.
    """
    print(f"Initializing S3 connection to {settings.S3_ENDPOINT_URL}")
    s3 = s3fs.S3FileSystem(
        key=settings.AWS_KEY,
        secret=settings.AWS_SECRET,
        endpoint_url=settings.S3_ENDPOINT_URL,
    )

    print(f"Checking if bucket {s3_bucket} exists...")
    if not (settings.RENDER or s3.exists(s3_bucket)):
        print(f"Bucket {s3_bucket} does not exist, creating it...")
        s3.mkdir(s3_bucket)
    else:
        print(f"Bucket {s3_bucket} already exists")
        print("Current contents:")
        print(s3.ls(s3_bucket))

    print(f"Copying files from {dir_path} to s3://{s3_bucket}")
    s3.put(dir_path, s3_bucket, recursive=True)
    
    print("Files in bucket after upload:")
    print(s3.ls(s3_bucket))

async def async_seed_db(include_clinical: bool = True):
    with TemporaryDirectory() as temp_dir:
        if include_clinical:
            if settings.ENVIRONMENT == AppEnvironment.LOCAL:
                print("Using example clinical guidelines for local development")
                example_guidelines_dir = Path("example_guidelines")
                
                # Map filenames to metadata
                guideline_metadata = {
                    "Euro J of Neurology - 2021 - Quinn - European Stroke Organisation and European Academy of Neurology joint guidelines on.pdf": {
                        "title": "ESO-EAN Joint Guidelines on Post-Stroke Management",
                        "issuing_organization": "European Stroke Organisation and European Academy of Neurology",
                        "specialty": "Neurology",
                        "evidence_grading_system": "GRADE"
                    },
                    "NCPG - Antenatal Corticosteroids to Reduce Neonatal Morbidity and Mortality.pdf": {
                        "title": "Antenatal Corticosteroids Guidelines",
                        "issuing_organization": "NCPG",
                        "specialty": "Obstetrics",
                        "evidence_grading_system": "GRADE"
                    },
                    "decompensated-cirrhosis-English-report.pdf": {
                        "title": "Decompensated Cirrhosis Management Guidelines",
                        "issuing_organization": "British Society of Gastroenterology",
                        "specialty": "Gastroenterology",
                        "evidence_grading_system": "GRADE"
                    },
                    "ehae178.pdf": {
                        "title": "EASL Clinical Practice Guidelines",
                        "issuing_organization": "European Association for the Study of the Liver",
                        "specialty": "Hepatology",
                        "evidence_grading_system": "GRADE"
                    },
                    "joint-replacement-primary-hip-knee-and-shoulder-pdf-66141845322181.pdf": {
                        "title": "Joint Replacement Guidelines",
                        "issuing_organization": "NICE",
                        "specialty": "Orthopedics",
                        "evidence_grading_system": "GRADE"
                    }
                }
                
                # Create metadata list from existing files
                metadata_list = []
                for guideline_file in example_guidelines_dir.glob("*.pdf"):
                    if guideline_file.name in guideline_metadata:
                        metadata_list.append(guideline_metadata[guideline_file.name])
                
                print(f"Found {len(metadata_list)} example guidelines")
                
                # Copy example guidelines to temp directory to maintain same structure
                temp_guidelines_dir = Path(temp_dir) / "clinical-guidelines"
                temp_guidelines_dir.mkdir(exist_ok=True)
                for guideline_file in example_guidelines_dir.glob("*.pdf"):
                    if guideline_file.name != ".DS_Store":  # Skip macOS system files
                        import shutil
                        shutil.copy2(guideline_file, temp_guidelines_dir / guideline_file.name)
                
                print("Copying example clinical guidelines to LocalStack S3")
                copy_to_s3(str(temp_guidelines_dir), f"{settings.S3_ASSET_BUCKET_NAME}/clinical-guidelines")
                
                print("Upserting clinical guidelines into database")
                await upsert_clinical_documents.async_upsert_documents_from_guidelines(
                    url_base=settings.CDN_BASE_URL,
                    doc_dir=str(temp_guidelines_dir),
                    metadata_list=metadata_list
                )
                
                print("Seeding storage context with clinical guidelines")
                await seed_storage_context.async_main_seed_storage_context()
                
                print(
                    """
Done! 🏁
\t- Example clinical guidelines uploaded to LocalStack S3 ✅
\t- Documents database table has been populated ✅
\t- Vector storage table has been seeded with embeddings ✅
                    """.strip()
                )
            else:
                print("Listing clinical guidelines from S3")
                s3 = s3fs.S3FileSystem(
                    key=settings.AWS_KEY,
                    secret=settings.AWS_SECRET,
                    endpoint_url=settings.S3_ENDPOINT_URL,
                )
                
                # List clinical guidelines from S3
                s3_prefix = f"{settings.S3_ASSET_BUCKET_NAME}/clinical-guidelines/"
                guideline_files = [f for f in s3.ls(s3_prefix) if f.endswith('.pdf')]
                
                if not guideline_files:
                    print("No clinical guidelines found in S3. Please upload some guidelines first.")
                    return
                    
                print(f"Found {len(guideline_files)} clinical guidelines")
                
                # Create metadata list from filenames
                metadata_list = [{
                    "title": Path(f).stem,
                    "issuing_organization": "Your Organization",  # You might want to extract this from filename or S3 metadata
                    "publication_date": None,  # You might want to get this from S3 metadata
                    "specialty": None,  # You might want to extract this from filename or S3 metadata
                    "evidence_grading_system": None  # You might want to extract this from filename or S3 metadata
                } for f in guideline_files]
                
                print("Upserting clinical guidelines into database")
                await upsert_clinical_documents.async_upsert_documents_from_guidelines(
                    url_base=settings.CDN_BASE_URL,
                    doc_dir=s3_prefix,
                    metadata_list=metadata_list
                )
                
                print("Seeding storage context with clinical guidelines")
                await seed_storage_context.async_main_seed_storage_context()
                
                print(
                    """
Done! 🏁
\t- Found existing clinical guidelines in S3 assets bucket ✅
\t- Documents database table has been populated ✅
\t- Vector storage table has been seeded with embeddings ✅
                    """.strip()
                )
        else:
            print("Skipping clinical guidelines")


def seed_db(include_clinical: bool = True):
    asyncio.run(async_seed_db(include_clinical=include_clinical))

if __name__ == "__main__":
    Fire(seed_db)
