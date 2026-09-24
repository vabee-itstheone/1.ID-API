from app.models import RoomChange
from app import db
from app.utilities.table_query import fetch_rows


def get_roomchange_data():
    return fetch_rows(
        RoomChange,
        lambda roomchange: {
            'Id': roomchange.Id,
            'FromRoomNumber': roomchange.FromRoomNumber,
            'ToRoomNumber': roomchange.ToRoomNumber,
            'CheckinId': roomchange.CheckinId,
            'EffectiveDateTime': roomchange.EffectiveDateTime.isoformat() if roomchange.EffectiveDateTime else None,
            'AddedAt': roomchange.AddedAt.isoformat() if roomchange.AddedAt else None,
            'AddedFrom': roomchange.AddedFrom,
            'LogId': roomchange.LogId,
        },
        filters={
            'checkin_id': RoomChange.CheckinId,
        },
    )
