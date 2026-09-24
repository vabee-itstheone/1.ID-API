from flask import Blueprint, jsonify
from app.paymenttype.services import get_paymenttype_data

paymenttype_bp = Blueprint('paymenttype', __name__)

@paymenttype_bp.route('/paymenttype', methods=['GET'])
def paymenttype():
    data = get_paymenttype_data()
    return jsonify(data)