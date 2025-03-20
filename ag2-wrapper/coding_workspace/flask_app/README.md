# Flask Web Application

This is a standard Flask web application following best practices for project structure.

## Project Structure

flask_app/
│
├── app/                    # Application package
│   ├── __init__.py         # Initialize the app and bring together components
│   ├── models/             # Database models
│   ├── views/              # Routes and view functions
│   ├── forms/              # WTForms for data validation
│   └── utils/              # Utility functions and classes
│
├── static/                 # Static files
│   ├── css/                # CSS files
│   ├── js/                 # JavaScript files
│   └── img/                # Images
│
├── templates/              # Jinja2 templates
│   ├── base.html           # Base template with common structure
│   └── index.html          # Homepage template
│
├── instance/               # Instance-specific config (not in version control)
│
├── config.py               # Configuration settings
├── run.py                  # Application entry point
├── requirements.txt        # Project dependencies
├── .env.example            # Example environment variables
└── .gitignore              # Git ignore rules

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Copy .env.example to .env and configure environment variables
   cp .env.example .env

5. Run the application:
   python run.py
   
The application will be available at http://127.0.0.1:5000/

## Development

- Add models to app/models/
- Add routes to app/views/
- Add form classes to app/forms/
- Add templates to templates/
- Add static files to their respective folders in static/

## Testing

pytest

## Deployment

Configure gunicorn for production deployment:

gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
