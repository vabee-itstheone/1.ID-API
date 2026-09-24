from app.models import EscortType
from app import db

def get_escorttype_data():
    try:
        # Query the Country table
        escorttypes = EscortType.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': escorttype.Id,
                'Type': escorttype.Type,
                
            }
            for escorttype in escorttypes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}