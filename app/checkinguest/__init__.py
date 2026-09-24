from flask import Blueprint

checkin_bp = Blueprint('checkinguest', __name__)

from app.checkin import routes