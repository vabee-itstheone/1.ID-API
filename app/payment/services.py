from app.models import Payment
from app import db
from app.utilities.table_query import fetch_rows


def get_payment_data():
    # AddedAt is deliberately handed over as a datetime, not an ISO string:
    # jsonify renders it as an HTTP date and that is what callers of this
    # endpoint already parse.
    return fetch_rows(
        Payment,
        lambda payment: {
            'Id': payment.Id,
            'CardNumber': payment.CardNumber,
            'PaidAmount': payment.PaidAmount,
            'AddedAt': payment.AddedAt,
            'AddedFrom': payment.AddedFrom,
            'PaymentTypeId': payment.PaymentTypeId,
            'CardTypeId': payment.CardTypeId,
        },
    )
