from flask import Blueprint, jsonify
from app.mainguestchange.services import get_mainguestchange_data

mainguestchange_bp = Blueprint('mainguestchange', __name__)

@mainguestchange_bp.route('/mainguestchange', methods=['GET'])
def mainguestchange():
    data = get_mainguestchange_data()
    return jsonify(data)