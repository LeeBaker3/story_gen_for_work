\
import io
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

from .database import Story as StoryModel
from .logging_config import app_logger, error_logger

# Ensure the image paths are correct relative to the project root
# If backend/pdf_generator.py is calling this, and images are in /data/images
# then the path needs to be constructed carefully.
# Assuming image_path stored in DB is relative to project root e.g., "data/images/..."


def create_story_pdf(story_data: StoryModel) -> bytes:
    """
    Generates a PDF for the given story.
    story_data should be an ORM model instance of Story.
    """
    app_logger.info(
        f"Starting PDF generation for story: {story_data.title} (ID: {story_data.id})")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story_elements = []

    # Story Title
    story_elements.append(Paragraph(story_data.title, styles['h1']))
    story_elements.append(Spacer(1, 0.25*inch))

    # Sort pages by page number just in case they are not ordered
    sorted_pages = sorted(story_data.pages, key=lambda p: p.page_number)

    for page in sorted_pages:
        app_logger.debug(
            f"Processing page {page.page_number} for PDF of story {story_data.id}")
        # Page Text
        story_elements.append(
            Paragraph(f"Page {page.page_number}", styles['h3']))
        story_elements.append(Spacer(1, 0.1*inch))
        story_elements.append(Paragraph(page.text, styles['Normal']))
        story_elements.append(Spacer(1, 0.2*inch))

        # Page Image
        if page.image_path and os.path.exists(page.image_path):
            try:
                # Ensure image path is absolute or correctly relative for ImageReader
                # If page.image_path is like "data/images/...", it should be fine from project root.
                img = Image(page.image_path, width=6*inch,
                            height=4*inch)  # Adjust size as needed
                img.hAlign = 'CENTER'
                story_elements.append(img)
                app_logger.debug(
                    f"Added image {page.image_path} to PDF for page {page.page_number} of story {story_data.id}")
            except Exception as e:
                error_logger.error(
                    f"Could not add image {page.image_path} to PDF for story {story_data.id}, page {page.page_number}: {e}", exc_info=True)
                story_elements.append(Paragraph(
                    f"[Image not available: {os.path.basename(page.image_path)}]", styles['Italic']))
        else:
            app_logger.warning(
                f"Image path not found or missing for story {story_data.id}, page {page.page_number}: {page.image_path}")
            story_elements.append(
                Paragraph("[Image not available]", styles['Italic']))

        story_elements.append(Spacer(1, 0.25*inch))
        # Don't add page break after the last page
        if page.page_number < len(sorted_pages):
            story_elements.append(PageBreak())

    try:
        doc.build(story_elements)
        app_logger.info(
            f"Successfully built PDF for story: {story_data.title} (ID: {story_data.id})")
    except Exception as e:
        error_logger.error(
            f"Failed to build PDF document for story {story_data.id}: {e}", exc_info=True)
        raise  # Re-raise the exception to be caught by the endpoint

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# Example usage (for testing this file directly - requires a mock StoryModel object)
if __name__ == '__main__':
    # This is a mock setup for direct testing.
    # In the actual app, StoryModel will come from SQLAlchemy.
    class MockPage:
        def __init__(self, page_number, text, image_path):
            self.page_number = page_number
            self.text = text
            self.image_path = image_path

    class MockStory:
        def __init__(self, id, title, pages):
            self.id = id
            self.title = title
            self.pages = pages

    # Create a dummy image for testing if it doesn't exist
    # This test assumes it's run from the 'backend' directory.
    # For the actual app, image paths are relative to the workspace root.

    # Adjust path for test image creation
    test_image_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), "data", "images", "test")
    os.makedirs(test_image_dir, exist_ok=True)
    test_image_path = os.path.join(test_image_dir, "sample_test_image.png")

    if not os.path.exists(test_image_path):
        try:
            from PIL import Image as PILImage
            img = PILImage.new('RGB', (100, 100), color='red')
            img.save(test_image_path)
            print(f"Created dummy image at {test_image_path}")
        except ImportError:
            print(
                "Pillow not installed, cannot create dummy image for testing pdf_generator.py directly.")
            # Create an empty file as a placeholder if Pillow is not available
            open(test_image_path, 'a').close()
            print(f"Created empty placeholder file at {test_image_path}")
        except Exception as e:
            print(f"Error creating dummy image: {e}")

    mock_story_data = MockStory(
        id=1,
        title="The Adventures of Sir Reginald and Sparky",
        pages=[
            MockPage(
                1, "Once upon a time, Sir Reginald, a brave knight, met Sparky, a friendly dragon.", test_image_path),
            # Test missing image
            MockPage(
                2, "They decided to go on an adventure to find the legendary Golden Acorn.", None),
            MockPage(
                3, "After many trials, they found it and shared its magic with the kingdom!", test_image_path)
        ]
    )

    print(
        f"Attempting to generate PDF for mock story ID: {mock_story_data.id}...")
    try:
        pdf_output_path = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), "data", "test_story.pdf")
        pdf_bytes = create_story_pdf(mock_story_data)
        with open(pdf_output_path, 'wb') as f:
            f.write(pdf_bytes)
        print(
            f"Mock PDF generated successfully: {os.path.abspath(pdf_output_path)}")
    except Exception as e:
        print(f"Error during PDF generation test: {e}")
