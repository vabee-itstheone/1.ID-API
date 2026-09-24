from app.models import GuestAttachment
from app import db
from app.utilities.table_query import fetch_rows


def get_guestattachment_data():
    return fetch_rows(
        GuestAttachment,
        lambda guestattachment: {
            'Id': guestattachment.Id,
            'ExpiryDate': guestattachment.ExpiryDate.isoformat() if guestattachment.ExpiryDate else None,
            'IssueDate': guestattachment.IssueDate.isoformat() if guestattachment.IssueDate else None,
            'AttachmentInfoListJson': guestattachment.AttachmentInfoListJson,
            'DocumentTypeId': guestattachment.DocumentTypeId,
            'IssueCountryId': guestattachment.IssueCountryId,
            'GuestId': guestattachment.GuestId,
        },
        filters={
            'guest_id': GuestAttachment.GuestId,
        },
    )
