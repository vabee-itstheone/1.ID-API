from flask import Blueprint, jsonify
from app.checkouttype.services import get_checkouttype_data

checkouttype_bp = Blueprint('checkouttype', __name__)

@checkouttype_bp.route('/checkouttype', methods=['GET'])
def checkouttype():
    data = get_checkouttype_data()
    return jsonify(data)