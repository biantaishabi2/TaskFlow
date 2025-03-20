from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Homepage route"""
    return render_template('index.html', title='Home')

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('index.html', title='About')
