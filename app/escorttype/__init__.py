from flask import Blueprint

escorttype_bp = Blueprint('escorttype', __name__)

from app.escorttype import routes