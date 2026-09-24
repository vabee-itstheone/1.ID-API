from app.models import Room
from app import db
from app.utilities.table_query import fetch_rows


def get_room_data():
    # 59 rows and 3 ms - this endpoint was never the problem, and it stays the
    # one to call when all a client wants to know is which rooms are occupied.
    # ?occupied=1 / ?occupied=0 narrows it further.
    return fetch_rows(
        Room,
        lambda room: {
            'Id': room.Id,
            'RoomNumber': room.RoomNumber,
            'BedCount': room.BedCount,
            'IsChecked': room.IsChecked,
            'CheckinId': room.CheckinId,
            'IsWaitingRoom': room.IsWaitingRoom,
            'IsActive': room.IsActive,
        },
        filters={
            'occupied': Room.IsChecked,
            'room_number': Room.RoomNumber,
            'active': Room.IsActive,
        },
    )
