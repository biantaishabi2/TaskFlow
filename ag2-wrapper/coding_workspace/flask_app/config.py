import os
from datetime import timedelta

class Config:
    """Base configuration."""
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 
                                              'sqlite:///instance/app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # File uploads
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # In production, ensure SECRET_KEY is set in environment
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Configure production database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Security headers
    SECURITY_HEADERS = {
        'Content-Security-Policy': "default-src 'self'",
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
    }


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
