from flask import Blueprint

changes_bp = Blueprint('changes', __name__)

from app.changes import routes
