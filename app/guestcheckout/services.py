from app.models import CheckinGuest
from app import db
from app.utilities.table_query import fetch_rows


def get_guestcheckout_data():
    # Same table as /checkinguest; kept as its own endpoint because the
    # specification names it separately.
    return fetch_rows(
        CheckinGuest,
        lambda guestcheckout: {
            'Id': guestcheckout.Id,
            'CheckinDate': guestcheckout.CheckinDate.isoformat() if guestcheckout.CheckinDate else None,
            'IsMainGuest': guestcheckout.IsMainGuest,
            'GuestCode': guestcheckout.GuestCode,
            'GuestUID': guestcheckout.GuestUID,
            'CheckoutDate': guestcheckout.CheckoutDate.isoformat() if guestcheckout.CheckoutDate else None,
            'IsFirstGuest': guestcheckout.IsFirstGuest,
            'GuestId': guestcheckout.GuestId,
            'CheckinId': guestcheckout.CheckinId,
            'RelationshipName': guestcheckout.RelationshipName,
            'EscortTypeId': guestcheckout.EscortTypeId,
            'VisitPurposeId': guestcheckout.VisitPurposeId,
        },
        filters={
            'checkin_id': CheckinGuest.CheckinId,
            'guest_id': CheckinGuest.GuestId,
        },
    )
