from flask import Blueprint, jsonify
from app.checkintype.services import get_checkintype_data

checkintype_bp = Blueprint('checkintype', __name__)

@checkintype_bp.route('/checkintype', methods=['GET'])
def checkintype():
    data = get_checkintype_data()
    return jsonify(data)