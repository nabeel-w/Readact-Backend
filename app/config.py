import spacy
import os

class Config:
    DEBUG = False
    SECRET_KEY = 'your_secret_key'
    # Specify the path to your local spaCy model
    SPACY_MODEL_PATH = os.path.abspath(os.path.join(os.getcwd(), './model-best'))
    UPLOAD_PATH = os.path.abspath(os.path.join(os.getcwd(), './uploads'))
    SAVE_PATH = os.path.abspath(os.path.join(os.getcwd(), './results'))
    
    # Load the spaCy model from the local directory
    SPACY_MODEL = spacy.load(SPACY_MODEL_PATH)