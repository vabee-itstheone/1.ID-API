from flask import Blueprint, jsonify
from app.log.services import get_log_data

log_bp = Blueprint('log', __name__)

@log_bp.route('/log', methods=['GET'])
def log():
    data = get_log_data()
    return jsonify(data)