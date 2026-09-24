from flask import Blueprint

checkin_bp = Blueprint('accessibilitytype', __name__)

from app.checkin import routes