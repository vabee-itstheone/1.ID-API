from app.models import CheckoutType
from app import db

def get_checkouttype_data():
    try:
        # Query the CheckinType table
        checkouttypes = CheckoutType.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': checkouttype.Id,
                'Type': checkouttype.Type,
            }
            for checkouttype in checkouttypes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}