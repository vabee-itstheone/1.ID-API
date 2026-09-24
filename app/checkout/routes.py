from flask import jsonify, request
from app import db
from flask import Blueprint
from app.checkout.services import get_checkout_data
from app.checkout import checkout_bp
from app.models import Payment, Checkin, Guest, GuestAttachment, CheckinGuest, Log, GuestVersion, Room, Country, Emirate, DocumentType, VisitPurpose, Relationship,  PaymentType, CheckinType, CardType, Checkout, RoomChange, MainGuestChange, Checkout
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

checkout_bp = Blueprint('checkout', __name__)

@checkout_bp.route('/checkout', methods=['GET'])
def checkout():
    data = get_checkout_data()
    return jsonify(data)


@checkout_bp.route('/checkout', methods=['POST'])
def create_checkout():
    data = request.json

    establishment_uid = data.get('ClientUID')
    # Extract data from the request
    current_checkin_id = data.get('CheckinUID')
    # Validation 40014: Checkout Date Time is invalid
        
        
        
    if not data['CheckoutDateTime']:
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40014 Checkout Date Time is invalid"},
            "messageType": "CheckoutResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400
    checkout_date_time = datetime.fromisoformat(data['CheckoutDateTime'])
    is_late_checkout = data.get('IsLateCheckout', False)

    # Validation 40034: Check-out date and time should be equal or after any guest check-in
    all_checkedout_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id).filter(CheckinGuest.CheckoutDate.isnot(None)).all()

    
    for guest in all_checkedout_guests:
        # print("Guest Checkout Date",guest.Id, guest.CheckoutDate)
        # print("Room Checkout Date", guest.Id,checkout_date_time)

        if checkout_date_time < guest.CheckoutDate:
            
            return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40034 Check-out date and time should be equal or after any guestcheck-out"},
            "messageType": "CheckoutResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400


        
        

    # Validation 40034: Check-out date and time should be equal or after any guest check-in
    all_checkin_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id).all()

    
    for checkinguest in all_checkin_guests:
        # print("Guest Checkin Date",checkinguest.Id, checkinguest.CheckinDate)
        # print("Room Checkout Date",checkinguest.Id, checkout_date_time)

        if checkout_date_time < checkinguest.CheckinDate:
            
            return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40034 Check-out date and time should be equal or after any guestcheck-in"},
            "messageType": "CheckoutResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400

        


    try:
        # Fetch the current check-in
        # Validation 40009: Checkin is not specified
        db_current_checkin = Checkin.query.get(current_checkin_id)
        if not db_current_checkin:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40009  Checkin is not specified"},
                "messageType": "CheckoutResponse",
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
                "messageType": "CheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40011: Checkin is already checkedout
        
        if not db_current_checkin.IsActive:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40011 Checkin is already checkedout"},
                "messageType": "CheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
         # Validation 40014: Checkout Date Time is invalid
        
        
        
        if not checkout_date_time:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40014 Checkout Date Time is invalid"},
                "messageType": "CheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40004: Checkout date must not be in future
        
        
        current_datetime = datetime.now()
        # print(checkin_date)
        # print(current_datetime)
        if checkout_date_time > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Checkout date must not be in future"},
                "messageType": "CheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40039: Check-out with house use flag does not require late checkout
        if db_current_checkin.CheckinTypeId == 2 and data.get('IsLateCheckout'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40039 Check-out with house use flag does not require late checkout"},
                "messageType": "CheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        # Get the most recent RoomChange entry for the checkin
        previous_room_change = RoomChange.query.filter_by(CheckinId=db_current_checkin.Id).order_by(RoomChange.Id.desc()).first()
        if previous_room_change and previous_room_change.EffectiveDateTime is not None:
            print(previous_room_change)

            if checkout_date_time <= previous_room_change.EffectiveDateTime:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {
                        "general": f"The Room Change Overlaps with the Previous Room Change at {previous_room_change.EffectiveDateTime}"
                    },
                    "messageType": "CheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

        # Get the most recent MainGuestChange entry for the checkin
        previous_main_guest_change = MainGuestChange.query.filter_by(CheckinId=db_current_checkin.Id).order_by(MainGuestChange.Id.desc()).first()
        if previous_main_guest_change and previous_main_guest_change.EffectiveDateTime is not None:
            print(previous_main_guest_change)
            if checkout_date_time <= previous_main_guest_change.EffectiveDateTime:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {
                        "general": f"The Checkout Overlaps with the Previous Main Guest Change at {previous_main_guest_change.EffectiveDateTime}"
                    },
                    "messageType": "CheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

        # Get the most recent CheckinGuest entry for the checkin
        previous_checkin_guest = CheckinGuest.query.filter_by(CheckinId=db_current_checkin.Id).order_by(CheckinGuest.Id.desc()).first()
        if previous_checkin_guest:
            print(previous_checkin_guest)
            if previous_checkin_guest.CheckinDate:
                if checkout_date_time <= previous_checkin_guest.CheckinDate:
                    return jsonify({
                        "hasErrors": True,
                        "errorMessages": {
                            "general": f"The Checkout time should be greater than the Previous Escort's check-in Time at {previous_checkin_guest.CheckinDate}"
                        },
                        "messageType": "CheckoutResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400
            if previous_checkin_guest.CheckoutDate:
                if checkout_date_time <= previous_checkin_guest.CheckoutDate:
                    return jsonify({
                        "hasErrors": True,
                        "errorMessages": {
                            "general": f"The Checkout time should be greater than the Previous Escort's Checkout Time at {previous_checkin_guest.CheckoutDate}"
                        },
                        "messageType": "CheckoutResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400

        # Update the check-in status
        db_current_checkin.IsActive = False
        db_current_checkin.IsFeeUpdated = False
        db.session.commit()

        # room_id = db_current_checkin.RoomNumber
        room_number = db_current_checkin.RoomNumber
        
        # Update the room status
        db_current_room = Room.query.filter_by(RoomNumber=room_number).first()
        # db_current_room = Room.query.get(room_id)
        if db_current_room:
            db_current_room.IsChecked = False
            db_current_room.CheckinId = None
            db.session.commit()

        # Create a new checkout record
        checkout = Checkout(
            CheckoutDate=checkout_date_time,
            ChargeExtra=is_late_checkout,
            AddedFrom=request.remote_addr,
            CheckinId=current_checkin_id,
            CancellationReasonId=None,
            CheckoutTypeId=1
        )
        db.session.add(checkout)
        db.session.commit()

        # Update associated check-in guests
        associated_checkin_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id, CheckoutDate=None).all()
        associated_main_guest = CheckinGuest.query.filter_by(CheckinId=current_checkin_id, IsMainGuest=True).order_by(CheckinGuest.Id.desc()).first()
        for guest in associated_checkin_guests:
            guest.CheckoutDate = checkout_date_time

        db.session.commit()

        # Log the checkout event
        log = Log(
            RoomNumber=room_number,
            RequestType="Checkout POST",  # Assuming 2 is the ID for "Cancelled"
            DtcmStatus=-1,
            CidStatus=-1,
            CheckinGuestId=associated_main_guest.Id,
            CheckinId=current_checkin_id
        )
        db.session.add(log)
        db.session.commit()

        response = {
                    "CheckinUID": current_checkin_id
                }

        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@checkout_bp.route('/checkout', methods=['PUT'])
def update_checkout():
    data = request.json

    establishment_uid = data.get('ClientUID')
    # Extract data from the request
    current_checkin_id = data.get('CheckinUID')
    # Validation 40014: Checkout Date Time is invalid
        
    # Validation 40031: Checkin is already checkedout
    db_current_checkin = Checkin.query.get(current_checkin_id)
    
    if db_current_checkin.IsActive:
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40031 Check-in is already active"},
            "messageType": "CheckoutUpdateResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400
        
        
    if not data['CheckoutDateTime']:
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40014 Checkout Date Time is invalid"},
            "messageType": "CheckoutUpdateResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400
    checkout_date_time = datetime.fromisoformat(data['CheckoutDateTime'])
    is_late_checkout = data.get('IsLateCheckout', False)

    # Validation 40034: Check-out date and time should be equal or after any guest check-in
    all_checkedout_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id).filter(CheckinGuest.CheckoutDate.isnot(None)).all()

    
    # for guest in all_checkedout_guests:
    #     # print("Guest Checkout Date",guest.Id, guest.CheckoutDate)
    #     # print("Room Checkout Date", guest.Id,checkout_date_time)

    #     if checkout_date_time < guest.CheckoutDate:
            
    #         return jsonify({
    #         "hasErrors": True,
    #         "errorMessages": {"general": "40034 Check-out date and time should be equal or after any guestcheck-out"},
    #         "messageType": "CheckoutUpdateResponse",
    #         "clientUID": establishment_uid,
    #         "messageUID": str(uuid.uuid4()),
    #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
    #         "timestamp": local_time_str
    #     }), 400


        
        

    # Validation 40032: Check-out date and time should be equal or after any guest check-in
    all_checkin_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id).all()

    
    for checkinguest in all_checkin_guests:
        # print("Guest Checkin Date",checkinguest.Id, checkinguest.CheckinDate)
        # print("Room Checkout Date",checkinguest.Id, checkout_date_time)

        if checkout_date_time < checkinguest.CheckinDate:
            
            return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40032 Check-out date and time should be equal or after any guestcheck-in"},
            "messageType": "CheckoutUpdateResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400

        


    try:
        # Fetch the current check-in
        # Validation 40009: Checkin is not specified
        
        if not db_current_checkin:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40009  Checkin is not specified"},
                "messageType": "CheckoutUpdateResponse",
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
                "messageType": "CheckoutUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        
         # Validation 40014: Checkout Date Time is invalid
        
        
        
        if not checkout_date_time:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40014 Checkout Date Time is invalid"},
                "messageType": "CheckoutUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40004: Checkout date must not be in future
        
        
        current_datetime = datetime.now()
        # print(checkin_date)
        # print(current_datetime)
        if checkout_date_time > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Checkout date must not be in future"},
                "messageType": "CheckoutUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40039: Check-out with house use flag does not require late checkout
        if db_current_checkin.CheckinTypeId == 2 and data.get('IsLateCheckout'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40039 Check-out with house use flag does not require late checkout"},
                "messageType": "CheckoutUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        # Get the most recent RoomChange entry for the checkin
        previous_room_change = RoomChange.query.filter_by(CheckinId=db_current_checkin.Id).order_by(RoomChange.Id.desc()).first()
        if previous_room_change and previous_room_change.EffectiveDateTime is not None:
            print(previous_room_change)

            if checkout_date_time <= previous_room_change.EffectiveDateTime:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {
                        "general": f"The Room Change Overlaps with the Previous Room Change at {previous_room_change.EffectiveDateTime}"
                    },
                    "messageType": "CheckoutUpdateResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

        # Get the most recent MainGuestChange entry for the checkin
        previous_main_guest_change = MainGuestChange.query.filter_by(CheckinId=db_current_checkin.Id).order_by(MainGuestChange.Id.desc()).first()
        if previous_main_guest_change and previous_main_guest_change.EffectiveDateTime is not None:
            print(previous_main_guest_change)
            if checkout_date_time <= previous_main_guest_change.EffectiveDateTime:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {
                        "general": f"The Checkout Overlaps with the Previous Main Guest Change at {previous_main_guest_change.EffectiveDateTime}"
                    },
                    "messageType": "CheckoutUpdateResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

        # Get the most recent CheckinGuest entry for the checkin
        previous_checkin_guest = CheckinGuest.query.filter_by(CheckinId=db_current_checkin.Id).order_by(CheckinGuest.Id.desc()).first()
        if previous_checkin_guest:
            print(previous_checkin_guest)
            if previous_checkin_guest.CheckinDate:
                if checkout_date_time <= previous_checkin_guest.CheckinDate:
                    return jsonify({
                        "hasErrors": True,
                        "errorMessages": {
                            "general": f"The Checkout time should be greater than the Previous Escort's check-in Time at {previous_checkin_guest.CheckinDate}"
                        },
                        "messageType": "CheckoutUpdateResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400
            # if previous_checkin_guest.CheckoutDate:
            #     if checkout_date_time <= previous_checkin_guest.CheckoutDate:
            #         return jsonify({
            #             "hasErrors": True,
            #             "errorMessages": {
            #                 "general": f"The Checkout time should be greater than the Previous Escort's Checkout Time at {previous_checkin_guest.CheckoutDate}"
            #             },
            #             "messageType": "CheckoutUpdateResponse",
            #             "clientUID": establishment_uid,
            #             "messageUID": str(uuid.uuid4()),
            #             "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            #             "timestamp": local_time_str
            #         }), 400
        
        
        # Update the check-in status
        db_current_checkin.IsActive = False
        db_current_checkin.IsFeeUpdated = False
        db.session.commit()

        room_id = db_current_checkin.RoomNumber

        # Update the room status
        db_current_room = Room.query.get(room_id)
        if db_current_room:
            db_current_room.IsChecked = False
            db_current_room.CheckinId = None
            db.session.commit()

        existing_checkout = Checkout.query.filter_by(CheckinId=current_checkin_id).first()

        if existing_checkout:
            # Update the existing record
            existing_checkout.CheckoutDate = checkout_date_time
            existing_checkout.ChargeExtra = is_late_checkout
            existing_checkout.AddedFrom = request.remote_addr
            existing_checkout.CancellationReasonId = None
            existing_checkout.CheckoutTypeId = 1

            # Commit the changes to the database
            db.session.commit()
        # Create a new checkout record
        # checkout = Checkout(
        #     CheckoutDate=checkout_date_time,
        #     ChargeExtra=is_late_checkout,
        #     AddedFrom=request.remote_addr,
        #     CheckinId=current_checkin_id,
        #     CancellationReasonId=None,
        #     CheckoutTypeId=1
        # )
        # db.session.add(checkout)
        # db.session.commit()

        # Update associated check-in guests
        associated_checkin_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id).all()
        associated_main_guest = CheckinGuest.query.filter_by(CheckinId=current_checkin_id, IsMainGuest=True).order_by(CheckinGuest.Id.desc()).first()
        # print("associated_checkin_guests",associated_checkin_guests)
        for guest in associated_checkin_guests:
            guest.CheckoutDate = checkout_date_time
            # print(guest.CheckoutDate)

        db.session.commit()

        # Log the checkout event
        log = Log(
            RoomNumber=room_id,
            RequestType="Checkout POST",  # Assuming 2 is the ID for "Cancelled"
            DtcmStatus=-1,
            CidStatus=-1,
            CheckinGuestId=associated_main_guest.Id,
            CheckinId=current_checkin_id
        )
        db.session.add(log)
        db.session.commit()

        response = {
                    "CheckinUID": current_checkin_id
                }

        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
