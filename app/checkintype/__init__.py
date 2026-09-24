from flask import Blueprint

checkin_bp = Blueprint('checkintype', __name__)

from app.checkintype import routes