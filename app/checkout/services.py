from app.models import Checkout
from app import db
from app.utilities.table_query import fetch_rows


def get_checkout_data():
    # The row a client is usually after here is the one that was just written.
    # ?since_id=<last Id you saw> returns exactly that, instead of all 36,080.
    return fetch_rows(
        Checkout,
        lambda checkout: {
            'Id': checkout.Id,
            'CheckoutDate': checkout.CheckoutDate.isoformat() if checkout.CheckoutDate else None,
            'ChargeExtra': checkout.ChargeExtra,
            'AddedAt': checkout.AddedAt.isoformat() if checkout.AddedAt else None,
            'AddedFrom': checkout.AddedFrom,
            'CheckinId': checkout.CheckinId,
            'CancellationReasonId': checkout.CancellationReasonId,
            'CheckoutTypeId': checkout.CheckoutTypeId,
        },
        filters={
            'checkin_id': Checkout.CheckinId,
        },
    )
