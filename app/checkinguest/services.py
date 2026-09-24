from app.models import CheckinGuest
from app import db
from app.utilities.table_query import fetch_rows


def get_checkinguest_data():
    return fetch_rows(
        CheckinGuest,
        lambda checkinguest: {
            'Id': checkinguest.Id,
            'CheckinDate': checkinguest.CheckinDate.isoformat() if checkinguest.CheckinDate else None,
            'IsMainGuest': checkinguest.IsMainGuest,
            'GuestCode': checkinguest.GuestCode,
            'GuestUID': checkinguest.GuestUID,
            'CheckoutDate': checkinguest.CheckoutDate.isoformat() if checkinguest.CheckoutDate else None,
            'IsFirstGuest': checkinguest.IsFirstGuest,
            'GuestId': checkinguest.GuestId,
            'CheckinId': checkinguest.CheckinId,
            'RelationshipName': checkinguest.RelationshipName,
            'EscortTypeId': checkinguest.EscortTypeId,
            'VisitPurposeId': checkinguest.VisitPurposeId,
        },
        filters={
            'checkin_id': CheckinGuest.CheckinId,
            'guest_id': CheckinGuest.GuestId,
        },
    )
