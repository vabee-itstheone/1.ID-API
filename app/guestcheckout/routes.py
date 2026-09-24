from flask import jsonify, request
from app import db
from flask import Blueprint
from app.guestcheckout.services import get_guestcheckout_data
from app.guestcheckout import guestcheckout_bp
from app.models import Payment, Checkin, Guest, GuestAttachment, CheckinGuest, Log, GuestVersion, Room, Country, Emirate, DocumentType, VisitPurpose, Relationship,  PaymentType, CheckinType, CardType, Checkout,MainGuestChange
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

guestcheckout_bp = Blueprint('guestcheckout', __name__)

@guestcheckout_bp.route('/guestcheckout', methods=['GET'])
def checkout():
    data = get_guestcheckout_data()
    return jsonify(data)


@guestcheckout_bp.route('/guestcheckout', methods=['POST'])
def update_guestcheckout():
    data = request.json

    establishment_uid = data.get('ClientUID')
    # Extract data from the request
    current_checkin_id = data.get('CheckinUID')
    current_guest_id = data.get('GuestUID')
    current_checkin_guest_id = CheckinGuest.query.filter(
                                CheckinGuest.CheckinId == current_checkin_id,
                                CheckinGuest.GuestId == current_guest_id
                                # Ensure 'IsMainGuest' is used correctly
                            ).order_by(CheckinGuest.Id.desc()).first()
    print(current_checkin_guest_id)
    db_current_checkin = Checkin.query.get(current_checkin_id)

    # Validation 40014: Checkout Date Time is invalid
        
    # Validation 40011: Checkin is already checkedout
    db_current_checkin = Checkin.query.get(current_checkin_id)
    
    if not db_current_checkin.IsActive:
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40011 Checkin is already checkedout"},
            "messageType": "GuestCheckoutResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400
        
        
    if not data['CheckoutDateTime']:
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40014 Checkout Date Time is invalid"},
            "messageType": "GuestCheckoutResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400
    checkout_date_time = datetime.fromisoformat(data['CheckoutDateTime'])
    # is_late_checkout = data.get('IsLateCheckout', False)

    # # Validation 40034: Check-out date and time should be equal or after any guest check-in
    # all_checkedout_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id).filter(CheckinGuest.CheckoutDate.isnot(None)).all()

    
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


        
        

    # # Validation 40032: Check-out date and time should be equal or after any guest check-in
    # all_checkin_guests = CheckinGuest.query.filter_by(CheckinId=current_checkin_id).all()

    
    # for checkinguest in all_checkin_guests:
    #     # print("Guest Checkin Date",checkinguest.Id, checkinguest.CheckinDate)
    #     # print("Room Checkout Date",checkinguest.Id, checkout_date_time)

    #     if checkout_date_time < checkinguest.CheckinDate:
            
    #         return jsonify({
    #         "hasErrors": True,
    #         "errorMessages": {"general": "40032 Check-out date and time should be equal or after any guestcheck-in"},
    #         "messageType": "CheckoutUpdateResponse",
    #         "clientUID": establishment_uid,
    #         "messageUID": str(uuid.uuid4()),
    #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
    #         "timestamp": local_time_str
    #     }), 400

    if checkout_date_time < current_checkin_guest_id.CheckinDate:
            
            return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40032 Check-out date and time should be after guest check-in date time"},
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
                "messageType": "GuestCheckoutResponse",
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
                "messageType": "GuestCheckoutResponse",
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
                "messageType": "GuestCheckoutResponse",
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
                "messageType": "GuestCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 50017: Guest is not in room, already checked out
        checkedout_checkin_guest = CheckinGuest.query.filter(
            CheckinGuest.CheckoutDate != None,
            CheckinGuest.Id == current_checkin_guest_id.Id
        ).first() 
        if checkedout_checkin_guest:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50017 Guest is not in room, already checked out"},
                "messageType": "GuestCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        
        # Validation 50019: the main guest cannot leave without a successor.
        # Checking them out anyway leaves the stay with no main guest, which then
        # breaks every later guestversion write for that stay.
        if (current_checkin_guest_id and current_checkin_guest_id.IsMainGuest
                and not data.get('NewMainGuestUID')):
            remaining = CheckinGuest.query.filter(
                CheckinGuest.CheckinId == db_current_checkin.Id,
                CheckinGuest.CheckoutDate == None,
                CheckinGuest.Id != current_checkin_guest_id.Id
            ).count()
            if remaining:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50019 Main guest cannot be checked out without a new main guest"},
                    "messageType": "GuestCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

        # Update the check-in status

        db_current_checkin.IsFeeUpdated = False
        db.session.commit()

        room_id = db_current_checkin.RoomNumber

        
        if data.get('NewMainGuestUID') != None:
            print(data.get('NewMainGuestUID'))
            exsisting_mainguest =  CheckinGuest.query.filter(
                    CheckinGuest.CheckinId == db_current_checkin.Id,
                    CheckinGuest.IsMainGuest == True).first()

            new_main_guest = CheckinGuest.query.filter(
                    CheckinGuest.CheckinId == db_current_checkin.Id,
                    CheckinGuest.GuestId == data.get('NewMainGuestUID')).first()
            
            log_entry = Log(
            
            RoomNumber=room_id,
            RequestType="MainGuestChangePOST",  # Assuming enum value
            DtcmStatus=1,
            CidStatus=-1,
            CheckinGuestId=new_main_guest.Id,
            CheckinId=current_checkin_id
            )
        
            db.session.add(log_entry)
            db.session.commit()

            # print("exsisting_mainguest",exsisting_mainguest)
            # print("new_main_guest",new_main_guest)
            # print("log_entry",new_main_guest)

            # Create MainGuestChange entry
            main_guest_change = MainGuestChange(
                FormerMainCheckinGuestId=exsisting_mainguest.Id,
                NewMainCheckinGuestId=new_main_guest.Id,
                CheckinId=current_checkin_id,
                EffectiveDateTime=checkout_date_time,
                AddedAt=local_time_str,
                AddedFrom=request.remote_addr,  # Equivalent to Environment.MachineName in C#
                LogId=log_entry.Id  # Associate with the Log entry
            )
            
            db.session.add(main_guest_change)
            db.session.commit()

            exsisting_mainguest.IsMainGuest = False
            exsisting_mainguest.RelationshipName = new_main_guest.RelationshipName

            db.session.commit()

            new_main_guest.IsMainGuest = True
            new_main_guest.RelationshipName = None

            db.session.commit()

            new_guest_version = GuestVersion.query.filter(
            GuestVersion.CheckinId == current_checkin_id,
            GuestVersion.CheckinGuestId == new_main_guest.Id
            ).order_by(GuestVersion.LogId.desc()).first()

            guest_version = GuestVersion(
                FirstName=new_guest_version.FirstName,
                LastName=new_guest_version.LastName,
                ArabicFirstName=new_guest_version.ArabicFirstName,
                ArabicLastName=new_guest_version.ArabicLastName,
                Gender=new_guest_version.Gender,
                BirthDate=new_guest_version.BirthDate,
                ResidenceCountryPhone=new_guest_version.ResidenceCountryPhone,
                MobileCode=new_guest_version.MobileCode,
                MobileNumber=new_guest_version.MobileNumber,
                Email=new_guest_version.Email,
                RequiresAccessibilityJson=new_guest_version.RequiresAccessibilityJson,
                CheckinId=new_guest_version.CheckinId,
                DocumentNumber=new_guest_version.DocumentNumber,
                NationalityId=new_guest_version.NationalityId,
                EmirateId=new_guest_version.EmirateId,
                CheckinDate=new_guest_version.CheckinDate,
                CheckoutDate=new_guest_version.CheckoutDate,
                IsMainGuest=True,
                GuestCode=new_guest_version.GuestCode,
                GuestUID=new_guest_version.GuestUID,
                GuestId= new_guest_version.GuestId,
                RelationshipId=None,
                EscortTypeId=new_guest_version.EscortTypeId,
                VisitPurposeId=new_guest_version.VisitPurposeId,
                ExpiryDate=new_guest_version.ExpiryDate,
                IssueDate=new_guest_version.IssueDate,
                DocumentTypeId=new_guest_version.DocumentTypeId,
                LogId=log_entry.Id,
                CheckinGuestId=new_guest_version.CheckinGuestId,
                BirthPlaceName=new_guest_version.BirthPlaceName,
                ResidenceCountryTwoCode=new_guest_version.ResidenceCountryTwoCode,
                IssueCountryTwoCode=new_guest_version.IssueCountryTwoCode,  # Assuming IssueCountryId maps to TwoCode
                AttachmentInfoListJson=new_guest_version.AttachmentInfoListJson,
                CurrentMainCheckinGuestId=new_guest_version.CurrentMainCheckinGuestId
            )
            db.session.add(guest_version)
            db.session.commit()


               

        # Update associated check-in guests
        # Query for the associated check-in guest
        associated_checkin_guest = CheckinGuest.query.filter(
            CheckinGuest.CheckinId == current_checkin_id,
            CheckinGuest.Id == current_checkin_guest_id.Id
        ).first()  # Use `.first()` to fetch a single record

        # Check if the guest exists before updating
        if associated_checkin_guest:
            associated_checkin_guest.CheckoutDate = checkout_date_time
            print(associated_checkin_guest.Id)  # Debugging print
            db.session.commit()
        else:
            print("No matching check-in guest found")




        # Log the checkout event
        log = Log(
            RoomNumber=room_id,
            RequestType="GuestCheckout POST",  # Assuming 2 is the ID for "Cancelled"
            DtcmStatus=-1,
            CidStatus=-1,
            CheckinGuestId=associated_checkin_guest.Id,
            CheckinId=current_checkin_id
        )
        db.session.add(log)
        db.session.commit()

        previous_guest_version = GuestVersion.query.filter(
            GuestVersion.CheckinId == current_checkin_id,
            GuestVersion.CheckinGuestId == current_checkin_guest_id.Id
        ).order_by(GuestVersion.LogId.desc()).first()

        print(previous_guest_version)  # Debugging print

        # Step 7: Create GuestVersion
        guest_version = GuestVersion(
            FirstName=previous_guest_version.FirstName,
            LastName=previous_guest_version.LastName,
            ArabicFirstName=previous_guest_version.ArabicFirstName,
            ArabicLastName=previous_guest_version.ArabicLastName,
            Gender=previous_guest_version.Gender,
            BirthDate=previous_guest_version.BirthDate,
            ResidenceCountryPhone=previous_guest_version.ResidenceCountryPhone,
            MobileCode=previous_guest_version.MobileCode,
            MobileNumber=previous_guest_version.MobileNumber,
            Email=previous_guest_version.Email,
            RequiresAccessibilityJson=previous_guest_version.RequiresAccessibilityJson,
            CheckinId=previous_guest_version.CheckinId,
            DocumentNumber=previous_guest_version.DocumentNumber,
            NationalityId=previous_guest_version.NationalityId,
            EmirateId=previous_guest_version.EmirateId,
            CheckinDate=previous_guest_version.CheckinDate,
            CheckoutDate=checkout_date_time,
            IsMainGuest=previous_guest_version.IsMainGuest,
            GuestCode=previous_guest_version.GuestCode,
            GuestUID=previous_guest_version.GuestUID,
            GuestId= previous_guest_version.GuestId,
            RelationshipId=previous_guest_version.RelationshipId,
            EscortTypeId=previous_guest_version.EscortTypeId,
            VisitPurposeId=previous_guest_version.VisitPurposeId,
            ExpiryDate=previous_guest_version.ExpiryDate,
            IssueDate=previous_guest_version.IssueDate,
            DocumentTypeId=previous_guest_version.DocumentTypeId,
            LogId=log.Id,
            CheckinGuestId=previous_guest_version.CheckinGuestId,
            BirthPlaceName=previous_guest_version.BirthPlaceName,
            ResidenceCountryTwoCode=previous_guest_version.ResidenceCountryTwoCode,
            IssueCountryTwoCode=previous_guest_version.IssueCountryTwoCode,  # Assuming IssueCountryId maps to TwoCode
            AttachmentInfoListJson=previous_guest_version.AttachmentInfoListJson,
            CurrentMainCheckinGuestId=previous_guest_version.CurrentMainCheckinGuestId
        )
        db.session.add(guest_version)
        db.session.commit()

        response = {
                    "CheckinUID": current_checkin_id
                }

        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
