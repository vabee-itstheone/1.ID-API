from flask import Blueprint

paymenttype_bp = Blueprint('paymenttype', __name__)

from app.paymenttype import routes