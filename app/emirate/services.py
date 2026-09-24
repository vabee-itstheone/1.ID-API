from app.models import Emirate
from app import db

def get_emirate_data():
    try:
        # Query the Country table
        emirates = Emirate.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': emirate.Id,
                'Name': emirate.Name,
                'DtcmCode': emirate.DtcmCode,
                
            }
            for emirate in emirates
        ]

        return result

    except Exception as e:
        return {"error": str(e)}