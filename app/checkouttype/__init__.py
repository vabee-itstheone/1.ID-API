from flask import Blueprint

checkin_bp = Blueprint('checkouttype', __name__)

from app.checkout import routes