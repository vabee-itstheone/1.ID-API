from flask import Blueprint, jsonify
from app.payment.services import get_payment_data

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payment', methods=['GET'])
def payment():
    data = get_payment_data()
    return jsonify(data)