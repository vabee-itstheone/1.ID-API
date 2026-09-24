from flask import Blueprint, jsonify
from app.relationship.services import get_relationship_data

relationship_bp = Blueprint('relationship', __name__)

@relationship_bp.route('/relationship', methods=['GET'])
def relationship():
    data = get_relationship_data()
    return jsonify(data)