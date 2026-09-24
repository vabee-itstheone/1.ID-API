from flask import Blueprint

guestcheckout_bp = Blueprint('guestcheckin', __name__)

from app.guestcheckout import routes