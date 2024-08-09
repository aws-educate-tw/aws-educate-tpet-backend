import logging
import os
from pathlib import Path

import fitz  # PyMuPDF
from s3 import read_file_from_s3, upload_file_to_s3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


BUCKET_NAME = os.getenv("BUCKET_NAME")
PRIVATE_BUCKET_NAME = os.getenv("PRIVATE_BUCKET_NAME")
CERTIFICATE_TEMPLATE_FILE_S3_OBJECT_KEY = (
    "templates/[template] AWS Educate certificate.pdf"
)
# Constants for certificate generation
FONT_SIZE_NAME = 32
FONT_SIZE_EVENT = 18
COORD_NAME = (365, 210)
COORD_EVENT = (250, 265)


def generate_certificate(
    run_id: str, participant_name: str, certificate_text: str
) -> str:

    def get_rect(coord: tuple[int, int], width: int, height: int) -> fitz.Rect:
        return fitz.Rect(coord[0], coord[1], coord[0] + width, coord[1] + height)

    def get_font(is_ascii: bool) -> fitz.Font:
        font_name = "AmazonEmber_Rg.ttf" if is_ascii else "NotoSansTC-Regular.ttf"
        return fitz.Font(fontfile=str(Path(__file__).parent / "fonts" / font_name))

    try:
        # Prepare file paths
        template_path = (
            Path("/tmp") / Path(CERTIFICATE_TEMPLATE_FILE_S3_OBJECT_KEY).name
        )
        output_path = (
            Path("/tmp")
            / f"{run_id}_{participant_name.replace(' ', '_')}_certificate.pdf"
        )

        # Check if the template already exists in /tmp, if not, download it
        if not template_path.exists():
            try:
                template_content = read_file_from_s3(
                    PRIVATE_BUCKET_NAME, CERTIFICATE_TEMPLATE_FILE_S3_OBJECT_KEY
                )
                template_path.write_bytes(template_content)
            except Exception as e:
                logger.error("Error reading template file from S3: %s", e)
                raise

        # Generate certificate
        try:
            with fitz.open(str(template_path)) as doc:
                page = doc[0]
                tw = fitz.TextWriter(page.rect)

                # Add participant name
                is_ascii = all(ord(char) < 128 for char in participant_name)
                tw.fill_textbox(
                    get_rect(COORD_NAME, 300, 300),
                    participant_name,
                    font=get_font(is_ascii),
                    fontsize=FONT_SIZE_NAME,
                    align=1,
                )

                # Add certificate text
                tw.fill_textbox(
                    get_rect(COORD_EVENT, 525, 350),
                    certificate_text,
                    font=get_font(True),
                    fontsize=FONT_SIZE_EVENT,
                    align=1,
                )

                tw.write_text(page)
                doc.subset_fonts()
                doc.save(str(output_path), deflate=True, garbage=3, clean=True)
        except Exception as e:
            logger.error("Error generating certificate: %s", e)
            raise

        # Upload and clean up
        try:
            certificate_s3_object_key = f"runs/{run_id}/certificates/{output_path.name}"
            upload_file_to_s3(str(output_path), BUCKET_NAME, certificate_s3_object_key)
        except Exception as e:
            logger.error("Error uploading file to S3: %s", e)
            raise

        logger.info(
            "Certificate generated and uploaded to S3: %s", certificate_s3_object_key
        )
        return str(output_path)
    except Exception as e:
        logger.error("Failed to generate certificate: %s", e)
        raise
