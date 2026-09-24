from flask import Blueprint

checkin_bp = Blueprint('cancellationreason', __name__)

from app.checkin import routes