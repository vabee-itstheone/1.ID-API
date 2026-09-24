from app.models import VisitPurpose
from app import db

def get_visitpurpose_data():
    try:
        # Query the Guest table
        visitpurposes = VisitPurpose.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': visitpurpose.Id,
                'Purpose': visitpurpose.Purpose,
                'CidCode': visitpurpose.CidCode,
                'DtcmCode': visitpurpose.DtcmCode,
                'DctCode': visitpurpose.DctCode,
                'PurposeType': visitpurpose.PurposeType,
            }
            for visitpurpose in visitpurposes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}