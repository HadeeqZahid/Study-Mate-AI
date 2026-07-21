import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Secret key for session management and security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-studymate-2026'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///studymate_v2.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = 'app/static/uploads'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'ppt', 'pptx'}
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')