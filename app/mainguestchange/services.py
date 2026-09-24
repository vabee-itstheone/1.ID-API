from app.models import MainGuestChange
from app import db
from app.utilities.table_query import fetch_rows


def get_mainguestchange_data():
    # EffectiveDateTime, AddedAt: handed over as datetimes on purpose - jsonify
    # renders them as HTTP dates, which is what callers already parse.
    return fetch_rows(
        MainGuestChange,
        lambda mainguestchange: {
            'Id': mainguestchange.Id,
            'FormerMainCheckinGuestId': mainguestchange.FormerMainCheckinGuestId,
            'NewMainCheckinGuestId': mainguestchange.NewMainCheckinGuestId,
            'CheckinId': mainguestchange.CheckinId,
            'EffectiveDateTime': mainguestchange.EffectiveDateTime,
            'AddedAt': mainguestchange.AddedAt,
            'AddedFrom': mainguestchange.AddedFrom,
            'LogId': mainguestchange.LogId,
        },
        filters={
            'checkin_id': MainGuestChange.CheckinId,
        },
    )
