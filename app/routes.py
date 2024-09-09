from flask import Blueprint, current_app, jsonify, request, send_file, after_this_request
import datetime
import pypdf
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/analyze', methods=['POST'])
def analyze_text():

    uploaded_file = request.files['file']
    redaction_level= request.form.get('level')
    upload_path=current_app.config['UPLOAD_PATH']
    save_path=current_app.config['SAVE_PATH']
    if uploaded_file and allowed_file(uploaded_file.filename):
        destination = os.path.join(upload_path,uploaded_file.filename)
        uploaded_file.save(destination)
        if redaction_level in ['HIGH', 'MED', 'LOW']:
            redacted_text=redact_pdf_text(destination, current_app.config['SPACY_MODEL'], redaction_level)
        else:
            redacted_text=redact_pdf_text(destination, current_app.config['SPACY_MODEL'])
        save_file_name="[REDACTED]"+uploaded_file.filename
        save_file=os.path.join(save_path, save_file_name)
        create_pdf(redacted_text, save_file)
        @after_this_request
        def delete_files(response):
            try:
                os.remove(destination)
            except Exception as error:
                current_app.logger.error(f"Error deleting file: {error}")
            return response
            

        return send_file(save_file, as_attachment=True), 200

    else:
        return jsonify({'error':'File upload failed, or invalid file type'}), 406



def allowed_file(filename):
    ALLOWED_EXTS = ['pdf']
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS

def redact_pdf_text(pdf_path, spacy_model, redaction_level="HIGH"):
    # Load the spaCy model
    nlp = spacy_model
    redaction_levels = {
        "HIGH": [
            "B-EMAIL", "B-ID_NUM", "B-NAME_STUDENT", "B-PHONE_NUM",
            "B-STREET_ADDRESS", "B-URL_PERSONAL", "B-USERNAME",
            "I-NAME_STUDENT", "I-PHONE_NUM",
            "I-STREET_ADDRESS", "I-URL_PERSONAL"
        ],
        "MED": [
            "B-EMAIL", "B-NAME_STUDENT", "B-PHONE_NUM",
            "B-STREET_ADDRESS", "B-USERNAME",
            "I-NAME_STUDENT", "I-PHONE_NUM",
            "I-STREET_ADDRESS"
        ],
        "LOW": [
            "B-EMAIL", "B-NAME_STUDENT", "B-PHONE_NUM",
            "I-NAME_STUDENT", "I-PHONE_NUM"
        ]
    }


    # Initialize the PyPDF PDF reader
    with open(pdf_path, 'rb') as file:
        pdf_reader = pypdf.PdfReader(file)
        redacted_pages = []

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text(extraction_mode="layout")

            if text:
                # Process the text with spaCy
                doc = nlp(text)

                # Create a list of (start, end, entity_text) tuples
                entities_to_redact = []
                for ent in doc.ents:
                    if ent.label_ in redaction_levels[redaction_level]:
                        entities_to_redact.append((ent.start_char, ent.end_char, ent.text))

                # Sort entities by start position in reverse to avoid issues with overlapping redactions
                entities_to_redact.sort(key=lambda x: x[0], reverse=True)

                # Redact text
                redacted_text = text
                for start, end, text in entities_to_redact:
                    redacted_text = redacted_text[:start] + "[REDACTED]" + redacted_text[end:]

                redacted_pages.append(redacted_text)
            else:
                redacted_pages.append("No text found on this page.")

    return redacted_pages

def wrap_text(text, font, font_size, max_width, canvas):
    """Wrap text to fit within max_width"""
    lines = []
    words = text.split(' ')
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        text_width = canvas.stringWidth(test_line, font, font_size)
        if text_width < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def create_pdf(texts, pdf_path):
    # Create a PDF file
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    margin = 40
    max_width = width - 2 * margin  # Maximum width for the text

    # Set font and size
    c.setFont("Times-Roman", 12)

    y_position = height - margin  # Start position (top of the page)

    for text in texts:
        # Split the text by newline characters
        paragraphs = text.split('\n')

        y_position -= 14

        for paragraph in paragraphs:
            # Wrap text
            wrapped_lines = wrap_text(paragraph, "Times-Roman", 12, max_width, c)

            for line in wrapped_lines:
                # Add wrapped line to PDF
                c.drawString(margin, y_position, line)
                y_position -= 14  # Move down for the next line

                # Check if we need to create a new page
                if y_position < margin:
                    c.showPage()
                    c.setFont("Times-Roman", 12)
                    y_position = height - margin
                

    # Save the PDF file
    c.save()

