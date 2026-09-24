from flask import Blueprint

log_bp = Blueprint('log', __name__)

from app.log import routes