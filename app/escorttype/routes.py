from flask import Blueprint, jsonify
from app.escorttype.services import get_escorttype_data

escorttype_bp = Blueprint('escorttype', __name__)

@escorttype_bp.route('/escorttype', methods=['GET'])
def escorttype():
    data = get_escorttype_data()
    return jsonify(data)