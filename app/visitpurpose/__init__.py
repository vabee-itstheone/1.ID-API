from flask import Blueprint

visitpurpose_bp = Blueprint('visitpurpose', __name__)

from app.visitpurpose import routes