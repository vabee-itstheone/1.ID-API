from flask import Blueprint, jsonify
from app.cardtype.services import get_cardtype_data

cardtype_bp = Blueprint('cardtype', __name__)

@cardtype_bp.route('/cardtype', methods=['GET'])
def cardtype():
    data = get_cardtype_data()
    return jsonify(data)