from flask import Blueprint, jsonify
from app.guestdocumentimage.services import get_guestdocumentimage_data

guestdocumentimage_bp = Blueprint('guestdocumentimage', __name__)

@guestdocumentimage_bp.route('/guestdocumentimage', methods=['GET'])
def guestdocumentimage():
    data = get_guestdocumentimage_data()
    return jsonify(data)