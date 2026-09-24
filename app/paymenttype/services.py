from app.models import PaymentType
from app import db

def get_paymenttype_data():
    try:
        # Query the Guest table
        paymenttypes = PaymentType.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': paymenttype.Id,
                'Type': paymenttype.Type,
                'DtcmCode': paymenttype.DtcmCode,

            }
            for paymenttype in paymenttypes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}