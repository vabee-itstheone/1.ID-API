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
from .services import validate_guest
import base64
import json
import tzlocal
import requests
import json
from app.config import Config  # Import your config file
from app.utilities.translation import translate_to_arabic
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

guest_bp = Blueprint('guest', __name__)

@guest_bp.route('/guesttable', methods=['GET'])
def guest():
    data = get_guest_data()
    return jsonify(data)

@guest_bp.route('/guest', methods=['GET'])
def get_guest():
    data = request.json

    establishment_uid = data.get('ClientUID')
    
    # Fetch the current check-in based on CheckinUID
    current_checkin = Checkin.query.filter_by(Id=data.get("CheckinUID")).first()
    
    if not current_checkin:
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "Check-in not found"},
            "messageType": "GuestRequest",
            "clientUID": establishment_uid,
            "messageUID": "error-msg-uid",
            "correlationUID": data.get("CorrelationUID", ""),
            "timestamp": local_time_str
        }), 404
    
    

    # Fetch all guests related to the current check-in
    # guest_versions = GuestVersion.query.filter_by(CheckinId=current_checkin.Id).all()
    checkinguests = CheckinGuest.query.filter_by(CheckinId=current_checkin.Id).all()

    # Prepare the response data
    guests_list = []
    for guest in checkinguests:
        
        guests = Guest.query.filter_by(Id=guest.GuestId).first()
        guest_attachments = GuestAttachment.query.filter_by(GuestId=guests.Id).first()
        guest_attachment = DocumentType.query.filter_by(Id=guest_attachments.DocumentTypeId).first()

        guests_list.append({
            "uid": guests.Id,
            "guestCode": guest.GuestCode,
            "isMainGuest": guest.IsMainGuest,
            "attachmentType": guest_attachment.Type,
            "documentNumber": guests.DocumentNumber,
            "attachments": guest_attachments.AttachmentInfoListJson if guest_attachments.AttachmentInfoListJson else []
        })

    # Construct final response
    response = {
        "guests": guests_list,
        "requestMessageID": str(uuid.uuid4()),
        "hasErrors": False,
        "errorMessages": {},
        "messageType": "GuestRequest",
        "clientUID": data.get("ClientUID", ""),
        "messageUID": str(uuid.uuid4()),
        "correlationUID": data.get("CorrelationUID", ""),
        "timestamp": local_time_str
    }

    return jsonify(response)




