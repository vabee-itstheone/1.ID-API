from flask import Blueprint

checkin_bp = Blueprint('checkin', __name__)

from app.checkin import routes