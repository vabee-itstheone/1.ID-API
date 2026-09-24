from app.models import CancellationReason
from app import db

def get_cancellationreason_data():
    try:
        # Query the CancellationReason table
        cancellationreasons = CancellationReason.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': cancellationreason.Id,
                'Reason': cancellationreason.Reason,
                'DtcmCode': cancellationreason.DtcmCode,
            }
            for cancellationreason in cancellationreasons
        ]

        return result

    except Exception as e:
        return {"error": str(e)}