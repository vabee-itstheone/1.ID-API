from app.models import DocumentType
from app import db

def get_documenttype_data():
    try:
        # Query the Country table
        documenttypes = DocumentType.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': documenttype.Id,
                'Type': documenttype.Type,
                'DtcmCode': documenttype.DtcmCode,
                
            }
            for documenttype in documenttypes
        ]

        return result

    except Exception as e:
        return {"error": str(e)}