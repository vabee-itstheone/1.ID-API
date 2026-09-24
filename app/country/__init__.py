from flask import Blueprint

checkin_bp = Blueprint('country', __name__)

from app.checkin import routes