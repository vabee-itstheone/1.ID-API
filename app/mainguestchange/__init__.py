from flask import Blueprint

mainguestchange_bp = Blueprint('mainguestchange', __name__)

from app.mainguestchange import routes