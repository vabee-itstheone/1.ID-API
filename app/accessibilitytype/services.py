from app.models import AccessibilityType
from app import db

def get_accessibilitytype_data():
    try:
        # Query the AccessibilityType table
        accessibilitytypes = AccessibilityType.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': accessibilitytype.Id,
                'EnglishName': accessibilitytype.EnglishName,
                'ArabicName': accessibilitytype.ArabicName,
                'DtcmCode': accessibilitytype.DtcmCode,
            }
            for accessibilitytype in accessibilitytypes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}