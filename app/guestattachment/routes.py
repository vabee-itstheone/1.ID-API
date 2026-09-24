from flask import Blueprint, jsonify
from app.guestattachment.services import get_guestattachment_data
from flask import Blueprint, jsonify, request
from app.guest.services import get_guest_data
from app import db
from app.models import Payment, Checkin, Guest, GuestAttachment, CheckinGuest, Log, GuestVersion, Room, Country, Emirate, DocumentType, VisitPurpose, Relationship,  PaymentType, CheckinType, CardType, Checkout, GuestDocumentImage
from datetime import datetime, timezone
import uuid
import base64
import re
from flask import Flask, request, jsonify
from datetime import datetime
import base64
import json
import tzlocal
from io import BytesIO
from PIL import Image
  # Replace with your actual model and database setup
from app.utilities.image_manipulator import ImageManipulator
from app.utilities.attachment_store import store_guest_attachments
 # Replace with the actual import for ImageManipulator
from googletrans import Translator


translator = Translator()

# Automatically detect the local time zone
local_timezone = tzlocal.get_localzone()  # Detects local time zone based on the machine

# Get the current local time in ISO format with microseconds and time zone offset
local_time = datetime.now(local_timezone)

# Format the timestamp with microseconds and the timezone offset
local_time_str = local_time.isoformat()

guestattachment_bp = Blueprint('guestattachment', __name__)

@guestattachment_bp.route('/guestattachment', methods=['GET'])
def guestattachment():
    data = get_guestattachment_data()
    return jsonify(data)



