from flask import Blueprint, jsonify, request
from app.roomchange.services import get_roomchange_data
from app import db
from flask import Blueprint
from app.roomchange import roomchange_bp
from app.models import Payment, Checkin, Guest, GuestAttachment, CheckinGuest, Log, GuestVersion, Room, Country, Emirate, DocumentType, VisitPurpose, Relationship,  PaymentType, CheckinType, CardType, Checkout, RoomChange, MainGuestChange
from datetime import datetime, timezone
import uuid
import base64
import re
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import base64
import json
import tzlocal


# Automatically detect the local time zone
local_timezone = tzlocal.get_localzone()  # Detects local time zone based on the machine

# Get the current local time in ISO format with microseconds and time zone offset
local_time = datetime.now(local_timezone)

# Format the timestamp with microseconds and the timezone offset
local_time_str = local_time.isoformat()

roomchange_bp = Blueprint('roomchange', __name__)

@roomchange_bp.route('/roomchange', methods=['GET'])
def roomchange():
    data = get_roomchange_data()
    return jsonify(data)



@roomchange_bp.route('/roomchange', methods=['POST'])
def create_roomchange():
    data = request.json

    establishment_uid = data.get('ClientUID')
    # Extract data from the request
    current_checkin_id = data.get('CheckinUID')
    
    db_current_checkin = Checkin.query.get(current_checkin_id)
    
    
    try:

        room_change_time = datetime.fromisoformat(data['EffectiveDate'])
        current_checkin_time = db_current_checkin.CheckinDate
        

        if not db_current_checkin.IsActive:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40011 Checkin is already checkedout"},
                "messageType": "RoomChangeResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
            
        
        
        
        if not db_current_checkin:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40009  Checkin is not specified"},
                "messageType": "RoomChangeResponse",
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
                "messageType": "RoomChangeResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        
        
        
        
        current_datetime = datetime.now()
        # print(checkin_date)
        # print(current_datetime)
        if room_change_time > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Room Change date must not be in future"},
                "messageType": "RoomChangeResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        if room_change_time < current_checkin_time:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": f"40004 The Room Change time should be after the Primary Checkin Time at {current_checkin_time}"},
                "messageType": "RoomChangeResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 80001: The new room does not exist
        new_room_number = data.get('NewRoomNumber')
        room = Room.query.filter_by(RoomNumber=new_room_number).first()
        if not room:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "80001 The new room does not exist"},
                "messageType": "RoomChangeResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 80003: Checkin room is occupied
        
        
        if room.IsChecked:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "80003 The new room is Occupied"},
                "messageType": "RoomChangeResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        
        error_response = roomchange_date_time_overlap_status(new_room_number, room_change_time, "CheckinRequest")
        print("error_response",error_response)
        if error_response:
            return jsonify({
                "hasErrors": True,
                "errorMessages":error_response,
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Get the most recent RoomChange entry for the checkin
        previous_room_change = RoomChange.query.filter_by(CheckinId=db_current_checkin.Id).order_by(RoomChange.Id.desc()).first()
        if previous_room_change and previous_room_change.EffectiveDateTime is not None:
            print(previous_room_change)

            if room_change_time <= previous_room_change.EffectiveDateTime:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {
                        "general": f"The Room Change Overlaps with the Previous Room Change at {previous_room_change.EffectiveDateTime}"
                    },
                    "messageType": "RoomChangeResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

        # Get the most recent MainGuestChange entry for the checkin
        previous_main_guest_change = MainGuestChange.query.filter_by(CheckinId=db_current_checkin.Id).order_by(MainGuestChange.Id.desc()).first()
        if previous_main_guest_change and previous_main_guest_change.EffectiveDateTime is not None:
            print(previous_main_guest_change)
            if room_change_time <= previous_main_guest_change.EffectiveDateTime:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {
                        "general": f"The Room Change Overlaps with the Previous Main Guest Change at {previous_main_guest_change.EffectiveDateTime}"
                    },
                    "messageType": "RoomChangeResponse",
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
                if room_change_time <= previous_checkin_guest.CheckinDate:
                    return jsonify({
                        "hasErrors": True,
                        "errorMessages": {
                            "general": f"The Room Change time should be greater than the Previous Escort's check-in Time at {previous_checkin_guest.CheckinDate}"
                        },
                        "messageType": "RoomChangeResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400
            if previous_checkin_guest.CheckoutDate:
                if room_change_time <= previous_checkin_guest.CheckoutDate:
                    return jsonify({
                        "hasErrors": True,
                        "errorMessages": {
                            "general": f"The Room Change time should be greater than the Previous Escort's Checkout Time at {previous_checkin_guest.CheckoutDate}"
                        },
                        "messageType": "RoomChangeResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400

        
        current_room_number = db_current_checkin.RoomNumber
        
        db_current_checkin.RoomNumber = new_room_number
        db_current_checkin.IsFeeUpdated = False
        db.session.commit()

        current_room = Room.query.filter_by(RoomNumber=current_room_number).first()
        new_room = Room.query.filter_by(RoomNumber=new_room_number).first()
        
        current_room.CheckinId = None
        current_room.IsChecked = False
        db.session.commit()

        new_room.CheckinId = db_current_checkin.Id
        new_room.IsChecked = True
        db.session.commit()

        # Log the room change
        log = Log(
            AddedAt=local_time_str,
            RoomNumber=new_room_number,
            RequestType="RoomChange POST",
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

        # Record the room change
        room_change = RoomChange(
            FromRoomNumber=current_room_number,
            ToRoomNumber=new_room_number,
            CheckinId=db_current_checkin.Id,
            EffectiveDateTime=room_change_time,
            AddedAt=local_time_str,
            AddedFrom=request.remote_addr,  # Adjust as necessary
            LogId=log.Id
        )
        db.session.add(room_change)
        db.session.commit()

        response = {
                    "CheckinUID": current_checkin_id
                }

        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    


def roomchange_date_time_overlap_status(room, date_time, checkin_action_name):
    two_months_ago = datetime.now() - timedelta(days=60)
    # Remove milliseconds by setting microseconds to 0
    two_months_ago = two_months_ago.replace(microsecond=0)


    logs_1 = Log.query.filter(
                Log.RoomNumber == room,
                Log.AddedAt >= two_months_ago
            ).all()
    
    print("Roomchange Date", date_time)
    print("logs_1",logs_1)
            
    for log_1 in logs_1:
        print(log_1.Id, log_1.RequestType)
        print(log_1)
        if log_1.RequestType == "Checkin POST":
            # checkin_1 = session.query(Checkin).filter(Checkin.Id == log.CheckinId).first()
            checkin_1 = Checkin.query.filter(
                    Checkin.Id == log_1.CheckinId).first()
           

            if checkin_1:
                room_change_log = Log.query.filter(
                    
                        Log.CheckinId == checkin_1.Id,
                        Log.RequestType == "RoomChange POST"
                    ).first()
                
                if room_change_log:
                    room_change = RoomChange.query.filter(RoomChange.CheckinId == checkin_1.Id).first()
                    if room_change:
                        if date_time >= checkin_1.CheckinDate and date_time <= room_change.EffectiveDateTime:
                            return f"The Room Change Date and Time overlaps with the Previous Checkin. (CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and [Room Change Time: {room_change.EffectiveDateTime}]"
                else:
                    checkout_1 = Checkout.query.filter(Checkout.CheckinId == checkin_1.Id).first()
                    if checkout_1:
                        if date_time >= checkin_1.CheckinDate and date_time <= checkout_1.CheckoutDate:
                            return f"The Room Change Date and Time overlaps with the Previous Checkin. (CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and [Checkout Time: {checkout_1.CheckoutDate}]"

        if log_1.RequestType == "RoomChange POST":
            # Get all room change records for the related CheckinId
            room_changes = RoomChange.query.filter(RoomChange.CheckinId == log_1.CheckinId).order_by(RoomChange.EffectiveDateTime).all()

            # Find the room change record with LogId matching the current log
            room_change_1 = next((rc for rc in room_changes if rc.LogId == log_1.Id), None)

            if room_change_1:
                # Find the next room change in the list after the current room_change_1
                room_change_2 = None
                for i, rc in enumerate(room_changes):
                    if rc.LogId == log_1.Id and i + 1 < len(room_changes):
                        room_change_2 = room_changes[i + 1]
                        break

                if room_change_2:
                    # Check if input dateTime is within the range of roomChange_1 and roomChange_2 EffectiveDateTime
                    if room_change_1.EffectiveDateTime <= date_time <= room_change_2.EffectiveDateTime:
                        return f"The Room Change Date and Time overlaps with the Previous Checkin. (CheckinID: {log_1.CheckinId}) between [Room Change Time 1: {room_change_1.EffectiveDateTime}] and [Room Change Time 2: {room_change_2.EffectiveDateTime}]"
                else:
                    # If no next room change exists, check against the checkout table
                    checkout_2 = Checkout.query.filter(Checkout.CheckinId == log_1.CheckinId).first()

                    if checkout_2 and room_change_1.EffectiveDateTime <= date_time <= checkout_2.CheckoutDate:
                        return f"The Room Change Date and Time overlaps with the Previous Checkin. (CheckinID: {log_1.CheckinId}) between [Room Change Time: {room_change_1.EffectiveDateTime}] and [Checkout Time: {checkout_2.CheckoutDate}]"

        if log_1.RequestType == "AddBackdatedMainGuestCheckin POST" :
            # Get the CheckinDate for the related CheckinId
            checkin_2 = Checkin.query.filter(Checkin.Id == log_1.CheckinId).first()

            if checkin_2:
                checkout_3 = Checkout.query.filter(Checkout.CheckinId == checkin_2.Id).first()

                if checkout_3 and checkin_2.CheckinDate <= date_time <= checkout_3.CheckoutDate:
                    return f"The Room Change Date and Time overlaps with the Previous Backdated Checkin. (CheckinID: {checkin_2.Id}) between [Checkin Time: {checkin_2.CheckinDate}] and [Checkout Time: {checkout_3.CheckoutDate}]"
                
        # Get the previous check-in for the given room, ordered by the latest ID
    previous_checkin = Checkin.query.filter(Checkin.RoomNumber == room).order_by(Checkin.Id.desc()).first()

    if not previous_checkin:
        return ""

    if checkin_action_name != "BackdatedCheckinAction":
        # New Check-in
        if not previous_checkin.IsActive:
            previous_checkout = Checkout.query.filter(Checkout.CheckinId == previous_checkin.Id).first()
            
            if not previous_checkout:
                return f"The Checkout Record for CheckinId: {previous_checkin.Id} is Missing and This Date is therefore Overlapping"
            elif date_time <= previous_checkout.CheckoutDate:
                return f"The Room Change Date and Time overlaps with the Previous Checkin. (CheckinID: {previous_checkin.Id}) [Checkout Time: {previous_checkout.CheckoutDate}]"

        # Adding an escort or editing available guests
        else:
            previous_checkout = (
                CheckinGuest.query.filter(CheckinGuest.CheckinId == previous_checkin.Id).first()
            )

            if previous_checkout and previous_checkout.CheckoutDate:
                if (date_time < previous_checkin.CheckinDate or date_time > previous_checkout.CheckoutDate) and (
                    checkin_action_name != "EditGuestAction"
                ):
                    return f"The Checkin-in date and time should be between the primary check-in time: {previous_checkin.CheckinDate}, and the checkout time: {previous_checkout.CheckoutDate}."
            
            elif date_time < previous_checkin.CheckinDate and checkin_action_name != "EditGuestAction":
                return f"The Checkin Date and Time should be after the primary check-in time: {previous_checkin.CheckinDate}"


    return None


