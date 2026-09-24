from app.models import Log
from app import db
from app.utilities.table_query import fetch_rows


def get_log_data():
    # The largest table in the database - 99,722 rows and 27 MB of JSON on a
    # year-old hotel - and the one that made a re-sync after check-out take
    # over a minute. Callers that only want what is new should send
    # ?since_id=, and callers after one stay's history ?checkin_id=.
    return fetch_rows(
        Log,
        lambda log: {
            'Id': log.Id,
            'AddedAt': log.AddedAt,
            'RoomNumber': log.RoomNumber,
            'RequestType': log.RequestType,
            'DtcmStatus': log.DtcmStatus,
            'CidStatus': log.CidStatus,
            'CheckinUID': log.CheckinUID,
            'PayloadIdentifier': log.PayloadIdentifier,
            'Error': log.Error,
            'CheckinGuestId': log.CheckinGuestId,
            'CheckinId': log.CheckinId,
        },
        filters={
            'checkin_id': Log.CheckinId,
            'room_number': Log.RoomNumber,
            'request_type': Log.RequestType,
        },
    )
