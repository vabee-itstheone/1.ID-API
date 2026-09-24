from flask import Blueprint, jsonify
from app.room.services import get_room_data

room_bp = Blueprint('room', __name__)

@room_bp.route('/room', methods=['GET'])
def room():
    data = get_room_data()
    return jsonify(data)