from app.models import Dtcmaction
from app import db

def get_dtcmaction_data():
    try:
        # Query the Dtcmaction table
        dtcmactions = Dtcmaction.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': dtcmaction.Id,
                'Name': dtcmaction.Name,
            }
            for dtcmaction in dtcmactions
        ]

        return result

    except Exception as e:
        return {"error": str(e)}