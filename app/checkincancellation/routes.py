from flask import Blueprint, jsonify, request
from app.checkincancellation.services import get_checkincancellation_data
from app import db
from flask import Blueprint
from app.roomchange import roomchange_bp
from app.models import Payment, Checkin, Guest, GuestAttachment, CheckinGuest, Log, GuestVersion, Room, Country, Emirate, DocumentType, VisitPurpose, Relationship,  PaymentType, CheckinType, CardType, Checkout, RoomChange, CancellationReason
from datetime import datetime, timezone
import uuid
import base64
import re
from flask import Flask, request, jsonify
from datetime import datetime
import base64
import json
import tzlocal


# Automatically detect the local time zone
local_timezone = tzlocal.get_localzone()  # Detects local time zone based on the machine

# Get the current local time in ISO format with microseconds and time zone offset
local_time = datetime.now(local_timezone)

# Format the timestamp with microseconds and the timezone offset
local_time_str = local_time.isoformat()

checkincancellation_bp = Blueprint('checkincancellation', __name__)

@checkincancellation_bp.route('/checkincancellation', methods=['GET'])
def checkincancellation():
    data = get_checkincancellation_data()
    return jsonify(data)


@checkincancellation_bp.route('/checkincancellation', methods=['POST'])
def create_checkincancellation():
    data = request.json

    establishment_uid = data.get('ClientUID')
    # Extract data from the request
    current_checkin_id = data.get('CheckinUID')
    
    db_current_checkin = Checkin.query.get(current_checkin_id)
    
    
    try:

        cancellation_date_time = datetime.fromisoformat(data['CancellationDateTime'])
        
        # Validation 40011: Checkin is already checkedout

        if not db_current_checkin.IsActive:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40011 Checkin is already checkedout"},
                "messageType": "CheckinCancellationRequest",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
            
        
        # Validation 40009: Checkin is not specified
        
        if not db_current_checkin:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40009  Checkin is not specified"},
                "messageType": "CheckinCancellationRequest",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        # Validation 40010: Checkin is already cancelled

        cancelled_checkin = (
                                Checkout.query
                                .filter(
                                    Checkout.CheckinId == db_current_checkin.Id, 
                                    Checkout.CheckoutTypeId == 2  # Assuming 2 represents a "canceled" status
                                )
                                .order_by(Checkout.Id.desc())
                                .first()
                            )
        # print(cancelled_checkin)
        
        if cancelled_checkin:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40010 Checkin is already cancelled"},
                "messageType": "CheckinCancellationRequest",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        
        
        # Validation 40025: Cancellation date time is not specified or overlap with checkin date time
        if not cancellation_date_time or cancellation_date_time < db_current_checkin.CheckinDate:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40025 Cancellation date time is not specified or overlap with checkin date time"},
                "messageType": "CheckinCancellationRequest",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        current_datetime = datetime.now()
        # print(checkin_date)
        # print(current_datetime)
        if cancellation_date_time > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Cancellation date must not be in future"},
                "messageType": "CheckinCancellationRequest",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        if  datetime.now().month > db_current_checkin.CheckinDate.month:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {
            "general": ( f"The Cancel Checkout should be done in the same month "
                f"({db_current_checkin.CheckinDate.strftime('%B')}) as the original check-in date."
            )
        },
                "messageType": "CheckinCancellationRequest",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        
        
        

        cancellation_reason_code = data.get('CancellationReasonCode')
        current_room = Room.query.filter_by(CheckinId=db_current_checkin.Id).first()
        cancellation_reason_id = CancellationReason.query.filter_by(DtcmCode=cancellation_reason_code).first()
        
        db_current_checkin.IsActive = False
        db_current_checkin.IsFeeUpdated = False
        db.session.commit()

        current_room.CheckinId = None
        current_room.IsChecked = False
        db.session.commit()

        # Update associated check-in guests
        associated_checkin_guests = CheckinGuest.query.filter_by(CheckinId=db_current_checkin.Id, CheckoutDate=None).all()
        associated_main_guest = CheckinGuest.query.filter_by(CheckinId=db_current_checkin.Id, IsMainGuest=True).order_by(CheckinGuest.Id.desc()).first()
        for guest in associated_checkin_guests:
            guest.CheckoutDate = cancellation_date_time

        db.session.commit()

        # Log the room change
        log = Log(
            AddedAt=local_time_str,
            RoomNumber=current_room.RoomNumber,
            RequestType="CheckinCancellation POST",
            DtcmStatus=-1,
            CidStatus=-1,
            CheckinUID=None,
            PayloadIdentifier=None,
            Error=None,
            CheckinGuestId=CheckinGuest.query.filter_by(CheckinId=db_current_checkin.Id, IsFirstGuest=True).first().Id,
            CheckinId=db_current_checkin.Id
        )
        db.session.add(log)
        db.session.commit()

        # Create a new checkout record
        checkout = Checkout(
            CheckoutDate=cancellation_date_time,
            ChargeExtra=False,
            AddedFrom=request.remote_addr,
            CheckinId=current_checkin_id,
            CancellationReasonId=cancellation_reason_id.Id,
            CheckoutTypeId=2
        )
        db.session.add(checkout)
        db.session.commit()

        response = {
                    "CheckinUID": current_checkin_id
                }

        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
