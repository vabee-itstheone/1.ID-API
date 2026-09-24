from flask import Blueprint

relationship_bp = Blueprint('relationship', __name__)

from app.relationship import routes