@guest_bp.route('/guest', methods=['POST'])
def create_guestcheckin():
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
                "messageType": "GuestResponse",
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
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # This endpoint carries one guest under "GuestInfo", not a "Guests" list.
        # Reading "Guests" made the loop body dead code, so a guest added or edited
        # after check-in skipped every field-format check that the identical guest
        # inside POST /checkin's Guests[] is held to.
        guests1 = data.get("Guests") or []
        guest_info = data.get("GuestInfo")
        if guest_info:
            guests1 = [guest_info]

        all_errors = []
        for guest1 in guests1:
            errors = validate_guest(guest1)
            if errors:
                all_errors.append({"GuestCode": guest1.get("GuestCode", ""), "errors": errors})

        if all_errors:
            return jsonify({
                    "hasErrors": True,
                    "errorMessages": all_errors,
                    "messageType": "CheckinResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
       
        guests_response = []
        # Step 3: Create or Update Guest
        # guest_data = data['Guests'][0]  # Assuming only one guest for simplicity
        

        if not data.get('GuestInfo'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50010 Guest is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        guest_data = data['GuestInfo']
        # Validation 5000454: Guest invalid first name
        guest_code = guest_data.get('GuestCode')
        if not guest_code or not isinstance(guest_code, str) or len(guest_code) > 75:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50001 Guest invalid Guest Code"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 50001: Guest invalid first name
        first_name = guest_data.get('FirstName')
        if not first_name or not isinstance(first_name, str):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50001 Guest invalid first name"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50002: Guest invalid last name
        last_name = guest_data.get('LastName')
        if not last_name or not isinstance(last_name, str):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50002 Guest invalid last name"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50011: Guest mobile number is invalid
        mobile_number = guest_data.get('Mobile')
        # if not mobile_number or not re.match(r'^\d{10}$', mobile_number):
        if not mobile_number:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50011 Guest mobile number is invalid"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50005: Guest invalid nationality
        nationality_code = guest_data.get('NationalityCode')
        if not nationality_code or not Country.query.filter_by(TwoCode=nationality_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50005 Guest invalid nationality"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400


        # Validation 50006: Guest invalid residence country
        residence_country_code = guest_data.get('ResidenceCountryCode')
        if not residence_country_code or not Country.query.filter_by(TwoCode=residence_country_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50006 Guest invalid residence country"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        is_main_guest = guest_data.get('IsMainGuest', False)
        relationship_code = guest_data.get('RelationshipCode')


        if not is_main_guest and not Relationship.query.filter_by(DtcmCode=relationship_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50009 Guest invalid relationship: Relationship code does not exist"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

            # Validation 50007: Guest invalid birth date
        birth_date = guest_data.get('BirthDate')
        try:
            birth_date = datetime.fromisoformat(birth_date)
            current_datetime = datetime.now()
            if birth_date > current_datetime :
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50007 Guest invalid birth date"},
                    "messageType": "GuestResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50007 Guest invalid birth date"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

            # Validation 50013: Birth Place is not specified
        birth_place = guest_data.get('BirthPlace')
        if not birth_place:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50013 Birth Place is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50008: Guest invalid visit purpose
        visit_purpose_code = guest_data.get('VisitPurposeCode')
        if not visit_purpose_code or not VisitPurpose.query.filter_by(DtcmCode=visit_purpose_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50008 Guest invalid visit purpose"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50014: Guest Checkin date is before Checkin date
        # checkin_date1 = datetime.fromisoformat(main_checkin.CheckinDate)
        guest_checkin_date = datetime.fromisoformat(guest_data['CheckinDateTime'])
        # print(checkin_date1)
        # print(guest_checkin_date)
        
        if guest_checkin_date < main_checkin.CheckinDate:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50014 Guest Checkin date is before Checkin date"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50015: Guest checkin date time should not be in future

        guest_checkin_date1 = guest_data['CheckinDateTime']
        guest_checkin_date1 = datetime.fromisoformat(guest_checkin_date1)
        # print(local_time)
        # print(current_datetime)
        # print(guest_checkin_date1)
        if guest_checkin_date1 > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50015 Guest checkin date time should not be in future"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60001: Attachment is not specified
        if 'Attachments' not in guest_data or not guest_data['Attachments']:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60001 Attachment is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        document_number = guest_data.get('DocumentNumber')
        

        # Validation 60006: Attachment document number is invalid

        if not document_number:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60006 Attachment document number is invalid"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60007: Attachment Type is not specified
        document_type = guest_data.get('AttachmentTypeCode')
            
        if not document_type or not DocumentType.query.filter_by(DtcmCode=document_type).first() :
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60007 Attachment Type is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60013: Attachment issue date is not specified
    
    
        issue_date = guest_data.get('IssueDate')
        if not issue_date:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60013 Attachment issue date is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        issue_date1 = datetime.fromisoformat(issue_date)

        # Validation 60008: Attachment issue date can't be in the future
        
        if issue_date1 > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60008 Attachment issue date can't be in the future"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        expiry_date = guest_data.get('ExpiryDate')
        
        if not expiry_date:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60011 Attachment expiry date is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        expiry_date1 = datetime.fromisoformat(expiry_date)

        if issue_date1 >= expiry_date1:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60009 Attachment issue date should be before expiry date"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

            
        if expiry_date1 < current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60011 Attachment is expired"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
                

    

        # Validation 60010: Attachment issue country is not specified
        issue_country_code = guest_data.get('IssueCountryCode')
        if not issue_country_code or not Country.query.filter_by(TwoCode=issue_country_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60010 Attachment issue country is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # # Validation 60012: Attachment issue emirate is not specified
        emirate_code = guest_data.get('EmirateCode')

        if (issue_country_code == 'AE')  and not Emirate.query.filter_by(DtcmCode=emirate_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60012 Attachment issue emirate is not specified"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60004: Attachment should not exceed 200 KB in size
        
        for attachment in guest_data['Attachments']:
            attachement_code = attachment.get('AttachmentCode')
            if 'ContentBase64Encoded' in attachment:
                attachment_size = len(attachment['ContentBase64Encoded']) * 3 / 4  # Base64 size calculation
                print(attachement_code , attachment_size)
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
                
                # Check if "other" exists in AccessibilityTypes and validate OtherAccessibilityType
        # accessibility_types = guest_data.get("AccessibilityTypes", [])
        accessibility_types = guest_data.get("AccessibilityTypes") or []

        # other_accessibility_type = guest_data.get("OtherAccessibilityType", "").strip()
        other_accessibility_type = (guest_data.get("OtherAccessibilityType") or "").strip()


        if any(item.get("Code") == "other" for item in accessibility_types) and not other_accessibility_type:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60008 Other Accessibility Type must be specified when 'other' is selected"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
                
        # Validation 50016: Guest already exist
        already_exist_guest =   GuestVersion.query.filter(GuestVersion.CheckinId == main_checkin.Id, GuestVersion.DocumentNumber == guest_data['DocumentNumber']).order_by(GuestVersion.LogId.desc()).first()
        print(already_exist_guest)
        if already_exist_guest:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50016 Guest already exist"},
                "messageType": "GuestResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

    
    # # Validation 60012: Attachment issue emirate is not specified
    # for guest_data in data['Guests']:
    #     for attachment in guest_data['Attachments']:
    #         if not attachment.get('IssueEmirateCode'):
    #             return jsonify({
    #                 "hasErrors": True,
    #                 "errorMessages": {"general": "60012 Attachment issue emirate is not specified"},
    #                 "messageType": "CheckinResponse",
    #                 "clientUID": data.get('ClientUID', 'Establishment101'),
    #                 "messageUID": str(uuid.uuid4()),
    #                 "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
    #                 "timestamp": datetime.utcnow().isoformat() + "+04:00"
    #             }), 400

    # # Validation 60013: Attachment issue date is not specified
    # for guest_data in data['Guests']:
    #     for attachment in guest_data['Attachments']:
    #         if not attachment.get('IssueDate'):
    #             return jsonify({
    #                 "hasErrors": True,
    #                 "errorMessages": {"general": "60013 Attachment issue date is not specified"},
    #                 "messageType": "CheckinResponse",
    #                 "clientUID": data.get('ClientUID', 'Establishment101'),
    #                 "messageUID": str(uuid.uuid4()),
    #                 "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
    #                 "timestamp": datetime.utcnow().isoformat() + "+04:00"
    #             }), 400

    


        nationality_code = guest_data.get('NationalityCode')
        # issue_country_code = guest_data.get('IssueCountryCode')
        nationality_country = Country.query.filter_by(TwoCode=nationality_code).first()

        emirate_code = guest_data.get('EmirateCode')
        emirate = Emirate.query.filter_by(DtcmCode=emirate_code).first()
        # ArabicFirstName = translator.translate(guest_data.get('FirstName'), dest='ar').text
        # print(f"ArabicFirstName: {ArabicFirstName}")

        mobile_code = guest_data['ResidenceCountryCode'] 
        mobile_code = Country.query.filter_by(TwoCode=mobile_code).first()

        if guest_data['GenderCode'] == "male":
                gender_code = "Male"
        elif guest_data['GenderCode'] == "female":
            gender_code = "Female"
        else:
            gender_code = guest_data['GenderCode']

        if guest_data.get('RequiresAccessibility') is True:
            # requires_accessibility_Json = json.dumps({
            #     "AccessibilityTypes": guest_data.get('AccessibilityTypes', []),
            #     "OtherAccessibility": guest_data.get('OtherAccessibility', "")

            
            accessibility_types = [item["Code"] for item in guest_data.get('AccessibilityTypes', [])]

            requires_accessibility_Json = json.dumps({
                "AccessibilityTypes": accessibility_types,  # Extract only the "Code" values
                "OtherAccessibility": guest_data.get("OtherAccessibilityType", "")
            
            })
        else:
            requires_accessibility_Json = None  # Or an empty JSON string "{}"


        guest = Guest.query.filter_by(DocumentNumber=guest_data['DocumentNumber']).first()
        if not guest:
            guest = Guest()
            db.session.add(guest)

        guest.FirstName = guest_data['FirstName']
        guest.LastName = guest_data['LastName']
        
        # guest.ArabicFirstName = translator.translate(guest.FirstName, dest='ar').text
        # guest.ArabicLastName = translator.translate(guest.LastName, dest='ar').text

        guest.ArabicFirstName = translate_to_arabic(guest.FirstName)
        guest.ArabicLastName = translate_to_arabic(guest.LastName)
        
        guest.Gender = gender_code
        guest.BirthDate = datetime.fromisoformat(guest_data['BirthDate'])
        guest.ResidenceCountryPhone = guest_data['ResidenceCountryPhone']
        guest.MobileCode = mobile_code.MobileCode
        guest.MobileNumber = guest_data['Mobile']
        guest.Email = guest_data['Email']
        guest.RequiresAccessibilityJson = requires_accessibility_Json
        guest.DocumentNumber = guest_data['DocumentNumber']
        # Set NationalityId based on NationalityCode
        # Query by TwoCode
        guest.NationalityId = nationality_country.Id
        
        # guest.EmirateId = guest_data.get('EmirateId')
        if emirate == None: 
            guest.EmirateId = None
        else:
            guest.EmirateId = emirate.Id

        guest.BirthPlaceName = guest_data['BirthPlace']
        guest.ResidenceCountryTwoCode = guest_data['ResidenceCountryCode']

        

        db.session.commit()

        
        # The guest is left holding exactly the images this request sent
        attachments_response, duplicate_image_status = store_guest_attachments(
            guest.Id, guest_data.get('Attachments', [])
        )


        # Process attachments
        

        document_type_code = guest_data.get('AttachmentTypeCode')
        document_type = DocumentType.query.filter_by(DtcmCode=document_type_code).first()  # Query by TwoCode
        issue_country_code = guest_data.get('IssueCountryCode')
        issue_country = Country.query.filter_by(TwoCode=issue_country_code).first()  # Query by TwoCode

        # Step 4: Create or Update GuestAttachment
        guest_attachment = GuestAttachment.query.filter_by(GuestId=guest.Id).first()
        if not guest_attachment:
            guest_attachment = GuestAttachment()
            db.session.add(guest_attachment)

        

        guest_attachment.ExpiryDate = datetime.fromisoformat(guest_data['ExpiryDate'])
        guest_attachment.IssueDate = datetime.fromisoformat(guest_data['IssueDate'])
        
        # guest_attachment.AttachmentInfoListJson ='[{"Id":0,"UID":None,"AttachmentCode":"SekuAaxxG0yq0DiF8fvi3w","Name":"Image_1.jpg","Size":94993,"ContentBase64Encoded":None}]'
        

        attachments = guest_data.get("Attachments", [])

        # Modify the attachments list to set ContentBase64Encoded to None
        for attachment in attachments:
            attachment["ContentBase64Encoded"] = None  # This will be stored as "null" in JSON

        # Convert the modified list to a JSON string before saving. Every attachment that was
        # sent is listed, including the ones whose content was already stored on disk
        guest_attachment.AttachmentInfoListJson = json.dumps(attachments)
        # guest_attachment.DocumentTypeId = guest_data['DocumentTypeId']
        
        guest_attachment.DocumentTypeId = document_type.Id
        
        
        guest_attachment.IssueCountryId = issue_country.Id
        # guest_attachment.IssueCountryId = guest_data['IssueCountryId']
        # guest_attachment.AttachmentInfoListJson = json.dumps(guest_data.get('Attachments', []))

        # guest_attachment.AttachmentInfoListJson = str(guest_data['Attachments'])
        # # guest_attachment.DocumentTypeId = guest_data['DocumentTypeId']

        # # emirate_code = guest_data.get('EmirateCode')
        # # emirate = Emirate.query.filter_by(DtcmCode=emirate_code).first()
        # # guest.EmirateId = emirate.Id

        # # Set DocumentTypeId
        # # document_type_code = guest_data.get('AttachmentTypeCode')
        # # if document_type_code:
        # #     document_type = DocumentType.query.filter_by(DtcmCode=document_type_code).first()
        # #     if document_type:
        # #         guest_attachment.DocumentTypeId = document_type.Id
        # #     else:
        # #         # Log a warning if no matching document type is found
        # #         print(f"Warning: DocumentType with DtcmCode '{document_type_code}' not found. Using default value.")
        # #         guest_attachment.DocumentTypeId = 1  # Default value
        # # else:
        # #     # Log a warning if AttachmentTypeCode is missing
        # #     print("Warning: AttachmentTypeCode is missing in guest_data. Using default value.")
        # #     guest_attachment.DocumentTypeId = 1  # Default value

        # # # Set IssueCountryId
        # # issue_country_code = guest_data.get('IssueCountryCode')
        # # if issue_country_code:
        # #     issue_country = Country.query.filter_by(TwoCode=issue_country_code).first()
        # #     if issue_country:
        # #         guest_attachment.IssueCountryId = issue_country.Id
        # #     else:
        # #         # Log a warning if no matching country is found
        # #         print(f"Warning: Country with TwoCode '{issue_country_code}' not found. Using default value.")
        # #         guest_attachment.IssueCountryId = 1  # Default value
        # # else:
        # #     # Log a warning if IssueCountryCode is missing
        # #     print("Warning: IssueCountryCode is missing in guest_data. Using default value.")
        # #     guest_attachment.IssueCountryId = 1  # Default value

        # # guest_attachment.IssueCountryId = guest_data['IssueCountryId']
        
        guest_attachment.GuestId = guest.Id

        # # Debugging: Print values before committing
        # print(f"DocumentTypeId: {guest_attachment.DocumentTypeId}")
        # print(f"IssueCountryId: {guest_attachment.IssueCountryId}")
        # print(f"GuestId: {guest_attachment.GuestId}")

        db.session.commit()

        # Step 5: Create CheckinGuest
        visit_purpose_code = guest_data.get('VisitPurposeCode')
        visit_purpose = VisitPurpose.query.filter_by(DtcmCode=visit_purpose_code).first()
        

        checkin_guest = CheckinGuest(
            CheckinDate=datetime.fromisoformat(guest_data['CheckinDateTime']),
            IsMainGuest=guest_data['IsMainGuest'],
            GuestCode=guest_data.get('GuestCode'),
            GuestUID=None,
            CheckoutDate=None,
            IsFirstGuest=True,
            GuestId=guest.Id,
            CheckinId=main_checkin.Id,
            RelationshipName=guest_data.get('RelationshipCode'),
            EscortTypeId=2,
            VisitPurposeId=visit_purpose.Id
        )
        db.session.add(checkin_guest)
        db.session.commit()

        guests_response.append({
            "uid": guest.Id,
            "guestCode": guest_data.get('GuestCode'),
            "attachments": attachments_response
        })

        # Step 6: Create Log
        log = Log(
            AddedAt=local_time_str,
            RoomNumber=main_checkin.RoomNumber,
            RequestType='Guest POST',
            DtcmStatus=-1,
            CidStatus=-1,
            CheckinUID=None,
            PayloadIdentifier=None,
            Error=None,
            CheckinGuestId=checkin_guest.Id,
            CheckinId=main_checkin.Id
        )
        db.session.add(log)
        db.session.commit()

        is_main_guest = guest_data.get('IsMainGuest', False)
        relationship_code = guest_data.get('RelationshipCode')
        relationship = None 
        if is_main_guest:
            current_mainguest_checkinId = checkin_guest
        elif not is_main_guest:
            
            current_mainguest_checkinId = CheckinGuest.query.filter(
                            CheckinGuest.CheckinId == main_checkin.Id,
                            CheckinGuest.IsMainGuest == True
                            # Ensure 'IsMainGuest' is used correctly
                        ).order_by(CheckinGuest.Id.desc()).first()
            relationship = Relationship.query.filter_by(DtcmCode=relationship_code).first().Id
        print(current_mainguest_checkinId)
            
        # Step 7: Create GuestVersion
        guest_version = GuestVersion(
            FirstName=guest.FirstName,
            LastName=guest.LastName,
            ArabicFirstName=guest.ArabicFirstName,
            ArabicLastName=guest.ArabicLastName,
            Gender=guest.Gender,
            BirthDate=guest.BirthDate,
            ResidenceCountryPhone=guest.ResidenceCountryPhone,
            MobileCode=guest.MobileCode,
            MobileNumber=guest.MobileNumber,
            Email=guest.Email,
            RequiresAccessibilityJson=guest.RequiresAccessibilityJson,
            CheckinId=main_checkin.Id,
            DocumentNumber=guest.DocumentNumber,
            NationalityId=guest.NationalityId,
            EmirateId=guest.EmirateId,
            CheckinDate=checkin_guest.CheckinDate,
            CheckoutDate=checkin_guest.CheckoutDate,
            IsMainGuest=checkin_guest.IsMainGuest,
            GuestCode=checkin_guest.GuestCode,
            GuestUID=checkin_guest.GuestUID,
            GuestId=guest.Id,
            RelationshipId=relationship,
            EscortTypeId=checkin_guest.EscortTypeId,
            VisitPurposeId=checkin_guest.VisitPurposeId,
            ExpiryDate=guest_attachment.ExpiryDate,
            IssueDate=guest_attachment.IssueDate,
            DocumentTypeId=guest_attachment.DocumentTypeId,
            LogId=log.Id,
            CheckinGuestId=checkin_guest.Id,
            BirthPlaceName=guest.BirthPlaceName,
            ResidenceCountryTwoCode=guest.ResidenceCountryTwoCode,
            IssueCountryTwoCode=Country.query.get(guest_attachment.IssueCountryId).TwoCode,  # Assuming IssueCountryId maps to TwoCode
            AttachmentInfoListJson=guest_attachment.AttachmentInfoListJson,
            CurrentMainCheckinGuestId=current_mainguest_checkinId.Id
        )
        db.session.add(guest_version)
        db.session.commit()

        


        response = {
                    "CheckinUID": main_checkin.Id,
                    "guests": guests_response,
                    "requestMessageID": log.Id,
                    "hasErrors": False,
                    "errorMessages": {},
                    "messageType": "GuestResponse",
                    "clientUID": data.get('ClientUID'),
                    "messageUID": str(uuid.uuid4()),  # Generate a unique message UID
                    "correlationUID": data.get('CorrelationUID'),
                    "timestamp": local_time_str
                    
                }
        return jsonify(response), 201

        

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": str(e)},
            "messageType": "GuestResponse",
            "clientUID": data.get('ClientUID'),
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID'),
            # "timestamp": datetime.now(timezone.utc).isoformat()
            "timestamp": local_time_str
        }), 500
    


@guest_bp.route('/guest', methods=['PUT'])
def update_guestcheckin():
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
                "messageType": "GuestResponse",
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
                "messageType": "CheckinUpdateResponse",
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
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        # This endpoint carries one guest under "GuestInfo", not a "Guests" list.
        # Reading "Guests" made the loop body dead code, so a guest added or edited
        # after check-in skipped every field-format check that the identical guest
        # inside POST /checkin's Guests[] is held to.
        guests1 = data.get("Guests") or []
        guest_info = data.get("GuestInfo")
        if guest_info:
            guests1 = [guest_info]

        all_errors = []
        for guest1 in guests1:
            errors = validate_guest(guest1)
            if errors:
                all_errors.append({"GuestCode": guest1.get("GuestCode", ""), "errors": errors})

        if all_errors:
            return jsonify({
                    "hasErrors": True,
                    "errorMessages": all_errors,
                    "messageType": "CheckinResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
        
        
       
        guests_response = []
        # Step 3: Create or Update Guest
        # guest_data = data['Guests'][0]  # Assuming only one guest for simplicity
        

        if not data.get('GuestInfo'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50010 Guest is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        guest_data = data['GuestInfo']
        # Validation 50001: Guest invalid first name
        guest_code = guest_data.get('GuestCode')
        if not guest_code or not isinstance(guest_code, str) or len(guest_code) > 75:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50001 Guest invalid Guest Code"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 50001: Guest invalid first name
        first_name = guest_data.get('FirstName')
        if not first_name or not isinstance(first_name, str):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50001 Guest invalid first name"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50002: Guest invalid last name
        last_name = guest_data.get('LastName')
        if not last_name or not isinstance(last_name, str):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50002 Guest invalid last name"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50011: Guest mobile number is invalid
        mobile_number = guest_data.get('Mobile')
        # if not mobile_number or not re.match(r'^\d{10}$', mobile_number):
        if not mobile_number:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50011 Guest mobile number is invalid"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50005: Guest invalid nationality
        nationality_code = guest_data.get('NationalityCode')
        if not nationality_code or not Country.query.filter_by(TwoCode=nationality_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50005 Guest invalid nationality"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400


        # Validation 50006: Guest invalid residence country
        residence_country_code = guest_data.get('ResidenceCountryCode')
        if not residence_country_code or not Country.query.filter_by(TwoCode=residence_country_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50006 Guest invalid residence country"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        is_main_guest = guest_data.get('IsMainGuest', False)
        relationship_code = guest_data.get('RelationshipCode')


        if not is_main_guest and not Relationship.query.filter_by(DtcmCode=relationship_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50009 Guest invalid relationship: Relationship code does not exist"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

            # Validation 50007: Guest invalid birth date
        birth_date = guest_data.get('BirthDate')
        try:
            birth_date = datetime.fromisoformat(birth_date)
            current_datetime = datetime.now()
            if birth_date > current_datetime :
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50007 Guest invalid birth date"},
                    "messageType": "CheckinResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50007 Guest invalid birth date"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

            # Validation 50013: Birth Place is not specified
        birth_place = guest_data.get('BirthPlace')
        if not birth_place:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50013 Birth Place is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50008: Guest invalid visit purpose
        visit_purpose_code = guest_data.get('VisitPurposeCode')
        if not visit_purpose_code or not VisitPurpose.query.filter_by(DtcmCode=visit_purpose_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50008 Guest invalid visit purpose"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50014: Guest Checkin date is before Checkin date
        # checkin_date1 = datetime.fromisoformat(main_checkin.CheckinDate)
        guest_checkin_date = datetime.fromisoformat(guest_data['CheckinDateTime'])
        # print(checkin_date1)
        # print(guest_checkin_date)
        
        if guest_checkin_date < main_checkin.CheckinDate:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50014 Guest Checkin date is before Checkin date"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 50015: Guest checkin date time should not be in future

        guest_checkin_date1 = guest_data['CheckinDateTime']
        guest_checkin_date1 = datetime.fromisoformat(guest_checkin_date1)
        # print(local_time)
        # print(current_datetime)
        # print(guest_checkin_date1)
        if guest_checkin_date1 > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "50015 Guest checkin date time should not be in future"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60001: Attachment is not specified
        if 'Attachments' not in guest_data or not guest_data['Attachments']:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60001 Attachment is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        document_number = guest_data.get('DocumentNumber')
        

        # Validation 60006: Attachment document number is invalid

        if not document_number:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60006 Attachment document number is invalid"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60007: Attachment Type is not specified
        document_type = guest_data.get('AttachmentTypeCode')
            
        if not document_type or not DocumentType.query.filter_by(DtcmCode=document_type).first() :
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60007 Attachment Type is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60013: Attachment issue date is not specified
    
    
        issue_date = guest_data.get('IssueDate')
        if not issue_date:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60013 Attachment issue date is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        issue_date1 = datetime.fromisoformat(issue_date)

        # Validation 60008: Attachment issue date can't be in the future
        
        if issue_date1 > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60008 Attachment issue date can't be in the future"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        expiry_date = guest_data.get('ExpiryDate')
        
        if not expiry_date:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60011 Attachment expiry date is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        expiry_date1 = datetime.fromisoformat(expiry_date)

        if issue_date1 >= expiry_date1:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60009 Attachment issue date should be before expiry date"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

            
        if expiry_date1 < current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60011 Attachment is expired"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
                

    

        # Validation 60010: Attachment issue country is not specified
        issue_country_code = guest_data.get('IssueCountryCode')
        if not issue_country_code or not Country.query.filter_by(TwoCode=issue_country_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60010 Attachment issue country is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # # Validation 60012: Attachment issue emirate is not specified
        emirate_code = guest_data.get('EmirateCode')

        if (issue_country_code == 'AE')  and not Emirate.query.filter_by(DtcmCode=emirate_code).first():
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60012 Attachment issue emirate is not specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 60004: Attachment should not exceed 200 KB in size
        
        for attachment in guest_data['Attachments']:
            attachement_code = attachment.get('AttachmentCode')
            if 'ContentBase64Encoded' in attachment:
                attachment_size = len(attachment['ContentBase64Encoded']) * 3 / 4  # Base64 size calculation
                print(attachement_code , attachment_size)
                if attachment_size > 200 * 1024:  # 200 KB
                    return jsonify({
                        "hasErrors": True,
                        "errorMessages": {"general": "60004 Attachment should not exceed 200 KB in size"},
                        "messageType": "CheckinResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400
                

        # Check if "other" exists in AccessibilityTypes and validate OtherAccessibilityType
        # accessibility_types = guest_data.get("AccessibilityTypes", [])
        accessibility_types = guest_data.get("AccessibilityTypes") or []

        #other_accessibility_type = guest_data.get("OtherAccessibilityType", "").strip()
        other_accessibility_type = (guest_data.get("OtherAccessibilityType") or "").strip()


        if any(item.get("Code") == "other" for item in accessibility_types) and not other_accessibility_type:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "60008 Other Accessibility Type must be specified when 'other' is selected"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
                
        # Validation 50016: Guest already exist
        # already_exist_guest =   GuestVersion.query.filter(GuestVersion.CheckinId == main_checkin.Id, GuestVersion.DocumentNumber == guest_data['DocumentNumber']).order_by(GuestVersion.LogId.desc()).first()
        # print(already_exist_guest)
        # if already_exist_guest:
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "50016 Guest already exist"},
        #         "messageType": "GuestResponse",
        #         "clientUID": establishment_uid,
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": local_time_str
        #     }), 400

    
    # # Validation 60012: Attachment issue emirate is not specified
    # for guest_data in data['Guests']:
    #     for attachment in guest_data['Attachments']:
    #         if not attachment.get('IssueEmirateCode'):
    #             return jsonify({
    #                 "hasErrors": True,
    #                 "errorMessages": {"general": "60012 Attachment issue emirate is not specified"},
    #                 "messageType": "CheckinResponse",
    #                 "clientUID": data.get('ClientUID', 'Establishment101'),
    #                 "messageUID": str(uuid.uuid4()),
    #                 "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
    #                 "timestamp": datetime.utcnow().isoformat() + "+04:00"
    #             }), 400

    # # Validation 60013: Attachment issue date is not specified
    # for guest_data in data['Guests']:
    #     for attachment in guest_data['Attachments']:
    #         if not attachment.get('IssueDate'):
    #             return jsonify({
    #                 "hasErrors": True,
    #                 "errorMessages": {"general": "60013 Attachment issue date is not specified"},
    #                 "messageType": "CheckinResponse",
    #                 "clientUID": data.get('ClientUID', 'Establishment101'),
    #                 "messageUID": str(uuid.uuid4()),
    #                 "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
    #                 "timestamp": datetime.utcnow().isoformat() + "+04:00"
    #             }), 400

    


        nationality_code = guest_data.get('NationalityCode')
        # issue_country_code = guest_data.get('IssueCountryCode')
        nationality_country = Country.query.filter_by(TwoCode=nationality_code).first()

        emirate_code = guest_data.get('EmirateCode')
        emirate = Emirate.query.filter_by(DtcmCode=emirate_code).first()
        # ArabicFirstName = translator.translate(guest_data.get('FirstName'), dest='ar').text
        # print(f"ArabicFirstName: {ArabicFirstName}")
        mobile_code = guest_data['ResidenceCountryCode'] 
        mobile_code = Country.query.filter_by(TwoCode=mobile_code).first()

        if guest_data['GenderCode'] == "male":
                gender_code = "Male"
        elif guest_data['GenderCode'] == "female":
            gender_code = "Female"
        else:
            gender_code = guest_data['GenderCode']

        # Assigning RequiresAccessibilityJson
        if guest_data.get('RequiresAccessibility') is True:
            # requires_accessibility_Json = json.dumps({
            #     "AccessibilityTypes": guest_data.get('AccessibilityTypes', []),
            #     "OtherAccessibility": guest_data.get('OtherAccessibility', "")

            
            accessibility_types = [item["Code"] for item in guest_data.get('AccessibilityTypes', [])]

            requires_accessibility_Json = json.dumps({
                "AccessibilityTypes": accessibility_types,  # Extract only the "Code" values
                "OtherAccessibility": guest_data.get("OtherAccessibilityType", "")
            
            })
        else:
            requires_accessibility_Json = None  # Or an empty JSON string "{}"

        # Locate the guest this edit is about. UID is the primary key and is the
        # most precise handle, but the caller does not always have it, so fall
        # back to the document number - the same key every other write path
        # matches on. Without the fallback an edit sent with "UID": null created a
        # detached Guest that was never added to the session, so guest.Id stayed
        # None and the guestattachment insert failed on a NULL GuestId.
        guest = None
        guest_uid = guest_data.get('UID')
        if guest_uid:
            guest = Guest.query.filter_by(Id=guest_uid).first()
        if not guest:
            guest = Guest.query.filter_by(
                DocumentNumber=guest_data['DocumentNumber']
            ).first()
        if not guest:
            guest = Guest()
            db.session.add(guest)

        guest.FirstName = guest_data['FirstName']
        guest.LastName = guest_data['LastName']
        
        # guest.ArabicFirstName = translator.translate(guest.FirstName, dest='ar').text
        # guest.ArabicLastName = translator.translate(guest.LastName, dest='ar').text
        guest.ArabicFirstName = translate_to_arabic(guest.FirstName)
        guest.ArabicLastName = translate_to_arabic(guest.LastName)
        
        guest.Gender = gender_code
        guest.BirthDate = datetime.fromisoformat(guest_data['BirthDate'])
        guest.ResidenceCountryPhone = guest_data['ResidenceCountryPhone']
        guest.MobileCode = mobile_code.MobileCode
        guest.MobileNumber = guest_data['Mobile']
        guest.Email = guest_data['Email']
        
        guest.RequiresAccessibilityJson = requires_accessibility_Json
        guest.DocumentNumber = guest_data['DocumentNumber']
        # Set NationalityId based on NationalityCode
        # Query by TwoCode
        guest.NationalityId = nationality_country.Id
        
        # guest.EmirateId = guest_data.get('EmirateId')
        if emirate == None: 
            guest.EmirateId = None
        else:
            guest.EmirateId = emirate.Id

        guest.BirthPlaceName = guest_data['BirthPlace']
        guest.ResidenceCountryTwoCode = guest_data['ResidenceCountryCode']

        

        db.session.commit()

        # The guest is left holding exactly the images this request sent
        attachments_response, duplicate_image_status = store_guest_attachments(
            guest.Id, guest_data.get('Attachments', [])
        )


        # Process attachments
        

        document_type_code = guest_data.get('AttachmentTypeCode')
        document_type = DocumentType.query.filter_by(DtcmCode=document_type_code).first()  # Query by TwoCode
        issue_country_code = guest_data.get('IssueCountryCode')
        issue_country = Country.query.filter_by(TwoCode=issue_country_code).first()  # Query by TwoCode

        # Step 4: Create or Update GuestAttachment
        guest_attachment = GuestAttachment.query.filter_by(GuestId=guest.Id).first()
        if not guest_attachment:
            guest_attachment = GuestAttachment()
            db.session.add(guest_attachment)

        

        guest_attachment.ExpiryDate = datetime.fromisoformat(guest_data['ExpiryDate'])
        guest_attachment.IssueDate = datetime.fromisoformat(guest_data['IssueDate'])
        
        # guest_attachment.AttachmentInfoListJson ='[{"Id":0,"UID":None,"AttachmentCode":"SekuAaxxG0yq0DiF8fvi3w","Name":"Image_1.jpg","Size":94993,"ContentBase64Encoded":None}]'
        

        attachments = guest_data.get("Attachments", [])

        # Modify the attachments list to set ContentBase64Encoded to None
        for attachment in attachments:
            attachment["ContentBase64Encoded"] = None  # This will be stored as "null" in JSON

        # Convert the modified list to a JSON string before saving. Every attachment that was
        # sent is listed, including the ones whose content was already stored on disk
        guest_attachment.AttachmentInfoListJson = json.dumps(attachments)
        print("guest_attachment.AttachmentInfoListJson", duplicate_image_status, guest_attachment.AttachmentInfoListJson)
        # guest_attachment.DocumentTypeId = guest_data['DocumentTypeId']
        
        guest_attachment.DocumentTypeId = document_type.Id
        
        
        guest_attachment.IssueCountryId = issue_country.Id
        # guest_attachment.IssueCountryId = guest_data['IssueCountryId']
        # guest_attachment.AttachmentInfoListJson = json.dumps(guest_data.get('Attachments', []))

        # guest_attachment.AttachmentInfoListJson = str(guest_data['Attachments'])
        # # guest_attachment.DocumentTypeId = guest_data['DocumentTypeId']

        # # emirate_code = guest_data.get('EmirateCode')
        # # emirate = Emirate.query.filter_by(DtcmCode=emirate_code).first()
        # # guest.EmirateId = emirate.Id

        # # Set DocumentTypeId
        # # document_type_code = guest_data.get('AttachmentTypeCode')
        # # if document_type_code:
        # #     document_type = DocumentType.query.filter_by(DtcmCode=document_type_code).first()
        # #     if document_type:
        # #         guest_attachment.DocumentTypeId = document_type.Id
        # #     else:
        # #         # Log a warning if no matching document type is found
        # #         print(f"Warning: DocumentType with DtcmCode '{document_type_code}' not found. Using default value.")
        # #         guest_attachment.DocumentTypeId = 1  # Default value
        # # else:
        # #     # Log a warning if AttachmentTypeCode is missing
        # #     print("Warning: AttachmentTypeCode is missing in guest_data. Using default value.")
        # #     guest_attachment.DocumentTypeId = 1  # Default value

        # # # Set IssueCountryId
        # # issue_country_code = guest_data.get('IssueCountryCode')
        # # if issue_country_code:
        # #     issue_country = Country.query.filter_by(TwoCode=issue_country_code).first()
        # #     if issue_country:
        # #         guest_attachment.IssueCountryId = issue_country.Id
        # #     else:
        # #         # Log a warning if no matching country is found
        # #         print(f"Warning: Country with TwoCode '{issue_country_code}' not found. Using default value.")
        # #         guest_attachment.IssueCountryId = 1  # Default value
        # # else:
        # #     # Log a warning if IssueCountryCode is missing
        # #     print("Warning: IssueCountryCode is missing in guest_data. Using default value.")
        # #     guest_attachment.IssueCountryId = 1  # Default value

        # # guest_attachment.IssueCountryId = guest_data['IssueCountryId']
        
        guest_attachment.GuestId = guest.Id

        # # Debugging: Print values before committing
        # print(f"DocumentTypeId: {guest_attachment.DocumentTypeId}")
        # print(f"IssueCountryId: {guest_attachment.IssueCountryId}")
        # print(f"GuestId: {guest_attachment.GuestId}")

        db.session.commit()

        # Step 5: Create CheckinGuest
        visit_purpose_code = guest_data.get('VisitPurposeCode')
        visit_purpose = VisitPurpose.query.filter_by(DtcmCode=visit_purpose_code).first()
        
        checkinguest = CheckinGuest.query.filter(
                            CheckinGuest.GuestId == guest.Id
                                    # Ensure 'IsMainGuest' is used correctly
                            ).order_by(CheckinGuest.Id.desc()).first()
                    
            
        checkinguest.CheckinDate=datetime.fromisoformat(guest_data['CheckinDateTime'])
        checkinguest.IsMainGuest=guest_data['IsMainGuest']
        checkinguest.GuestCode=guest_data.get('GuestCode')
        checkinguest.GuestUID= None
        checkinguest.CheckoutDate=None
        checkinguest.IsFirstGuest=True
        checkinguest.GuestId=guest.Id
        checkinguest.CheckinId=main_checkin.Id
        checkinguest.RelationshipName=guest_data.get('RelationshipCode')
        checkinguest.EscortTypeId=2
        checkinguest.VisitPurposeId=visit_purpose.Id

        db.session.commit()

        guests_response.append({
            "uid": guest.Id,
            "guestCode": guest_data.get('GuestCode'),
            "attachments": attachments_response
        })

        # Step 6: Create Log
        log = Log(
            AddedAt=local_time_str,
            RoomNumber=main_checkin.RoomNumber,
            RequestType='Guest PUT',
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

        is_main_guest = guest_data.get('IsMainGuest', False)
        relationship_code = guest_data.get('RelationshipCode')
        relationship = None 
        if is_main_guest:
            current_mainguest_checkinId = checkinguest
        elif not is_main_guest:
            
            current_mainguest_checkinId = CheckinGuest.query.filter(
                            CheckinGuest.CheckinId == main_checkin.Id,
                            CheckinGuest.IsMainGuest == True
                            # Ensure 'IsMainGuest' is used correctly
                        ).order_by(CheckinGuest.Id.desc()).first()
            
            relationship = Relationship.query.filter_by(DtcmCode=relationship_code).first().Id

        print(main_checkin.Id)
        print(current_mainguest_checkinId)

        
            
        # Step 7: Create GuestVersion
        guest_version = GuestVersion(
            FirstName=guest.FirstName,
            LastName=guest.LastName,
            ArabicFirstName=guest.ArabicFirstName,
            ArabicLastName=guest.ArabicLastName,
            Gender=guest.Gender,
            BirthDate=guest.BirthDate,
            ResidenceCountryPhone=guest.ResidenceCountryPhone,
            MobileCode=guest.MobileCode,
            MobileNumber=guest.MobileNumber,
            Email=guest.Email,
            RequiresAccessibilityJson=guest.RequiresAccessibilityJson,
            CheckinId=main_checkin.Id,
            DocumentNumber=guest.DocumentNumber,
            NationalityId=guest.NationalityId,
            EmirateId=guest.EmirateId,
            CheckinDate=checkinguest.CheckinDate,
            CheckoutDate=checkinguest.CheckoutDate,
            IsMainGuest=checkinguest.IsMainGuest,
            GuestCode=checkinguest.GuestCode,
            GuestUID=checkinguest.GuestUID,
            GuestId= guest.Id,
            RelationshipId=relationship,
            EscortTypeId=checkinguest.EscortTypeId,
            VisitPurposeId=checkinguest.VisitPurposeId,
            ExpiryDate=guest_attachment.ExpiryDate,
            IssueDate=guest_attachment.IssueDate,
            DocumentTypeId=guest_attachment.DocumentTypeId,
            LogId=log.Id,
            CheckinGuestId=checkinguest.Id,
            BirthPlaceName=guest.BirthPlaceName,
            ResidenceCountryTwoCode=guest.ResidenceCountryTwoCode,
            IssueCountryTwoCode=Country.query.get(guest_attachment.IssueCountryId).TwoCode,  # Assuming IssueCountryId maps to TwoCode
            AttachmentInfoListJson=guest_attachment.AttachmentInfoListJson,
            CurrentMainCheckinGuestId=current_mainguest_checkinId.Id
        )
        db.session.add(guest_version)
        db.session.commit()

        


        response = {
                    "CheckinUID": main_checkin.Id,
                    "guests": guests_response,
                    "requestMessageID": log.Id,
                    "hasErrors": False,
                    "errorMessages": {},
                    "messageType": "GuestResponse",
                    "clientUID": data.get('ClientUID'),
                    "messageUID": str(uuid.uuid4()),  # Generate a unique message UID
                    "correlationUID": data.get('CorrelationUID'),
                    "timestamp": local_time_str
                }
        return jsonify(response), 201

        

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": str(e)},
            "messageType": "CheckinResponse",
            "clientUID": data.get('ClientUID'),
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID'),
            # "timestamp": datetime.now(timezone.utc).isoformat()
            "timestamp": local_time_str
        }), 500

