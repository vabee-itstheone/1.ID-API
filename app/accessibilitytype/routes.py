from flask import Blueprint, jsonify
from app.accessibilitytype.services import get_accessibilitytype_data

accessibilitytype_bp = Blueprint('accessibilitytype', __name__)

@accessibilitytype_bp.route('/accessibilitytype', methods=['GET'])
def accessibilitytype():
    data = get_accessibilitytype_data()
    return jsonify(data)