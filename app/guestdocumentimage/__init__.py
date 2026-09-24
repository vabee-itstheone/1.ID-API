from flask import Blueprint

visitpurpose_bp = Blueprint('guestdocumentimage', __name__)

from app.guestdocumentimage import routes