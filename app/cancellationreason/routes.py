from flask import Blueprint, jsonify
from app.cancellationreason.services import get_cancellationreason_data

cancellationreason_bp = Blueprint('cancellationreason', __name__)

@cancellationreason_bp.route('/cancellationreason', methods=['GET'])
def cancellationreason():
    data = get_cancellationreason_data()
    return jsonify(data)