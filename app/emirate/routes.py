from flask import Blueprint, jsonify
from app.emirate.services import get_emirate_data

emirate_bp = Blueprint('emirate', __name__)

@emirate_bp.route('/emirate', methods=['GET'])
def emirate():
    data = get_emirate_data()
    return jsonify(data)