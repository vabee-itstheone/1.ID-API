from flask import Blueprint

roomchange_bp = Blueprint('roomchange', __name__)

from app.roomchange import routes