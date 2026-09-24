from flask import Blueprint

room_bp = Blueprint('room', __name__)

from app.room import routes