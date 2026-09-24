from flask import Blueprint, jsonify
from app.visitpurpose.services import get_visitpurpose_data

visitpurpose_bp = Blueprint('visitpurpose', __name__)

@visitpurpose_bp.route('/visitpurpose', methods=['GET'])
def visitpurpose():
    data = get_visitpurpose_data()
    return jsonify(data)