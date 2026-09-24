from flask import Blueprint

checkin_bp = Blueprint('emirate', __name__)

from app.checkin import routes