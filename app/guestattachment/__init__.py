from flask import Blueprint

guestattachment_bp = Blueprint('guestattachment', __name__)

from app.guestattachment import routes