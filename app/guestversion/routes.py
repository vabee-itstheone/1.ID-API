from flask import Blueprint, jsonify
from app.guestversion.services import get_guestversion_data

guestversion_bp = Blueprint('guestversion', __name__)

@guestversion_bp.route('/guestversion', methods=['GET'])
def guestversion():
    data = get_guestversion_data()
    return jsonify(data)