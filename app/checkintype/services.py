from app.models import CheckinType
from app import db

def get_checkintype_data():
    try:
        # Query the CheckinType table
        checkintypes = CheckinType.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': checkintype.Id,
                'Type': checkintype.Type,
            }
            for checkintype in checkintypes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}