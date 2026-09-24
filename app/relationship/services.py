from app.models import Relationship
from app import db

def get_relationship_data():
    try:
        # Query the Guest table
        relationships = Relationship.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': relationship.Id,
                'Relation': relationship.Relation,
                'DtcmCode': relationship.DtcmCode,
                
            }
            for relationship in relationships
        ]

        return result

    except Exception as e:
        return {"error": str(e)}