from flask import Blueprint

checkincancellation_bp = Blueprint('checkincancellation', __name__)

from app.checkincancellation import routes