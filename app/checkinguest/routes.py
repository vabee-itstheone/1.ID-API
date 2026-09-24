from flask import Blueprint, jsonify
from app.checkinguest.services import get_checkinguest_data

checkinguest_bp = Blueprint('checkinguest', __name__)

@checkinguest_bp.route('/checkinguest', methods=['GET'])
def checkinguest():
    data = get_checkinguest_data()
    return jsonify(data)