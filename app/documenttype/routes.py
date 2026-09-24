from flask import Blueprint, jsonify
from app.documenttype.services import get_documenttype_data

documenttype_bp = Blueprint('documenttype', __name__)

@documenttype_bp.route('/documenttype', methods=['GET'])
def documenttype():
    data = get_documenttype_data()
    return jsonify(data)