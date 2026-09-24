from flask import Blueprint

guestversion_bp = Blueprint('guestversion', __name__)

from app.guestversion import routes