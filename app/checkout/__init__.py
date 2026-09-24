from flask import Blueprint

checkout_bp = Blueprint('checkout', __name__)

from app.checkout import routes