\
import io
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from .database import Story as StoryModel
from .logging_config import app_logger, error_logger

# Helper function for page footer


def _page_footer(canvas, doc):
    app_logger.info(
        f"PDFGEN_FOOTER: _page_footer called for doc.page: {doc.page}, physical page: {canvas.getPageNumber()}")
    canvas.saveState()
    try:
        line_y = 0.75 * inch
        # canvas.line(doc.leftMargin, line_y, # Keep debug line commented out for now
        #             doc.pagesize[0] - doc.rightMargin, line_y)
    except Exception as e:
        pass
    style = ParagraphStyle(name='FooterStyle',
                           parent=getSampleStyleSheet()['Normal'],
                           alignment=1,  # TA_CENTER
                           textColor='black',
                           fontSize=10)
    # Adjust page number display and remove DEBUG prefix
    # Changed from doc.page to doc.page - 1 and removed DEBUG:
    page_num_text = f"Page {doc.page - 1}"
    p = Paragraph(page_num_text, style)
    available_width_for_text = doc.width
    p_width, p_height = p.wrapOn(
        canvas, available_width_for_text, doc.bottomMargin)
    x_coord = doc.leftMargin + (available_width_for_text - p_width) / 2.0
    y_coord = 0.5 * inch
    p.drawOn(canvas, x_coord, y_coord)
    canvas.restoreState()

# Page event handlers


def _on_first_page_handler(canvas, doc):
    # app_logger.info(f"PDFGEN_HANDLER: onFirstPage called for doc.page: {doc.page}, physical page: {canvas.getPageNumber()}")
    # No footer on the first page (cover page)
    pass


def _on_later_pages_handler(canvas, doc):
    # app_logger.info(f"PDFGEN_HANDLER: onLaterPages called for doc.page: {doc.page}, physical page: {canvas.getPageNumber()}")
    _page_footer(canvas, doc)


def create_story_pdf(story_data: StoryModel) -> bytes:
    app_logger.info(
        f"Starting PDF generation for story: {story_data.title} (ID: {story_data.id})")

    buffer = io.BytesIO()
    # Restore original SimpleDocTemplate constructor, without onFirstPage/onLaterPages here
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=1.0*inch)
    styles = getSampleStyleSheet()

    # Assign handlers directly to the doc instance
    doc.onFirstPage = _on_first_page_handler
    doc.onLaterPages = _on_later_pages_handler

    # Remove the minimal handler test block that was here.
    # Restore original story_elements population
    story_elements = []

    # Story Title - Main H1, Centered
    centered_h1_style = ParagraphStyle(
        name='CenteredH1', parent=styles['h1'], alignment=1)  # 1 for TA_CENTER
    story_elements.append(Paragraph(story_data.title, centered_h1_style))
    story_elements.append(Spacer(1, 0.25*inch))

    sorted_pages = sorted(story_data.pages, key=lambda p: p.page_number)

    if sorted_pages:
        cover_page_data = sorted_pages[0]
        app_logger.debug(
            f"Processing cover page elements (DB page_number {cover_page_data.page_number}) for PDF of story {story_data.id}")
        if cover_page_data.image_path:
            PROJECT_ROOT = os.path.abspath(os.path.join(
                os.path.dirname(__file__), os.pardir))
            full_image_path = os.path.join(
                PROJECT_ROOT, "data", cover_page_data.image_path)
            app_logger.debug(
                f"PDF Gen: Attempting to access cover image at: {full_image_path}")
            if os.path.exists(full_image_path):
                try:
                    img = Image(full_image_path, width=6*inch, height=4*inch)
                    img.hAlign = 'CENTER'
                    story_elements.append(img)
                    story_elements.append(Spacer(1, 0.25*inch))
                    app_logger.debug(
                        f"Added cover image {full_image_path} to PDF for story {story_data.id}")
                except Exception as e:
                    error_logger.error(
                        f"Could not add cover image {full_image_path} to PDF for story {story_data.id}: {e}", exc_info=True)
                    story_elements.append(Paragraph(
                        f"[Cover image not available: {os.path.basename(cover_page_data.image_path)}]", styles['Italic']))
            else:
                app_logger.warning(
                    f"Cover image file not found at: {full_image_path} (DB path: {cover_page_data.image_path}) for story {story_data.id}")
                story_elements.append(Paragraph(
                    "[Cover image not available]", styles['Italic']))
        else:
            app_logger.info(
                f"No image path specified for cover page (DB page_number {cover_page_data.page_number}) of story {story_data.id}. Skipping cover image.")

        if len(sorted_pages) > 1:
            story_elements.append(PageBreak())

    for page_idx, content_page_data in enumerate(sorted_pages[1:], start=1):
        app_logger.debug(
            f"Processing content page (DB page_number {content_page_data.page_number}) for PDF of story {story_data.id}")
        story_elements.append(
            Paragraph(content_page_data.text, styles['Normal']))
        story_elements.append(Spacer(1, 0.2*inch))
        if content_page_data.image_path:
            PROJECT_ROOT = os.path.abspath(os.path.join(
                os.path.dirname(__file__), os.pardir))
            full_image_path = os.path.join(
                PROJECT_ROOT, "data", content_page_data.image_path)
            app_logger.debug(
                f"PDF Gen: Attempting to access content image at: {full_image_path}")
            if os.path.exists(full_image_path):
                try:
                    img = Image(full_image_path, width=6*inch, height=4*inch)
                    img.hAlign = 'CENTER'
                    story_elements.append(img)
                    app_logger.debug(
                        f"Added image {full_image_path} to PDF for page {content_page_data.page_number} of story {story_data.id}")
                except Exception as e:
                    error_logger.error(
                        f"Could not add image {full_image_path} to PDF for story {story_data.id}, page {content_page_data.page_number}: {e}", exc_info=True)
                    story_elements.append(Paragraph(
                        f"[Image not available: {os.path.basename(content_page_data.image_path)}]", styles['Italic']))
            else:
                app_logger.warning(
                    f"Image file not found at: {full_image_path} (DB path: {content_page_data.image_path}) for story {story_data.id}, page {content_page_data.page_number}")
                story_elements.append(
                    Paragraph("[Image not available]", styles['Italic']))
        else:
            app_logger.info(
                f"No image path specified for story {story_data.id}, page {content_page_data.page_number}. Skipping image in PDF.")
        story_elements.append(Spacer(1, 0.25*inch))
        if page_idx < len(sorted_pages[1:]):
            story_elements.append(PageBreak())

    app_logger.info(
        f"PDF Gen: Story ID {story_data.id} - Total sorted pages for PDF: {len(sorted_pages)}")
    for i, p in enumerate(sorted_pages):
        app_logger.info(
            f"PDF Gen: Story ID {story_data.id} - Sorted Page {i}: DB page_number={p.page_number}, Text length={len(p.text) if p.text else 0}, Image path={p.image_path}")

    # Restore original doc.build call with full story_elements
    try:
        doc.build(story_elements)
        app_logger.info(
            f"Successfully built PDF for story: {story_data.title} (ID: {story_data.id})")
    except Exception as e:
        error_logger.error(
            f"Failed to build PDF document for story {story_data.id}: {e}", exc_info=True)
        raise

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
