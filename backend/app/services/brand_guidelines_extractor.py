"""Brand Guidelines Extractor Service - Parse brand guidelines documents.

This service downloads, parses, and extracts structured information from brand
guidelines documents (PDF, DOCX, TXT) using LLM analysis.

Task 5: New service to actually use the guidelines_url field.
"""

import logging
import tempfile
import json
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Dict, Optional, List
from app.services.llm_client import get_llm_client, BaseLLMClient
from app.config import settings

logger = logging.getLogger(__name__)


class ExtractedGuidelines:
    """Extracted brand guidelines data."""
    
    def __init__(
        self,
        color_palette: List[str],
        tone_of_voice: str,
        font_family: Optional[str],
        dos_and_donts: Dict[str, List[str]],
        raw_text: str
    ):
        self.color_palette = color_palette
        self.tone_of_voice = tone_of_voice
        self.font_family = font_family
        self.dos_and_donts = dos_and_donts
        self.raw_text = raw_text
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "color_palette": self.color_palette,
            "tone_of_voice": self.tone_of_voice,
            "font_family": self.font_family,
            "dos_and_donts": self.dos_and_donts,
            "raw_text_preview": self.raw_text[:500] if self.raw_text else None,  # Truncate for storage
        }


class BrandGuidelineExtractor:
    """Extract brand guidelines from documents (PDF, DOCX, TXT)."""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        s3_bucket_name: Optional[str] = None,
        aws_region: str = "us-east-1",
    ):
        """Initialize with LLM client and S3 credentials.

        Args:
            llm_client: LLM client instance. If not provided, creates one based on settings.
            aws_access_key_id: AWS access key. Uses settings if not provided.
            aws_secret_access_key: AWS secret key. Uses settings if not provided.
            s3_bucket_name: S3 bucket name. Uses settings if not provided.
            aws_region: AWS region. Defaults to us-east-1.
        """
        self.llm_client = llm_client or get_llm_client(
            provider=settings.llm_provider,
            api_key=settings.openai_api_key,
            region=settings.aws_region
        )
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id or settings.aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key or settings.aws_secret_access_key,
            region_name=aws_region,
        )
        self.s3_bucket_name = s3_bucket_name or settings.s3_bucket_name
        self.aws_region = aws_region
        logger.info(f"BrandGuidelineExtractor initialized (LLM: {settings.llm_provider})")
    
    async def extract_guidelines(
        self,
        guidelines_url: str,
        brand_name: str
    ) -> Optional[ExtractedGuidelines]:
        """
        Extract brand guidelines from document URL.
        
        Task 5: Download guidelines document, parse to text, extract structured data.
        
        Args:
            guidelines_url: S3 URL of guidelines document
            brand_name: Brand name for context
            
        Returns:
            ExtractedGuidelines or None if extraction fails (non-critical)
        """
        try:
            logger.info(f"📄 Extracting brand guidelines for {brand_name} from: {guidelines_url}")
            
            # Step 1: Download and parse document to text
            text_content = await self._download_and_parse(guidelines_url)
            
            if not text_content or len(text_content) < 50:
                logger.warning("Guidelines document too short or empty, skipping")
                return None
            
            logger.info(f"✅ Parsed {len(text_content)} characters from guidelines document")
            
            # Step 2: Extract structured data using LLM
            extracted = await self._extract_with_llm(text_content, brand_name)
            
            logger.info(
                f"✅ Extracted guidelines: {len(extracted.color_palette)} colors, "
                f"tone='{extracted.tone_of_voice}'"
            )
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting guidelines: {e}")
            logger.warning("Continuing pipeline without brand guidelines")
            return None
    
    async def _download_and_parse(self, url: str) -> Optional[str]:
        """Download and parse document to text."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Download file from S3
                file_path = Path(tmpdir) / "guidelines"
                await self._download_file(url, file_path)
                
                # Detect file type and parse accordingly
                file_type = self._detect_file_type(file_path)
                logger.info(f"Detected file type: {file_type}")
                
                if file_type == "txt":
                    return file_path.read_text(encoding='utf-8', errors='ignore')
                elif file_type == "pdf":
                    return await self._parse_pdf(file_path)
                elif file_type == "docx":
                    return await self._parse_docx(file_path)
                else:
                    logger.warning(f"Unsupported file type: {file_type}, treating as text")
                    return file_path.read_text(encoding='utf-8', errors='ignore')
                    
        except Exception as e:
            logger.error(f"Error downloading/parsing document: {e}")
            return None
    
    async def _download_file(self, url: str, output_path: Path):
        """Download file from S3."""
        from app.utils.s3_utils import parse_s3_url

        # Parse S3 URL to get bucket and key
        bucket_name, s3_key = parse_s3_url(url)

        logger.info(f"Downloading S3 object: s3://{bucket_name}/{s3_key}")

        try:
            # Download from S3
            self.s3_client.download_file(
                bucket_name,
                s3_key,
                str(output_path)
            )
            logger.info(f"✅ Downloaded guidelines from S3: {s3_key} → {output_path}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code in ('403', 'AccessDenied'):
                logger.warning(
                    f"⚠️ Brand guidelines PDF access denied (403) - skipped. "
                    f"Bucket: {bucket_name}, Key: {s3_key}, Error: {error_message}"
                )
            else:
                logger.error(
                    f"S3 ClientError downloading guidelines: {error_code} - {error_message}. "
                    f"Bucket: {bucket_name}, Key: {s3_key}"
                )
            raise

        except Exception as e:
            logger.error(f"Error downloading file from S3: {e}")
            raise
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type from magic bytes."""
        try:
            with open(file_path, "rb") as f:
                header = f.read(10)
            
            if header.startswith(b"%PDF"):
                return "pdf"
            elif header.startswith(b"PK\x03\x04"):  # ZIP format (DOCX is zipped XML)
                return "docx"
            else:
                return "txt"
        except Exception as e:
            logger.warning(f"Error detecting file type: {e}, defaulting to txt")
            return "txt"
    
    async def _parse_pdf(self, file_path: Path) -> str:
        """Parse PDF to text using PyPDF2."""
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(str(file_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            logger.info(f"Extracted {len(text)} characters from PDF ({len(reader.pages)} pages)")
            return text
            
        except ImportError:
            logger.warning("PyPDF2 not installed, treating PDF as plain text (may fail)")
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}, falling back to plain text")
            return file_path.read_text(encoding='utf-8', errors='ignore')
    
    async def _parse_docx(self, file_path: Path) -> str:
        """Parse DOCX to text using python-docx."""
        try:
            from docx import Document
            
            doc = Document(str(file_path))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            logger.info(f"Extracted {len(text)} characters from DOCX")
            return text
            
        except ImportError:
            logger.warning("python-docx not installed, treating DOCX as plain text (may fail)")
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}, falling back to plain text")
            return file_path.read_text(encoding='utf-8', errors='ignore')
    
    async def _extract_with_llm(
        self,
        text_content: str,
        brand_name: str
    ) -> ExtractedGuidelines:
        """Extract structured data from guidelines text using LLM."""
        
        # Truncate if too long (GPT-4o-mini context limit ~128k tokens, use 10k chars ~2500 tokens)
        if len(text_content) > 10000:
            logger.warning(f"Guidelines too long ({len(text_content)} chars), truncating to 10000")
            text_content = text_content[:10000] + "\n\n[Document truncated...]"
        
        prompt = f"""You are analyzing brand guidelines for {brand_name}.

Extract the following information from the guidelines document:

1. **Color Palette**: Extract ALL hex color codes (e.g., #FF6B9D, #2C3E50)
2. **Tone of Voice**: How the brand communicates (2-4 word descriptor, e.g., "professional and friendly")
3. **Font Family**: Primary font name if mentioned (e.g., "Helvetica Neue")
4. **Do's and Don'ts**: Key rules about brand usage

Guidelines Document:
```
{text_content}
```

Return ONLY valid JSON (no markdown, no explanation):
{{
  "color_palette": ["#RRGGBB", "#RRGGBB"],
  "tone_of_voice": "descriptive tone",
  "font_family": "Font Name" or null,
  "dos": ["Do use...", "Do maintain..."],
  "donts": ["Don't use...", "Don't mix..."]
}}

If information is not found, use empty arrays or null."""

        try:
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=800,
            )

            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            data = json.loads(response_text)
            
            # Create ExtractedGuidelines object
            extracted = ExtractedGuidelines(
                color_palette=data.get("color_palette", []),
                tone_of_voice=data.get("tone_of_voice", "professional"),
                font_family=data.get("font_family"),
                dos_and_donts={
                    "dos": data.get("dos", []),
                    "donts": data.get("donts", []),
                },
                raw_text=text_content
            )
            
            return extracted
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Response was: {response_text[:200]}")
            # Return empty guidelines on parse failure
            return ExtractedGuidelines(
                color_palette=[],
                tone_of_voice="professional",
                font_family=None,
                dos_and_donts={"dos": [], "donts": []},
                raw_text=text_content
            )
        except Exception as e:
            logger.error(f"Error extracting with LLM: {e}")
            # Return empty guidelines on any failure
            return ExtractedGuidelines(
                color_palette=[],
                tone_of_voice="professional",
                font_family=None,
                dos_and_donts={"dos": [], "donts": []},
                raw_text=text_content
            )

