from flask import Blueprint, jsonify
from app.country.services import get_country_data

country_bp = Blueprint('country', __name__)

@country_bp.route('/country', methods=['GET'])
def country():
    data = get_country_data()
    return jsonify(data)