@guestattachment_bp.route('/guestattachment', methods=['POST'])
def create_guestattachment():
    data = request.json

    try:

        
        establishment_uid = data.get('ClientUID')
        
        checkin_id = data.get('CheckinUID')
        main_checkin =  Checkin.query.filter_by(Id=checkin_id).first()

       

        # Validation 40009: Checkin is not specified
        if not checkin_id:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40009  Checkin is not specified"},
                "messageType": "GuestAttachmentResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40010: Checkin is already cancelled

        cancelled_checkin = (
                                Checkout.query
                                .filter(
                                    Checkout.CheckinId == main_checkin.Id, 
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
                "messageType": "GuestAttachmentResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40011: Checkin is already checkedout
        
        if not main_checkin.IsActive:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40011 Checkin is already checkedout"},
                "messageType": "GuestAttachmentResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
       
        guests_response = []
        # Step 3: Create or Update Guest
        # guest_data = data['Guests'][0]  # Assuming only one guest for simplicity
        

        if not data.get('GuestUID'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50010 Guest is not specified"},
                "messageType": "GuestAttachmentResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        # guest_data = data['GuestInfo']

        # Validation 60001: Attachment is not specified
        
      
        if not data.get('Attachments'):
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "60001 Attachment is not specified"},
                    "messageType": "GuestResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

        # Validation 60004: Attachment should not exceed 200 KB in size
        
        for attachment in data['Attachments']:
            
            
            attachement_code = attachment.get('AttachmentCode')
            if 'ContentBase64Encoded' in attachment:
                attachment_size = len(attachment['ContentBase64Encoded']) * 3 / 4  # Base64 size calculation
                # print(attachement_code , attachment_size)
                if attachment_size > 200 * 1024:  # 200 KB
                    return jsonify({
                        "hasErrors": True,
                        "errorMessages": {"general": "60004 Attachment should not exceed 200 KB in size"},
                        "messageType": "GuestResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400
                
        

        guest_id = data['GuestUID']

        guest_attachment = GuestAttachment.query.filter_by(GuestId=guest_id).first()

        # Extract existing attachment names
        existing_names = set()
        if guest_attachment and guest_attachment.AttachmentInfoListJson:  # Ensure it's not None
            try:
                attachment_list = json.loads(guest_attachment.AttachmentInfoListJson)  # Convert JSON string to Python list
                existing_names = {attachment["Name"] for attachment in attachment_list}  # Extract names
                print("Names:", existing_names)
            except json.JSONDecodeError as e:
                print("JSON decoding error:", e)

        attachments_response = []

        existing_attachments = []
        if guest_attachment and guest_attachment.AttachmentInfoListJson:
            try:
                existing_attachments = json.loads(guest_attachment.AttachmentInfoListJson)
            except json.JSONDecodeError:
                existing_attachments = []  # Default to empty list if JSON is invalid

        # Add existing attachments to response first
        for existing_attachment in existing_attachments:
            attachments_response.append({
                "uid": existing_attachment.get("UID"),  # UID from existing data
                "attachmentCode": existing_attachment.get("AttachmentCode") or existing_attachment.get("attachmenttCode")  # Handle different key names
            })


        attachments = data['Attachments']
        # This endpoint adds documents to a guest rather than restating the whole set, so
        # the ones already listed for the guest are kept and a name already in that list
        # is given a suffix instead of writing over the document it belongs to
        new_attachments_response, duplicate_image_status = store_guest_attachments(
            guest_id, attachments, retained_names=list(existing_names)
        )
        attachments_response.extend(new_attachments_response)
        add_attachment = bool(new_attachments_response)

        for attachment in attachments:
            attachment["ContentBase64Encoded"] = None  # This will be stored as "null" in JSON

        # print("New Attachments",attachments)
        # print("Existing Attachments",existing_attachments)
        if add_attachment:
            

            # Merge new attachments with existing ones
            merged_attachments = existing_attachments + attachments
            print(json.dumps(merged_attachments))
            # Convert the final list to a JSON string before saving
            guest_attachment.AttachmentInfoListJson = json.dumps(merged_attachments)

            # Commit changes to the database
            db.session.commit()
        

        # Process attachments
        

        
        
        
        
        # guest_attachment.AttachmentInfoListJson ='[{"Id":0,"UID":None,"AttachmentCode":"SekuAaxxG0yq0DiF8fvi3w","Name":"Image_1.jpg","Size":94993,"ContentBase64Encoded":None}]'
        
        checkinguest = CheckinGuest.query.filter(
                                    CheckinGuest.GuestId == guest_id,
                                    CheckinGuest.CheckinId == checkin_id

                                            # Ensure 'IsMainGuest' is used correctly
                                    ).order_by(CheckinGuest.Id.desc()).first()
                            
  
        
        
        guests_response.append({
            "uid": guest_id,
            "guestCode": checkinguest.GuestCode,
            "attachments": attachments_response
        })

        # Step 6: Create Log
        log = Log(
            AddedAt=local_time_str,
            RoomNumber=main_checkin.RoomNumber,
            RequestType='GuestAttachment POST',
            DtcmStatus=-1,
            CidStatus=-1,
            CheckinUID=None,
            PayloadIdentifier=None,
            Error=None,
            CheckinGuestId=checkinguest.Id,
            CheckinId=main_checkin.Id
        )
        db.session.add(log)
        db.session.commit()

        previous_guest_version = GuestVersion.query.filter(
            GuestVersion.CheckinId == main_checkin.Id,
            GuestVersion.CheckinGuestId == checkinguest.Id
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
            CheckoutDate=previous_guest_version.CheckoutDate,
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
            AttachmentInfoListJson=guest_attachment.AttachmentInfoListJson,
            CurrentMainCheckinGuestId=previous_guest_version.CurrentMainCheckinGuestId
        )
        db.session.add(guest_version)
        db.session.commit()

        
        # Prepare the response data
        guests_list = []
        
        guests = Guest.query.filter_by(Id=guest_id).first()
        guest_attachments = GuestAttachment.query.filter_by(GuestId=guests.Id).first()
        
        # guests_list.append({
        #     "uid": guest_id,
        #     "guestCode": checkinguest.GuestCode,
        #     "attachments": guest_attachments.AttachmentInfoListJson if guest_attachments.AttachmentInfoListJson else []
        # })

        # Ensure guest_attachments.AttachmentInfoListJson is a list
        attachments_data = []
        if guest_attachments and guest_attachments.AttachmentInfoListJson:
            try:
                # Parse JSON string into a Python list if it's a string
                if isinstance(guest_attachments.AttachmentInfoListJson, str):
                    attachments_data = json.loads(guest_attachments.AttachmentInfoListJson)
                else:
                    attachments_data = guest_attachments.AttachmentInfoListJson
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")  # Log or handle the error properly

        # Append to guests_list
        guests_list.append({
            "uid": guest_id,
            "guestCode": checkinguest.GuestCode,
            "attachments": [
                {
                    "uid": attachment.get("UID"),  # Extract UID safely
                    "attachmenttCode": attachment.get("AttachmentCode") or attachment.get("attachmenttCode")  # Handle both key variations
                }
                for attachment in attachments_data  # Iterate only if it's a valid list
            ]
        })


        # Construct final response
        response = {
            "CheckinUID": main_checkin.Id,
            "guests": guests_list,
            
            "hasErrors": False,
            "errorMessages": {},
            "MessageType": "GuestAttachmentRequest",
            "ClientUID": data.get("ClientUID", ""),
            "MessageUID":str(uuid.uuid4()),
            "CorrelationUID": data.get("CorrelationUID", ""),
            "Timestamp": local_time_str
        }


        
        return jsonify(response), 201

        

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": str(e)},
            "messageType": "GuestAttachmentRequest",
            "clientUID": data.get('ClientUID'),
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID'),
            # "timestamp": datetime.now(timezone.utc).isoformat()
            "timestamp": local_time_str
        }), 500
    