def extract_text_entities(pdf_path, spacy_model, redaction_level="HIGH"):
    nlp = spacy_model
    redaction_levels = {
        "HIGH": [
            "B-EMAIL", "B-ID_NUM", "B-NAME_STUDENT", "B-PHONE_NUM",
            "B-STREET_ADDRESS", "B-URL_PERSONAL", "B-USERNAME",
            "I-NAME_STUDENT", "I-PHONE_NUM",
            "I-STREET_ADDRESS", "I-URL_PERSONAL"
        ],
        "MED": [
            "B-EMAIL", "B-NAME_STUDENT", "B-PHONE_NUM",
            "B-STREET_ADDRESS", "B-USERNAME",
            "I-NAME_STUDENT", "I-PHONE_NUM",
            "I-STREET_ADDRESS"
        ],
        "LOW": [
            "B-EMAIL", "B-NAME_STUDENT", "B-PHONE_NUM",
            "I-NAME_STUDENT", "I-PHONE_NUM"
        ]
    }

    with open(pdf_path, 'rb') as file:
        pdf_reader = pypdf.PdfReader(file)
        pages = []

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text(extraction_mode="layout")

            if text:
                # Process the text with spaCy
                doc = nlp(text)

                # Create a list of (start, end, entity_text) tuples
                entities_to_redact = []
                for ent in doc.ents:
                    if ent.label_ in redaction_levels[redaction_level]:
                        entities_to_redact.append((ent.start_char, ent.end_char, ent.text))

                # Sort entities by start position in reverse to avoid issues with overlapping redactions
                entities_to_redact.sort(key=lambda x: x[0], reverse=True)
                pages.append((text, entities_to_redact))
    
        return pages

def redact_text(pages):
    redacted_pages = []
    for page_text, entities_to_redact in pages:
        redacted_text=page_text
        for start, end, text in entities_to_redact:
            redact_string="X"*len(text)
            redacted_text = redacted_text[:start] + redact_string + redacted_text[end:]
        
        redacted_pages.append(redacted_text)
    
    return redacted_pages

@main_bp.route('/v2/analyze', methods=['POST'])
def v2_analyze_test():
    uploaded_file = request.files['file']
    redaction_level= request.form.get('level')
    upload_path=current_app.config['UPLOAD_PATH']
    save_path=current_app.config['SAVE_PATH']
    if uploaded_file and allowed_file(uploaded_file.filename):
        destination = os.path.join(upload_path,uploaded_file.filename)
        uploaded_file.save(destination)

        @after_this_request
        def delete_files(response):
            try:
                os.remove(destination)
            except Exception as error:
                current_app.logger.error(f"Error deleting file: {error}")
            return response

        if redaction_level in ['HIGH', 'MED', 'LOW']:
            pages=extract_text_entities(destination, current_app.config['SPACY_MODEL'], redaction_level)
            return jsonify(pages), 200
        else:
            return jsonify({"error":"Invalid Redaction Level Input"}), 400
    else:
        return jsonify({"error": "Invalid file or no file uploaded"}), 400

@main_bp.route('/v2/redact', methods=['POST'])
def v2_redact_text():
    pages_with_entities=json.loads(request.form.get('pages'))
    save_path=current_app.config['SAVE_PATH']
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    prefix="[REDACTED]"
    extension="pdf"
    file_name=f"{prefix}_{timestamp}.{extension}"
    redacted_text=redact_text(pages_with_entities)
    save_file=os.path.join(save_path, file_name)
    create_pdf(redacted_text, save_file)
    
    return send_file(save_file, as_attachment=True, download_name=file_name, mimetype='application/octet-stream'), 200


