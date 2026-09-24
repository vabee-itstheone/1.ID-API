from flask import Blueprint, jsonify
from app.dtcmaction.services import get_dtcmaction_data

dtcmaction_bp = Blueprint('dtcmaction', __name__)

@dtcmaction_bp.route('/dtcmaction', methods=['GET'])
def dtcmaction():
    data = get_dtcmaction_data()
    return jsonify(data)