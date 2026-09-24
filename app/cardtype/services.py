from app.models import CardType
from app import db

def get_cardtype_data():
    try:
        # Query the CardType table
        cardtypes = CardType.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': cardtype.Id,
                'Type': cardtype.Type,
                'MinLength': cardtype.MinLength,
                'MaxLength': cardtype.MaxLength,
                'DtcmCode': cardtype.DtcmCode,
            }
            for cardtype in cardtypes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}