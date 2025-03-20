from app import create_app, db
import os

app = create_app()

# CLI commands for development
@app.cli.command("init-db")
def init_db():
    """Create database tables."""
    db.create_all()
    print("Initialized the database.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
