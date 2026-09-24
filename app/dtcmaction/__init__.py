from flask import Blueprint

dtcmaction_bp = Blueprint('dtcmaction', __name__)

from app.checkin import routes