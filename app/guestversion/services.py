from app.models import GuestVersion
from app import db
from app.utilities.table_query import fetch_rows


def get_guestversion_data():
    # 59,331 rows. This table's primary key is composite, so LogId is the
    # column ?since_id= and ?order= work on - it is the one that only ever
    # increases.
    return fetch_rows(
        GuestVersion,
        lambda guestversion: {
            'FirstName': guestversion.FirstName,
            'LastName': guestversion.LastName,
            'ArabicFirstName': guestversion.ArabicFirstName,
            'ArabicLastName': guestversion.ArabicLastName,
            'Gender': guestversion.Gender,
            'BirthDate': guestversion.BirthDate,
            'ResidenceCountryPhone': guestversion.ResidenceCountryPhone,
            'MobileCode': guestversion.MobileCode,
            'MobileNumber': guestversion.MobileNumber,
            'Email': guestversion.Email,
            'RequiresAccessibilityJson': guestversion.RequiresAccessibilityJson,
            'CheckinId': guestversion.CheckinId,
            'DocumentNumber': guestversion.DocumentNumber,
            'NationalityId': guestversion.NationalityId,
            'EmirateId': guestversion.EmirateId,
            'CheckinDate': guestversion.CheckinDate,
            'CheckoutDate': guestversion.CheckoutDate,
            'IsMainGuest': guestversion.IsMainGuest,
            'GuestCode': guestversion.GuestCode,
            'GuestUID': guestversion.GuestUID,
            'GuestId': guestversion.GuestId,
            'RelationshipId': guestversion.RelationshipId,
            'EscortTypeId': guestversion.EscortTypeId,
            'VisitPurposeId': guestversion.VisitPurposeId,
            'ExpiryDate': guestversion.ExpiryDate,
            'IssueDate': guestversion.IssueDate,
            'DocumentTypeId': guestversion.DocumentTypeId,
            'LogId': guestversion.LogId,
            'CheckinGuestId': guestversion.CheckinGuestId,
            'BirthPlaceName': guestversion.BirthPlaceName,
            'ResidenceCountryTwoCode': guestversion.ResidenceCountryTwoCode,
            'IssueCountryTwoCode': guestversion.IssueCountryTwoCode,
            'AttachmentInfoListJson': guestversion.AttachmentInfoListJson,
            'CurrentMainCheckinGuestId': guestversion.CurrentMainCheckinGuestId,
        },
        sequence_column='LogId',
        filters={
            'checkin_id': GuestVersion.CheckinId,
            'guest_id': GuestVersion.GuestId,
        },
    )
