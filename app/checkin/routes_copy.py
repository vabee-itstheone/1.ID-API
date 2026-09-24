from flask import jsonify, request
from app import db
from app.checkin.services import get_checkin_data
from app.checkin import checkin_bp
from app.models import Payment, Checkin, Guest, GuestAttachment, CheckinGuest, Log, GuestVersion, Room, Country, Emirate, DocumentType, VisitPurpose, Relationship,  PaymentType, CheckinType, CardType, Checkout, RoomChange
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
 # Replace with the actual import for ImageManipulator
from googletrans import Translator
from datetime import datetime, timedelta
import uuid
from flask import jsonify
from .services import validate_guest

translator = Translator()

# Automatically detect the local time zone
local_timezone = tzlocal.get_localzone()  # Detects local time zone based on the machine

# Get the current local time in ISO format with microseconds and time zone offset
local_time = datetime.now(local_timezone)

# Format the timestamp with microseconds and the timezone offset
local_time_str = local_time.isoformat()  
def generate_short_guid():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=')

@checkin_bp.route('/checkin', methods=['GET'])
def checkin():
    data = get_checkin_data()
    return jsonify(data)


@checkin_bp.route('/checkin', methods=['POST'])
def create_checkin():
    data = request.json

    try:

        # Validation 40001: Checkin wrong Establishment UID
        establishment_uid = data.get('ClientUID')
        # if not establishment_uid or establishment_uid != "Establishment101":
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "40001 Checkin wrong Establishment UID"},
        #         "messageType": "CheckinResponse",
        #         "clientUID": establishment_uid,
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": datetime.utcnow().isoformat() + "+04:00"
        #     }), 400

        

        # Validation 40002: Checkin room does not exist
        room_number = data.get('RoomNumber')
        room = Room.query.filter_by(RoomNumber=room_number).first()
        if not room:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40002 Checkin room does not exist"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40003: Checkin room is not available
        if room.IsActive ==  False:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40003 Checkin room is not available"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        error_response = checkin_date_time_overlap_status(room_number, checkin_date, "CheckinRequest")
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
        
        if room.IsChecked:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40050 Checkin room is Occupied"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40004: Checkin date must not be in future
        
        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        # local_time = datetime.now(local_timezone)
        current_datetime = datetime.now()
        # print(checkin_date)
        # print(current_datetime)
        if checkin_date > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Checkin date must not be in future"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40005: Checkin no guests specified
        if 'Guests' not in data or not data['Guests']:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40005 Checkin no guests specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 40006: Checkin no main guest specified
        main_guest_count = sum(1 for guest in data['Guests'] if guest.get('IsMainGuest', False))
        if main_guest_count == 0:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40006 Checkin no main guest specified"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40028: You must have only one main guest
        if main_guest_count > 1:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40028 You must have only one main guest"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        main_checkin_datetime = datetime.fromisoformat(data["CheckinDateTime"])
        
         
        # Check guest check-in and check-out dates
        for guest in data["Guests"]:
            
            guest_checkin = guest["CheckinDateTime"]
            # print("Guest Checkin",guest_checkin)   
            
            if guest_checkin == None:
                guest_checkin = data["CheckinDateTime"]
            

            guest_checkin = datetime.fromisoformat(guest_checkin)
            # print("Guest Checkin After Checkin null",guest_checkin)   
           

            if guest_checkin < main_checkin_datetime :
                response = {
                    "hasErrors": True,
                    "errorMessages": {"general": "50014 Guest Checkin date is before Checkin date"},
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get("CorrelationUID", str(uuid.uuid4())),
                    "timestamp": local_time_str
                }
                return(jsonify(response))  # Debugging print
                

        
        # Validation 40007: Checkin invalid payment method
        payment_method = data.get('PaymentMethodCode')
        valid_payment_methods = ['cash', 'creditcard']
        is_house_use = data.get('IsHouseUse', False)

        # Raise error only if:
        # - Payment method is not valid AND it's NOT a house use check-in
        if payment_method not in valid_payment_methods and not (payment_method is None and is_house_use):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40007 Checkin invalid payment method"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400


        # Validation 40008: Checkin invalid credit card number
        if payment_method == 'creditcard' and not data.get('CreditCardNumber'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40008 Checkin invalid credit card number"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40035: Check-in with house use flag does not require payment method
        if data.get('IsHouseUse', True) and payment_method:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40035 Check-in with house use flag does not require payment method"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        # Validation 40036: Check-in with house use flag does not require credit card number
        if data.get('IsHouseUse', False) and data.get('CreditCardNumber'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40036 Check-in with house use flag does not require credit card number"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40037: Check-in with house use flag does not require early checkin
        if data.get('IsHouseUse', False) and data.get('IsEarlyCheckin', False):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40037 Check-in with house use flag does not require early checkin"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40038: Check-in with house use flag not allowed with waiting for room
        if data.get('IsHouseUse', False) and data.get('IsWaitingForRoom', False):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40038 Check-in with house use flag not allowed with waiting for room"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 40033: Check-in transaction must have at least one guest with check-in date & time equal to transaction check-in date & time
        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        matching_guest = any(
            datetime.fromisoformat(guest['CheckinDateTime']) == checkin_date
            for guest in data['Guests']
        )
        if not matching_guest:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40033 Check-in transaction must have at least one guest with check-in date & time equal to transaction check-in date & time"},
                "messageType": "CheckinResponse",
                "clientUID": data.get('ClientUID', 'Establishment101'),
                "messageUID": establishment_uid,
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        guests1 = data.get("Guests", [])

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
        
        
          
        
            
        # if (data.get('IsHouseUse') == False):
        payment_method_code = data.get('PaymentMethodCode')
        payment_type_id = PaymentType.query.filter_by(DtcmCode=payment_method_code).first()
        credit_card_type_code = data.get('CreditCardTypeCode')
        card_type_id = CardType.query.filter_by(DtcmCode=credit_card_type_code).first()
        print(card_type_id)
        # Step 1: Create Payment
        payment = Payment(
            CardNumber=data.get('CreditCardNumber'),
            PaidAmount=data.get('PaidAmount', 0),
            AddedAt=local_time_str,
            AddedFrom=request.remote_addr,
            PaymentTypeId=payment_type_id.Id if payment_type_id else 1,  # Default to 1 if not provided
            CardTypeId = card_type_id.Id if card_type_id else None
        )
        if data.get('PaymentMethodCode') == 'creditcard':
            payment.CardTypeId = card_type_id.Id if card_type_id else None

        db.session.add(payment)
        db.session.commit()

        
        # Step 2: Create Checkin
        checkin = Checkin(
            CheckinUID=data.get('CheckinUID'),
            RoomNumber=data['RoomNumber'],
            CheckinDate=datetime.fromisoformat(data['CheckinDateTime']),
            IsActive=True,
            ChargeExtra=data.get('IsEarlyCheckin', False),
            IsFeeUpdated=False,
            TDFee=None,
            AddedAt=local_time_str,
            AddedFrom=request.remote_addr,
            CheckinTypeId = 2 if data.get('IsHouseUse') else 1,
            PaymentId=payment.Id
        )
        db.session.add(checkin)
        db.session.commit()
       
        guests_response = []
        # Step 3: Create or Update Guest
        # guest_data = data['Guests'][0]  # Assuming only one guest for simplicity

        
          

        
    
        for guest_data in data['Guests']:

            if not guest_data:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50010 Guest is not specified"},
                    "messageType": "CheckinResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
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
            checkin_date1 = datetime.fromisoformat(data['CheckinDateTime'])
            guest_checkin_date = datetime.fromisoformat(guest_data['CheckinDateTime'])
            # print(checkin_date1)
            # print(guest_checkin_date)
            
            if guest_checkin_date < checkin_date1 :
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

            mobile_code = guest_data.get('ResidenceCountryCode')
            mobile_code = Country.query.filter_by(TwoCode=mobile_code).first()
            print(mobile_code)

            if guest_data.get('RequiresAccessibility') is True:
                requires_accessibility_Json = json.dumps({
                    "AccessibilityTypes": guest_data.get('AccessibilityTypes', []),
                    "OtherAccessibility": guest_data.get('OtherAccessibility', "")
                })
            else:
                requires_accessibility_Json = None  # Or an empty JSON string "{}"


            guest = Guest.query.filter_by(DocumentNumber=guest_data['DocumentNumber']).first()
            if not guest:
                guest = Guest()
                db.session.add(guest)

            guest.FirstName = guest_data['FirstName']
            guest.LastName = guest_data['LastName']
            
            guest.ArabicFirstName = translator.translate(guest.FirstName, dest='ar').text
            guest.ArabicLastName = translator.translate(guest.LastName, dest='ar').text
            
            guest.Gender = guest_data['GenderCode']
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

            
            attachments_response = []
            if 'Attachments' in guest_data:
                attachments = guest_data['Attachments']
                for attachment in attachments:
                    # Decode the base64 image data
                    image_data = base64.b64decode(attachment['ContentBase64Encoded'])
                    image = Image.open(BytesIO(image_data))
                    image_name = attachment['Name']

                    # Save the image using ImageManipulator
                    guest_id = guest.Id  # Use the guest ID from the database
                    attachment_info_list = ImageManipulator.save_bitmap_image_list([image],image_name, guest_id)
                    attachment_uid = str(uuid.uuid4())  # Generate a unique UID for the attachment
                    attachments_response.append({
                        "uid": attachment_uid,
                        "attachmenttCode": attachment.get('AttachmentCode')  or attachment.get('attachmenttCode') # Default value
                    })
            

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

            # Convert the modified list to a JSON string before saving
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
                CheckinId=checkin.Id,
                RelationshipName=guest_data.get('RelationshipCode'),
                EscortTypeId=2,
                VisitPurposeId=visit_purpose.Id
            )
            db.session.add(checkin_guest)
            db.session.commit()

            guests_response.append({
                "uid": checkin_guest.Id,
                "guestCode": guest_data.get('GuestCode'),
                "attachments": attachments_response
            })

            # Step 6: Create Log
            log = Log(
                AddedAt=local_time_str,
                RoomNumber=data['RoomNumber'],
                RequestType='Checkin POST',
                DtcmStatus=-1,
                CidStatus=-1,
                CheckinUID=None,
                PayloadIdentifier=None,
                Error=None,
                CheckinGuestId=checkin_guest.Id,
                CheckinId=checkin.Id
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
                                CheckinGuest.CheckinId == checkin.Id,
                                CheckinGuest.IsMainGuest == True
                                # Ensure 'IsMainGuest' is used correctly
                            ).order_by(CheckinGuest.Id.desc()).first()
                relationship = Relationship.query.filter_by(DtcmCode=relationship_code).first().Id
                
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
                CheckinId=checkin.Id,
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
                IssueCountryTwoCode=guest_attachment.IssueCountryId,  # Assuming IssueCountryId maps to TwoCode
                AttachmentInfoListJson=guest_attachment.AttachmentInfoListJson,
                CurrentMainCheckinGuestId=current_mainguest_checkinId.Id
            )
            db.session.add(guest_version)
            db.session.commit()

        # Step 8: Update Room
        room = Room.query.filter_by(RoomNumber=data['RoomNumber']).first()
        if room:
            room.IsChecked = True
            room.CheckinId = checkin.Id
            db.session.commit()


        response = {
                    "CheckinUID": checkin.Id,
                    "guests": guests_response,
                    "requestMessageID": log.Id,
                    "hasErrors": False,
                    "errorMessages": {},
                    "messageType": "CheckinResponse",
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


@checkin_bp.route('/checkin', methods=['PUT'])
def update_checkin():
    data = request.json

    try:

        establishment_uid = data.get('ClientUID')
        if 'UID' not in data:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "Checkin UID is required"},
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        # Validation 40004: Checkin date must not be in future
        
        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        # local_time = datetime.now(local_timezone)
        current_datetime = datetime.now()
        # print(checkin_date)
        # print(current_datetime)
        if checkin_date > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Checkin date must not be in future"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40002: Checkin room does not exist
        room_number = data.get('RoomNumber')
        room = Room.query.filter_by(RoomNumber=room_number).first()
        if not room:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40002 Checkin room does not exist"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40003: Checkin room is not available
        if room.IsActive ==  False:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40003 Checkin room is not available"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # if room.IsChecked:
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "40050 Checkin room is Occupied"},
        #         "messageType": "CheckinUpdateResponse",
        #         "clientUID": establishment_uid,
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": local_time_str
        #     }), 400

        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        error_response = checkin_date_time_overlap_status(room_number, checkin_date, "CheckinRequest")
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
        
        

        
        # Step 1: Find the existing checkin using UID
        current_checkin = Checkin.query.filter_by(Id=data['UID']).first()
        if not current_checkin:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "Checkin not found for the given UID"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 404
        
        payment_method = data.get('PaymentMethodCode')
        valid_payment_methods = ['cash', 'creditcard']
        is_house_use = data.get('IsHouseUse', False)
        
        # Validation 40008: Checkin invalid credit card number
        if payment_method == 'creditcard' and not data.get('CreditCardNumber'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40008 Checkin invalid credit card number"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40011: Checkin is already checkedout
        
        if not current_checkin.IsActive:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40011 Checkin is already checkedout"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40006: Checkin no main guest specified
        main_guest_count = sum(1 for guest in data['Guests'] if guest.get('IsMainGuest', False))
        if main_guest_count == 0:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40006 Checkin no main guest specified"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40028: You must have only one main guest
        if main_guest_count > 1:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40028 You must have only one main guest"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        main_checkin_datetime = datetime.fromisoformat(data["CheckinDateTime"])
        
         
        # Check guest check-in and check-out dates
        for guest in data["Guests"]:
            
            guest_checkin = guest["CheckinDateTime"]
            # print("Guest Checkin",guest_checkin)   
            
            if guest_checkin == None:
                guest_checkin = data["CheckinDateTime"]
            

            guest_checkin = datetime.fromisoformat(guest_checkin)
            # print("Guest Checkin After Checkin null",guest_checkin)   
           

            if guest_checkin < main_checkin_datetime :
                response = {
                    "hasErrors": True,
                    "errorMessages": {"general": "50014 Guest Checkin date is before Checkin date"},
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get("CorrelationUID", str(uuid.uuid4())),
                    "timestamp": local_time_str
                }
                return(jsonify(response))  # Debugging print
                
        
        if data.get('CheckoutDateTime'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40023 You can’t set a Checkout Date Time during Checkin Update for this checkin"},
                "messageType": "CheckinUpdateResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        guests1 = data.get("Guests", [])

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

        payment_method_code = data.get('PaymentMethodCode')
        payment_type_id = PaymentType.query.filter_by(DtcmCode=payment_method_code).first()
        credit_card_type_code = data.get('CreditCardTypeCode')
        card_type_id = CardType.query.filter_by(DtcmCode=credit_card_type_code).first()
        print(payment_type_id)
        print(card_type_id)
        print(current_checkin)

        payment = Payment.query.filter_by(Id=current_checkin.PaymentId).first()
        if payment:
            payment.CardNumber = data.get('CreditCardNumber')
            payment.AddedAt = local_time_str
            payment.AddedFrom = request.remote_addr
            payment.PaymentTypeId = payment_type_id.Id if payment_type_id else 1

            if data.get('PaymentMethodCode') == 'creditcard':
                payment.CardTypeId = card_type_id.Id if card_type_id else None
            else:
                payment.CardNumber = None
                payment.CardTypeId =  None

        # Commit changes
        db.session.commit()
        # Step 2: Create Checkin
        if current_checkin:
            
            
            current_checkin.CheckinDate=datetime.fromisoformat(data['CheckinDateTime'])
            current_checkin.IsActive=True
            current_checkin.ChargeExtra=data.get('IsEarlyCheckin', False)
            current_checkin.IsFeeUpdated=False
            # TDFee=None,
            current_checkin.AddedAt=local_time_str
            current_checkin.AddedFrom=request.remote_addr
            current_checkin.CheckinTypeId=data.get('CheckinTypeId', 1)  # Default to 1 if not provided
            current_checkin.PaymentId=payment.Id
        
        
        
            
        
        
        guests_response = []
        # Step 3: Create or Update Guest
        # guest_data = data['Guests'][0]  # Assuming only one guest for simplicity
        for guest_data in data['Guests']:

            if not guest_data:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50010 Guest is not specified"},
                    "messageType": "CheckinUpdateResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
        #     # Validation 50001: Guest invalid first name
        #     guest_code = guest_data.get('GuestCode')
        #     if not guest_code or not isinstance(guest_code, str) or len(guest_code) > 75:
        #         return jsonify({
        #             "hasErrors": True,
        #             "errorMessages": {"general": "50001 Guest invalid Guest Code"},
        #             "messageType": "CheckinResponse",
        #             "clientUID": establishment_uid,
        #             "messageUID": str(uuid.uuid4()),
        #             "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #             "timestamp": local_time_str
        #         }), 400
            
            # Validation 50001: Guest invalid first name
            first_name = guest_data.get('FirstName')
            if not first_name or not isinstance(first_name, str):
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50001 Guest invalid first name"},
                    "messageType": "CheckinUpdateResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

            # Validation 50002: Guest invalid last name
            last_name = guest_data.get('LastName')
            if not last_name or not isinstance(last_name, str) or len(last_name) > 45:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50002 Guest invalid last name"},
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                        "messageType": "CheckinUpdateResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50007 Guest invalid birth date"},
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

            # Validation 50014: Guest Checkin date is before Checkin date
            checkin_date1 = datetime.fromisoformat(data['CheckinDateTime'])
            guest_checkin_date = datetime.fromisoformat(guest_data['CheckinDateTime'])
            # print(checkin_date1)
            # print(guest_checkin_date)
            
            if guest_checkin_date < checkin_date1 :
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50014 Guest Checkin date is before Checkin date"},
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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
                    "messageType": "CheckinUpdateResponse",
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

        
        # # # Validation 60012: Attachment issue emirate is not specified
        # # for guest_data in data['Guests']:
        # #     for attachment in guest_data['Attachments']:
        # #         if not attachment.get('IssueEmirateCode'):
        # #             return jsonify({
        # #                 "hasErrors": True,
        # #                 "errorMessages": {"general": "60012 Attachment issue emirate is not specified"},
        # #                 "messageType": "CheckinResponse",
        # #                 "clientUID": data.get('ClientUID', 'Establishment101'),
        # #                 "messageUID": str(uuid.uuid4()),
        # #                 "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        # #                 "timestamp": datetime.utcnow().isoformat() + "+04:00"
        # #             }), 400

        # # # Validation 60013: Attachment issue date is not specified
        # # for guest_data in data['Guests']:
        # #     for attachment in guest_data['Attachments']:
        # #         if not attachment.get('IssueDate'):
        # #             return jsonify({
        # #                 "hasErrors": True,
        # #                 "errorMessages": {"general": "60013 Attachment issue date is not specified"},
        # #                 "messageType": "CheckinResponse",
        # #                 "clientUID": data.get('ClientUID', 'Establishment101'),
        # #                 "messageUID": str(uuid.uuid4()),
        # #                 "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        # #                 "timestamp": datetime.utcnow().isoformat() + "+04:00"
        # #             }), 400

        


            nationality_code = guest_data.get('NationalityCode')
            # issue_country_code = guest_data.get('IssueCountryCode')
            nationality_country = Country.query.filter_by(TwoCode=nationality_code).first()

            emirate_code = guest_data.get('EmirateCode')
            emirate = Emirate.query.filter_by(DtcmCode=emirate_code).first()
            # ArabicFirstName = translator.translate(guest_data.get('FirstName'), dest='ar').text
            # print(f"ArabicFirstName: {ArabicFirstName}")

            ArabicFirstName = translator.translate(guest_data['FirstName'], dest='ar').text
            ArabicLastName = translator.translate(guest_data['LastName'], dest='ar').text

            mobile_code = guest_data['ResidenceCountryCode'] 
            mobile_code = Country.query.filter_by(TwoCode=mobile_code).first()

            if guest_data.get('RequiresAccessibility') is True:
                requires_accessibility_Json = json.dumps({
                    "AccessibilityTypes": guest_data.get('AccessibilityTypes', []),
                    "OtherAccessibility": guest_data.get('OtherAccessibility', "")
                })
            else:
                requires_accessibility_Json = None  # Or an empty JSON string "{}"


            guest = Guest.query.filter_by(DocumentNumber=guest_data['DocumentNumber']).first()
            

            guest.FirstName = guest_data['FirstName']
            guest.LastName = guest_data['LastName']
            
            # guest.ArabicFirstName = translator.translate(guest.FirstName, dest='ar').text
            # guest.ArabicLastName = translator.translate(guest.LastName, dest='ar').text
            guest.ArabicFirstName = ArabicFirstName
            guest.ArabicLastName = ArabicLastName
            print(guest.FirstName )
            print(guest.LastName )
            print(translator.translate(guest.FirstName, dest='ar').text)
            print(translator.translate(guest.LastName, dest='ar').text)
            
            guest.Gender = guest_data['GenderCode']
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

            
            attachments_response = []
            if 'Attachments' in guest_data:
                attachments = guest_data['Attachments']
                for attachment in attachments:
                    # Decode the base64 image data
                    image_data = base64.b64decode(attachment['ContentBase64Encoded'])
                    image = Image.open(BytesIO(image_data))
                    image_name = attachment['Name']

                    # Save the image using ImageManipulator
                    guest_id = guest.Id  # Use the guest ID from the database
                    attachment_info_list = ImageManipulator.save_bitmap_image_list([image],image_name, guest_id)
                    attachment_uid = str(uuid.uuid4())  # Generate a unique UID for the attachment
                    attachments_response.append({
                        "uid": attachment_uid,
                        "attachmenttCode": attachment.get('AttachmentCode')  or attachment.get('attachmenttCode') # Default value
                    })
            

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

            # Convert the modified list to a JSON string before saving
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
            checkinguest.CheckinId=current_checkin.Id
            checkinguest.RelationshipName=guest_data.get('RelationshipCode')
            checkinguest.EscortTypeId=2
            checkinguest.VisitPurposeId=visit_purpose.Id
            
            

            

        
        
            print('Checckin Guest', checkinguest)
            
            

            db.session.commit()

            guests_response.append({
                "uid": checkinguest.Id,
                "guestCode": guest_data.get('GuestCode'),
                "attachments": attachments_response
            })

        
            # Step 6: Create Log
            log = Log(
                AddedAt=local_time_str,
                RoomNumber=current_checkin.RoomNumber,
                RequestType='Checkin PUT',
                DtcmStatus=-1,
                CidStatus=-1,
                CheckinUID=None,
                PayloadIdentifier=None,
                Error=None,
                CheckinGuestId=checkinguest.Id,
                CheckinId=current_checkin.Id
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
                                CheckinGuest.CheckinId == current_checkin.Id,
                                CheckinGuest.IsMainGuest == True
                                # Ensure 'IsMainGuest' is used correctly
                            ).order_by(CheckinGuest.Id.desc()).first()
                relationship = Relationship.query.filter_by(DtcmCode=relationship_code).first().Id

            print("current_mainguest_checkinId", current_mainguest_checkinId)

            # previous_guest_version = GuestVersion.query.filter(
            #         GuestVersion.CheckinGuestId == checkinguest.Id,
            #         GuestVersion.IsMainGuest == True  # Ensure 'IsMainGuest' is used correctly
            #     ).order_by(GuestVersion.CheckinGuestId.desc()).first()

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
                CheckinId=current_checkin.Id,
                DocumentNumber=guest.DocumentNumber,
                NationalityId=guest.NationalityId,
                EmirateId=guest.EmirateId,
                CheckinDate=checkinguest.CheckinDate,
                CheckoutDate=checkinguest.CheckoutDate,
                IsMainGuest=checkinguest.IsMainGuest,
                GuestCode=checkinguest.GuestCode,
                GuestUID=checkinguest.GuestUID,
                GuestId=guest.Id,
                RelationshipId= relationship,
                EscortTypeId=checkinguest.EscortTypeId,
                VisitPurposeId=checkinguest.VisitPurposeId,
                ExpiryDate=guest_attachment.ExpiryDate,
                IssueDate=guest_attachment.IssueDate,
                DocumentTypeId=guest_attachment.DocumentTypeId,
                LogId=log.Id,
                CheckinGuestId=checkinguest.Id,
                BirthPlaceName=guest.BirthPlaceName,
                ResidenceCountryTwoCode=guest.ResidenceCountryTwoCode,
                IssueCountryTwoCode=guest_attachment.IssueCountryId,  # Assuming IssueCountryId maps to TwoCode
                AttachmentInfoListJson=guest_attachment.AttachmentInfoListJson,
                CurrentMainCheckinGuestId=current_mainguest_checkinId.Id
            )
            db.session.add(guest_version)
            db.session.commit()

            print(local_time_str)

        # # Step 2: Update the checkin
        # current_checkin.IsFeeUpdated = False
        # if data.get('OutsideDubaiMode', False):
        #     current_checkin.CheckinUID = data.get('ConfirmationNumber')
        # db.session.commit()

        # # Step 3: Find the main guest for the checkin
        # main_guest = Guest.query.filter_by(Id=data['GuestId']).first()
        # if not main_guest:
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "The Guest being Edited was not found in the Database to be Updated"},
        #         "messageType": "CheckinResponse",
        #         "clientUID": data.get('ClientUID', 'Establishment101'),
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": datetime.utcnow().isoformat() + "+04:00"
        #     }), 404

        # # Step 4: Update the payment
        # payment = current_checkin.payment
        # payment.PaidAmount = float(data.get('PaidAmount', 0))
        # payment.AddedAt = datetime.utcnow()
        # payment.AddedFrom = request.remote_addr
        # payment.PaymentTypeId = data['PaymentType']['Id']

        # if data['PaymentType']['DtcmCode'] == 'creditcard':
        #     payment.CardTypeId = data['CardType']['Id']
        #     payment.CardNumber = data.get('CreditCardNumber')
        # db.session.commit()

        # # Step 5: Update the checkin details
        # current_checkin.CheckinDate = datetime.fromisoformat(data['CheckinDateTime'])
        # current_checkin.ChargeExtra = data.get('IsEarlyCheckin', False)
        # current_checkin.AddedAt = datetime.utcnow()
        # current_checkin.AddedFrom = request.remote_addr
        # current_checkin.CheckinTypeId = data['CheckinType']['Id']
        # db.session.commit()

        # # Step 6: Update the main guest details
        # main_guest.FirstName = data['FirstName']
        # main_guest.LastName = data['LastName']
        # main_guest.ArabicFirstName = data['ArabicFirstName']
        # main_guest.ArabicLastName = data['ArabicLastName']
        # main_guest.Gender = data['Gender']
        # main_guest.BirthDate = datetime.fromisoformat(data['BirthDate'])
        # main_guest.ResidenceCountryPhone = data['ResidencePhoneNumber']
        # main_guest.MobileCode = data['MobileCodeCountryAndPhoneCode']['Country']['MobileCode']
        # main_guest.MobileNumber = data['MobileNumber']
        # main_guest.Email = data['Email']
        # main_guest.RequiresAccessibilityJson = json.dumps(data.get('AccessibilityInfo')) if data.get('AccessibilityInfo') else None
        # main_guest.DocumentNumber = data['DocumentNumber']
        # main_guest.NationalityId = data['Nationality']['Id']
        # main_guest.EmirateId = data['Emirate']['Id'] if data.get('Emirate') else None
        # main_guest.BirthPlaceName = data['BirthPlaceName']
        # main_guest.ResidenceCountryTwoCode = data['ResidenceCountry']['TwoCode']
        # db.session.commit()

        # # Step 7: Update the guest attachment
        # guest_attachment = GuestAttachment.query.filter_by(GuestId=main_guest.Id).first()
        # if not guest_attachment:
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "Guest attachment not found"},
        #         "messageType": "CheckinResponse",
        #         "clientUID": data.get('ClientUID', 'Establishment101'),
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": datetime.utcnow().isoformat() + "+04:00"
        #     }), 404

        # # Save new attachments and merge with existing ones
        # new_attachments = ImageManipulator.save_bitmap_image_list(data['GuestImagesObservableCollection'], main_guest.Id)
        # existing_attachments = json.loads(guest_attachment.AttachmentInfoListJson)

        # # Merge attachment codes and UIDs
        # for i in range(min(len(new_attachments), len(existing_attachments))):
        #     new_attachments[i]['AttachmentCode'] = existing_attachments[i]['AttachmentCode']
        #     new_attachments[i]['UID'] = existing_attachments[i]['UID']

        # guest_attachment.ExpiryDate = datetime.fromisoformat(data['ExpiryDate'])
        # guest_attachment.IssueDate = datetime.fromisoformat(data['IssueDate'])
        # guest_attachment.AttachmentInfoListJson = json.dumps(new_attachments)
        # guest_attachment.DocumentTypeId = data['DocumentType']['Id']
        # guest_attachment.IssueCountryId = data['IssueCountry']['Id']
        # db.session.commit()

        # # Step 8: Update the checkin guest
        # checkin_guest = CheckinGuest.query.filter_by(CheckinId=current_checkin.Id, GuestId=main_guest.Id).first()
        # if not checkin_guest:
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "Checkin guest not found"},
        #         "messageType": "CheckinResponse",
        #         "clientUID": data.get('ClientUID', 'Establishment101'),
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": datetime.utcnow().isoformat() + "+04:00"
        #     }), 404

        # checkin_guest.CheckinDate = datetime.fromisoformat(data['CheckinDateTime'])
        # checkin_guest.IsMainGuest = True
        # checkin_guest.VisitPurposeId = data['VisitPurpose']['Id']
        # db.session.commit()

        # # Step 9: Create a log entry
        # log_entry = Log(
        #     AddedAt=datetime.utcnow(),
        #     RoomNumber=current_checkin.RoomNumber,
        #     RequestType='CheckinPUT',
        #     DtcmStatus=-1,
        #     CidStatus=-1,
        #     CheckinUID=None,
        #     PayloadIdentifier=None,
        #     Error=None,
        #     CheckinGuestId=checkin_guest.Id,
        #     CheckinId=current_checkin.Id
        # )
        # db.session.add(log_entry)
        # db.session.commit()

        # # Step 10: Create a guest version entry
        # guest_version = GuestVersion(
        #     FirstName=main_guest.FirstName,
        #     LastName=main_guest.LastName,
        #     ArabicFirstName=main_guest.ArabicFirstName,
        #     ArabicLastName=main_guest.ArabicLastName,
        #     Gender=main_guest.Gender,
        #     BirthDate=main_guest.BirthDate,
        #     ResidenceCountryPhone=main_guest.ResidenceCountryPhone,
        #     MobileCode=main_guest.MobileCode,
        #     MobileNumber=main_guest.MobileNumber,
        #     Email=main_guest.Email,
        #     RequiresAccessibilityJson=main_guest.RequiresAccessibilityJson,
        #     CheckinId=current_checkin.Id,
        #     DocumentNumber=main_guest.DocumentNumber,
        #     NationalityId=main_guest.NationalityId,
        #     EmirateId=main_guest.EmirateId,
        #     CheckinDate=checkin_guest.CheckinDate,
        #     CheckoutDate=checkin_guest.CheckoutDate,
        #     IsMainGuest=checkin_guest.IsMainGuest,
        #     GuestCode=checkin_guest.GuestCode,
        #     GuestUID=checkin_guest.GuestUID,
        #     GuestId=main_guest.Id,
        #     RelationshipId=None,
        #     EscortTypeId=checkin_guest.EscortTypeId,
        #     VisitPurposeId=checkin_guest.VisitPurposeId,
        #     ExpiryDate=guest_attachment.ExpiryDate,
        #     IssueDate=guest_attachment.IssueDate,
        #     DocumentTypeId=guest_attachment.DocumentTypeId,
        #     LogId=log_entry.Id,
        #     CheckinGuestId=checkin_guest.Id,
        #     BirthPlaceName=main_guest.BirthPlaceName,
        #     ResidenceCountryTwoCode=main_guest.ResidenceCountryTwoCode,
        #     IssueCountryTwoCode=Country.query.get(guest_attachment.IssueCountryId).TwoCode,
        #     AttachmentInfoListJson=guest_attachment.AttachmentInfoListJson,
        #     CurrentMainCheckinGuestId=checkin_guest.Id
        # )
        # db.session.add(guest_version)
        # db.session.commit()

        # Step 11: Return success response
        response = {
                    "CheckinUID": current_checkin.Id,
                    "guests": guests_response,
                    "requestMessageID": log.Id,
                    "hasErrors": False,
                    "errorMessages": {},
                    "messageType": "CheckinUpdateResponse",
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
            "messageType": "CheckinUpdateResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 500
    


@checkin_bp.route('/checkin/AddBackdatedCheckin', methods=['POST'])
def create_backdatedcheckin():
    data = request.json

    try:

        # Validation 40001: Checkin wrong Establishment UID
        establishment_uid = data.get('ClientUID')
        # if not establishment_uid or establishment_uid != "Establishment101":
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "40001 Checkin wrong Establishment UID"},
        #         "messageType": "CheckinResponse",
        #         "clientUID": establishment_uid,
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": datetime.utcnow().isoformat() + "+04:00"
        #     }), 400

        

        # Validation 40002: Checkin room does not exist
        room_number = data.get('RoomNumber')
        room = Room.query.filter_by(RoomNumber=room_number).first()
        if not room:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40002 Checkin room does not exist"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40003: Checkin room is not available
        if room.IsActive ==  False:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40003 Checkin room is not available"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        checkout_date_time = datetime.fromisoformat(data['CheckoutDateTime'])
        error_response1 = checkin_date_time_overlap_status(room_number, checkin_date, "BackdatedCheckinAction")
        error_response2 = checkout_date_time_overlap_status(room_number, checkin_date, checkout_date_time, "BackdatedCheckinAction")

        print("error_response1",error_response1)
        if error_response1:
            return jsonify({
                "hasErrors": True,
                "errorMessages":error_response1,
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        print("error_response2",error_response2)
        if error_response2:
            return jsonify({
                "hasErrors": True,
                "errorMessages":error_response2,
                "messageType": "CheckinResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # if room.IsChecked:
        #     return jsonify({
        #         "hasErrors": True,
        #         "errorMessages": {"general": "40050 Checkin room is Occupied"},
        #         "messageType": "CheckinResponse",
        #         "clientUID": establishment_uid,
        #         "messageUID": str(uuid.uuid4()),
        #         "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
        #         "timestamp": local_time_str
        #     }), 400
        
        # Validation 40004: Checkin date must not be in future
        
        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        
        # local_time = datetime.now(local_timezone)
        current_datetime = datetime.now()
        # print(checkin_date)
        # print(current_datetime)
        if checkin_date > current_datetime:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Checkin date must not be in future"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40014: Checkout Date Time is invalid
        
        
        
        if not data['CheckoutDateTime']:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40014 Checkout Date Time is invalid"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        


        checkout_date_time = datetime.fromisoformat(data['CheckoutDateTime'])
        is_late_checkout = data.get('IsLateCheckout', False)

        if checkout_date_time < checkin_date:
            
            return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "40034 Check-out date and time should be  after any Check-in date time"},
            "messageType": "CheckinCheckoutResponse",
            "clientUID": establishment_uid,
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
            "timestamp": local_time_str
        }), 400

        current_datetime1 = datetime.now()
        

        # print(checkin_date)
        # print(current_datetime)
        if checkout_date_time > current_datetime1:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40004 Checkout date must not be in future"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        
        # Validation 40005: Checkin no guests specified
        if 'Guests' not in data or not data['Guests']:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40005 Checkin no guests specified"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 40006: Checkin no main guest specified
        main_guest_count = sum(1 for guest in data['Guests'] if guest.get('IsMainGuest', False))
        if main_guest_count == 0:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40006 Checkin no main guest specified"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        # Extract main check-in and check-out dates
        main_checkin_datetime = datetime.fromisoformat(data["CheckinDateTime"])
        main_checkout_datetime = datetime.fromisoformat(data["CheckoutDateTime"])
         
        # Check guest check-in and check-out dates
        for guest in data["Guests"]:
            
            guest_checkin = guest["CheckinDateTime"]
            # print("Guest Checkin",guest_checkin)   
            guest_checkout = guest["CheckoutDateTime"]
            # print("Guest Checkout",guest_checkout) 
            if guest_checkin == None:
                guest_checkin = data["CheckinDateTime"]
            if guest_checkout == None:
                guest_checkout = data["CheckoutDateTime"]

            guest_checkin = datetime.fromisoformat(guest_checkin)
            # print("Guest Checkin After Checkin null",guest_checkin)   
            guest_checkout = datetime.fromisoformat(guest_checkout)
            # print("Guest Checkout After Checkout null",guest_checkout) 

            if guest_checkin < main_checkin_datetime or guest_checkout > main_checkout_datetime:
                response = {
                    "hasErrors": True,
                    "errorMessages": {"general": "40035 Guest check-in and check-out must be within main check-in period"},
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get("CorrelationUID", str(uuid.uuid4())),
                    "timestamp": local_time_str
                }
                return(jsonify(response))  # Debugging print
                

        

        # Validation 40028: You must have only one main guest
        if main_guest_count > 1:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40028 You must have only one main guest"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40007: Checkin invalid payment method
        payment_method = data.get('PaymentMethodCode')
        valid_payment_methods = ['cash', 'creditcard']
        is_house_use = data.get('IsHouseUse', False)

        # Raise error only if:
        # - Payment method is not valid AND it's NOT a house use check-in
        if payment_method not in valid_payment_methods and not (payment_method is None and is_house_use):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40007 Checkin invalid payment method"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400


        # Validation 40008: Checkin invalid credit card number
        if payment_method == 'creditcard' and not data.get('CreditCardNumber'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40008 Checkin invalid credit card number"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40035: Check-in with house use flag does not require payment method
        if data.get('IsHouseUse', True) and payment_method:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40035 Check-in with house use flag does not require payment method"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        

        # Validation 40036: Check-in with house use flag does not require credit card number
        if data.get('IsHouseUse', False) and data.get('CreditCardNumber'):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40036 Check-in with house use flag does not require credit card number"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40037: Check-in with house use flag does not require early checkin
        if data.get('IsHouseUse', False) and data.get('IsEarlyCheckin', False):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40037 Check-in with house use flag does not require early checkin"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        
        # Validation 40038: Check-in with house use flag not allowed with waiting for room
        if data.get('IsHouseUse', False) and data.get('IsWaitingForRoom', False):
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40038 Check-in with house use flag not allowed with waiting for room"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": establishment_uid,
                "messageUID": str(uuid.uuid4()),
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400

        # Validation 40033: Check-in transaction must have at least one guest with check-in date & time equal to transaction check-in date & time
        checkin_date = datetime.fromisoformat(data['CheckinDateTime'])
        matching_guest = any(
            datetime.fromisoformat(guest['CheckinDateTime']) == checkin_date
            for guest in data['Guests']
        )
        if not matching_guest:
            return jsonify({
                "hasErrors": True,
                "errorMessages": {"general": "40033 Check-in transaction must have at least one guest with check-in date & time equal to transaction check-in date & time"},
                "messageType": "CheckinCheckoutResponse",
                "clientUID": data.get('ClientUID', 'Establishment101'),
                "messageUID": establishment_uid,
                "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                "timestamp": local_time_str
            }), 400
        # if (data.get('IsHouseUse') == False):
        payment_method_code = data.get('PaymentMethodCode')
        payment_type_id = PaymentType.query.filter_by(DtcmCode=payment_method_code).first()
        credit_card_type_code = data.get('CreditCardTypeCode')
        card_type_id = CardType.query.filter_by(DtcmCode=credit_card_type_code).first()
        print(card_type_id)
        # Step 1: Create Payment
        payment = Payment(
            CardNumber=data.get('CreditCardNumber'),
            PaidAmount=data.get('PaidAmount', 0),
            AddedAt=local_time_str,
            AddedFrom=request.remote_addr,
            PaymentTypeId=payment_type_id.Id if payment_type_id else 1,  # Default to 1 if not provided
            CardTypeId = card_type_id.Id if card_type_id else None
        )
        if data.get('PaymentMethodCode') == 'creditcard':
            payment.CardTypeId = card_type_id.Id if card_type_id else None

        db.session.add(payment)
        db.session.commit()

        
        # Step 2: Create Checkin
        checkin = Checkin(
            CheckinUID=data.get('CheckinUID'),
            RoomNumber=data['RoomNumber'],
            CheckinDate=datetime.fromisoformat(data['CheckinDateTime']),
            IsActive=False,
            ChargeExtra=data.get('IsEarlyCheckin', False),
            IsFeeUpdated=False,
            TDFee=None,
            AddedAt=local_time_str,
            AddedFrom=request.remote_addr,
            CheckinTypeId = 2 if data.get('IsHouseUse') else 1,
            PaymentId=payment.Id
        )
        db.session.add(checkin)
        db.session.commit()
       
        guests_response = []
        # Step 3: Create or Update Guest
        # guest_data = data['Guests'][0]  # Assuming only one guest for simplicity
        for guest_data in data['Guests']:

            if not guest_data:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50010 Guest is not specified"},
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
            # Validation 50001: Guest invalid first name
            guest_code = guest_data.get('GuestCode')
            if not guest_code or not isinstance(guest_code, str) or len(guest_code) > 75:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50001 Guest invalid Guest Code"},
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                        "messageType": "CheckinCheckoutResponse",
                        "clientUID": establishment_uid,
                        "messageUID": str(uuid.uuid4()),
                        "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                        "timestamp": local_time_str
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50007 Guest invalid birth date"},
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

            # Validation 50014: Guest Checkin date is before Checkin date
            checkin_date1 = datetime.fromisoformat(data['CheckinDateTime'])
            guest_checkin_date = datetime.fromisoformat(guest_data['CheckinDateTime'])
            checkout_date1 = datetime.fromisoformat(data['CheckoutDateTime'])
            guest_checkout_date = datetime.fromisoformat(guest_data['CheckoutDateTime'])
            # print(checkin_date1)
            # print(guest_checkin_date)
            
            if guest_checkin_date < checkin_date1 :
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50014 Guest Checkin date is before Checkin date"},
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
            if guest_checkin_date > checkout_date1 :
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50014 Guest Checkin date is after Checkout date"},
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
            if guest_checkout_date < checkin_date1 :
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50014 Guest Checkout date is before Checkin date"},
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400
            
            if guest_checkout_date > checkout_date1 :
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "50014 Guest Checkout date is after Checkout date"},
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
                    "clientUID": establishment_uid,
                    "messageUID": str(uuid.uuid4()),
                    "correlationUID": data.get('CorrelationUID', str(uuid.uuid4())),
                    "timestamp": local_time_str
                }), 400

                
            if expiry_date1 < current_datetime:
                return jsonify({
                    "hasErrors": True,
                    "errorMessages": {"general": "60011 Attachment is expired"},
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                    "messageType": "CheckinCheckoutResponse",
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
                            "messageType": "CheckinCheckoutResponse",
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

            mobile_code = guest_data.get('ResidenceCountryCode')
            mobile_code = Country.query.filter_by(TwoCode=mobile_code).first()
            print(mobile_code)

            if guest_data.get('RequiresAccessibility') is True:
                requires_accessibility_Json = json.dumps({
                    "AccessibilityTypes": guest_data.get('AccessibilityTypes', []),
                    "OtherAccessibility": guest_data.get('OtherAccessibility', "")
                })
            else:
                requires_accessibility_Json = None  # Or an empty JSON string "{}"


            guest = Guest.query.filter_by(DocumentNumber=guest_data['DocumentNumber']).first()
            if not guest:
                guest = Guest()
                db.session.add(guest)

            guest.FirstName = guest_data['FirstName']
            guest.LastName = guest_data['LastName']
            
            guest.ArabicFirstName = translator.translate(guest.FirstName, dest='ar').text
            guest.ArabicLastName = translator.translate(guest.LastName, dest='ar').text
            
            guest.Gender = guest_data['GenderCode']
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

            
            attachments_response = []
            if 'Attachments' in guest_data:
                attachments = guest_data['Attachments']
                for attachment in attachments:
                    # Decode the base64 image data
                    image_data = base64.b64decode(attachment['ContentBase64Encoded'])
                    image = Image.open(BytesIO(image_data))
                    image_name = attachment['Name']

                    # Save the image using ImageManipulator
                    guest_id = guest.Id  # Use the guest ID from the database
                    attachment_info_list = ImageManipulator.save_bitmap_image_list([image],image_name, guest_id)
                    attachment_uid = str(uuid.uuid4())  # Generate a unique UID for the attachment
                    attachments_response.append({
                        "uid": attachment_uid,
                        "attachmenttCode": attachment.get('AttachmentCode')  or attachment.get('attachmenttCode') # Default value
                    })
            

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

            # Convert the modified list to a JSON string before saving
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
            
            if guest_data['CheckoutDateTime'] == None:
                checkout_date_time1 = datetime.fromisoformat(data['CheckoutDateTime'])
            else:
                checkout_date_time1 = datetime.fromisoformat(guest_data['CheckoutDateTime'])

            checkin_guest = CheckinGuest(
                CheckinDate=datetime.fromisoformat(guest_data['CheckinDateTime']),
                IsMainGuest=guest_data['IsMainGuest'],
                GuestCode=guest_data.get('GuestCode'),
                GuestUID=None,
                CheckoutDate=checkout_date_time1,
                IsFirstGuest=True,
                GuestId=guest.Id,
                CheckinId=checkin.Id,
                RelationshipName=guest_data.get('RelationshipCode'),
                EscortTypeId=2,
                VisitPurposeId=visit_purpose.Id
            )
            db.session.add(checkin_guest)
            db.session.commit()

            guests_response.append({
                "uid": checkin_guest.Id,
                "guestCode": guest_data.get('GuestCode'),
                "attachments": attachments_response
            })

            # Step 5: Update Guest if IsMainGuest is True
            backdated_request_type = "AddBackdatedGuestCheckin POST"
            if guest_data['IsMainGuest']:
                backdated_request_type = "AddBackdatedMainGuestCheckin POST"


            # Step 6: Create Log
            log = Log(
                AddedAt=local_time_str,
                RoomNumber=data['RoomNumber'],
                RequestType=backdated_request_type,
                DtcmStatus=-1,
                CidStatus=-1,
                CheckinUID=None,
                PayloadIdentifier=None,
                Error=None,
                CheckinGuestId=checkin_guest.Id,
                CheckinId=checkin.Id
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
                                CheckinGuest.CheckinId == checkin.Id,
                                CheckinGuest.IsMainGuest == True
                                # Ensure 'IsMainGuest' is used correctly
                            ).order_by(CheckinGuest.Id.desc()).first()
                relationship = Relationship.query.filter_by(DtcmCode=relationship_code).first().Id
                
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
                CheckinId=checkin.Id,
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
                IssueCountryTwoCode=guest_attachment.IssueCountryId,  # Assuming IssueCountryId maps to TwoCode
                AttachmentInfoListJson=guest_attachment.AttachmentInfoListJson,
                CurrentMainCheckinGuestId=current_mainguest_checkinId.Id
            )
            db.session.add(guest_version)
            db.session.commit()

        checkout_date_time2 = datetime.fromisoformat(data['CheckoutDateTime'])
        is_late_checkout2 = data.get('IsLateCheckout', False)


        # Create a new checkout record
        checkout = Checkout(
            CheckoutDate=checkout_date_time2,
            ChargeExtra=is_late_checkout2,
            AddedFrom=request.remote_addr,
            CheckinId=checkin.Id,
            CancellationReasonId=None,
            CheckoutTypeId=1
        )
        db.session.add(checkout)
        db.session.commit()
        
        log = Log(
                AddedAt=local_time_str,
                RoomNumber=data['RoomNumber'],
                RequestType='AddBackdatedCheckin POST',
                DtcmStatus=-1,
                CidStatus=-1,
                CheckinUID=None,
                PayloadIdentifier=None,
                Error=None,
                CheckinGuestId=checkin_guest.Id,
                CheckinId=checkin.Id
            )
        db.session.add(log)
        db.session.commit()

        


        response = {
                    "CheckinUID": checkin.Id,
                    "guests": guests_response,
                    "requestMessageID": log.Id,
                    "hasErrors": False,
                    "errorMessages": {},
                    "messageType": "CheckinCheckoutResponse",
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
            "messageType": "CheckinCheckoutResponse",
            "clientUID": data.get('ClientUID'),
            "messageUID": str(uuid.uuid4()),
            "correlationUID": data.get('CorrelationUID'),
            # "timestamp": datetime.now(timezone.utc).isoformat()
            "timestamp": local_time_str
        }), 500
    


def checkin_date_time_overlap_status(room, date_time, checkin_action_name):
    two_months_ago = datetime.now() - timedelta(days=60)
    # Remove milliseconds by setting microseconds to 0
    two_months_ago = two_months_ago.replace(microsecond=0)


    logs_1 = Log.query.filter(
                Log.RoomNumber == room,
                Log.AddedAt >= two_months_ago
            ).all()
    
    print("Checkin Date", date_time)
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
                            return f"The Checkin Date and Time overlaps with the Previous Checkin. (CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and [Room Change Time: {room_change.EffectiveDateTime}]"
                else:
                    checkout_1 = Checkout.query.filter(Checkout.CheckinId == checkin_1.Id).first()
                    if checkout_1:
                        if date_time >= checkin_1.CheckinDate and date_time <= checkout_1.CheckoutDate:
                            return f"The Checkin Date and Time overlaps with the Previous Checkin. (CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and [Checkout Time: {checkout_1.CheckoutDate}]"

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
                        return f"The Checkin Date and Time overlaps with the Previous Checkin. (CheckinID: {log_1.CheckinId}) between [Room Change Time 1: {room_change_1.EffectiveDateTime}] and [Room Change Time 2: {room_change_2.EffectiveDateTime}]"
                else:
                    # If no next room change exists, check against the checkout table
                    checkout_2 = Checkout.query.filter(Checkout.CheckinId == log_1.CheckinId).first()

                    if checkout_2 and room_change_1.EffectiveDateTime <= date_time <= checkout_2.CheckoutDate:
                        return f"The Checkin Date and Time overlaps with the Previous Checkin. (CheckinID: {log_1.CheckinId}) between [Room Change Time: {room_change_1.EffectiveDateTime}] and [Checkout Time: {checkout_2.CheckoutDate}]"

        if log_1.RequestType == "AddBackdatedMainGuestCheckin POST" :
            # Get the CheckinDate for the related CheckinId
            checkin_2 = Checkin.query.filter(Checkin.Id == log_1.CheckinId).first()

            if checkin_2:
                checkout_3 = Checkout.query.filter(Checkout.CheckinId == checkin_2.Id).first()

                if checkout_3 and checkin_2.CheckinDate <= date_time <= checkout_3.CheckoutDate:
                    return f"The Checkin Date and Time overlaps with the Previous Backdated Checkin. (CheckinID: {checkin_2.Id}) between [Checkin Time: {checkin_2.CheckinDate}] and [Checkout Time: {checkout_3.CheckoutDate}]"
                
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
                return f"The Checkin Date and Time overlaps with the Previous Checkin. (CheckinID: {previous_checkin.Id}) [Checkout Time: {previous_checkout.CheckoutDate}]"

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



def checkout_date_time_overlap_status(room, checkin_date_time, checkout_date_time, checkin_action_name):
    two_months_ago = datetime.now() - timedelta(days=60)
    # Remove milliseconds by setting microseconds to 0
    two_months_ago = two_months_ago.replace(microsecond=0)


    logs_1 = Log.query.filter(
                Log.RoomNumber == room,
                Log.AddedAt >= two_months_ago
            ).all()
    
    print("Checkin Date", checkin_date_time)
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
                        # Check if input dateTime is within the range of CheckinDate and RoomChange.EffectiveDateTime
                        if checkout_date_time >= checkin_1.CheckinDate and checkout_date_time <= room_change.EffectiveDateTime:
                            return (f"The Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and "
                                    f"[Room Change Time: {room_change.EffectiveDateTime}]")
                        
                        elif checkin_date_time <= checkin_1.CheckinDate and checkout_date_time >= room_change.EffectiveDateTime:
                            return (f"Checkin and Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and "
                                    f"[Room Change Time: {room_change.EffectiveDateTime}]") 
                else:
                    checkout_1 = Checkout.query.filter(Checkout.CheckinId == checkin_1.Id).first()
                    if checkin_1.IsActive and checkout_1 is not None:
                    # If the check-in is still active and has a checkout date, check for overlap
                        if checkout_date_time >= checkin_1.CheckinDate:
                            return (f"The Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {checkin_1.Id}) [Checkin Time: {checkin_1.CheckinDate}] which has not checked out yet.")

                    if checkout_1 is not None:
                        # Check if input dateTime is within the range of CheckinDate and CheckoutDate
                        if checkout_date_time >= checkin_1.CheckinDate and checkout_date_time <= checkout_1.CheckoutDate:
                            return (f"The Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and [Checkout Time: {checkout_1.CheckoutDate}]")
                        
                        elif checkout_date_time <= checkin_1.CheckinDate and checkout_date_time >= checkout_1.CheckoutDate:
                            return (f"Checkin and Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {checkin_1.Id}) between [Checkin Time: {checkin_1.CheckinDate}] and [Checkout Time: {checkout_1.CheckoutDate}]")
                        
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
                    if room_change_1.EffectiveDateTime <= checkout_date_time <= room_change_2.EffectiveDateTime:
                        return f"The Checkout Date and Time overlaps with the Previous Checkin. (CheckinID: {log_1.CheckinId}) between [Room Change Time 1: {room_change_1.EffectiveDateTime}] and [Room Change Time 2: {room_change_2.EffectiveDateTime}]"
                    elif checkin_date_time <= room_change_1.EffectiveDateTime and checkout_date_time >= room_change_2.EffectiveDateTime:
                        return (f"Checkin and Checkout Date and Time overlaps with the Previous Checkin. "
                                f"(CheckinID: {log_1.CheckinId}) between [Room Change Time 1: {room_change_1.EffectiveDateTime}] and "
                                f"[Room Change Time 2: {room_change_2.EffectiveDateTime}]") 
                else:
                    # If no next room change exists, check against the checkout table
                    checkout_2 = Checkout.query.filter(Checkout.CheckinId == log_1.CheckinId).first()
                    checkin_2 = Checkin.query.filter(Checkin.Id == log_1.CheckinId).first()

                    if checkin_2.IsActive and checkout_2 is not None:
                    # If the check-in is still active and has a checkout date, check for overlap
                        if checkout_date_time >= checkin_2.CheckinDate:
                            return (f"The Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {checkin_2.Id}) [Checkin Time: {checkin_2.CheckinDate}] which has not checked out yet.")

                    if checkout_2 is not None:
                        # Check if input dateTime is within the range of CheckinDate and CheckoutDate
                        if checkout_date_time >= room_change_1.EffectiveDateTime and checkout_date_time <= checkout_2.CheckoutDate:
                            return (f"The Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {checkin_2.Id}) between [Room Change Time 1: {room_change_1.EffectiveDateTime}] and [Checkout Time: {checkout_2.CheckoutDate}]")
                        
                        elif checkin_date_time <= room_change_1.EffectiveDateTime and checkout_date_time >= checkout_2.CheckoutDate:
                            return (f"Checkin and Checkout Date and Time overlaps with the Previous Checkin. "
                                    f"(CheckinID: {log_1.CheckinId}) between [Room Change Time 1: {room_change_1.EffectiveDateTime}] and [Checkout Time: {checkout_2.CheckoutDate}]")
                        
        if log_1.RequestType == "AddBackdatedMainGuestCheckin POST" :
            # Get the CheckinDate for the related CheckinId
            checkin_3 = Checkin.query.filter(Checkin.Id == log_1.CheckinId).first()

            if checkin_3:
                checkout_3 = Checkout.query.filter(Checkout.CheckinId == checkin_3.Id).first()

                if checkout_3 and checkin_3.CheckinDate <= checkout_date_time <= checkout_3.CheckoutDate:
                    return f"The Checkin Date and Time overlaps with the Previous Backdated Checkin. (CheckinID: {checkin_3.Id}) between [Checkin Time: {checkin_3.CheckinDate}] and [Checkout Time: {checkout_3.CheckoutDate}]"
                elif checkin_date_time <= checkin_3.CheckinDate and checkout_date_time >= checkout_3.CheckoutDate:
                    return f"Checkin and Checkout, Date and Time overlaps with the Previous Backdated Checkin. (CheckinID: {checkin_3.Id}) between [Checkin Time: {checkin_3.CheckinDate}] and [Checkout Time: {checkout_3.CheckoutDate}]"
                
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
            elif checkout_date_time <= previous_checkout.CheckoutDate:
                return f"The Checkin Date and Time overlaps with the Previous Checkin. (CheckinID: {previous_checkin.Id}) [Checkout Time: {previous_checkout.CheckoutDate}]"

        # Adding an escort or editing available guests
        else:
            previous_checkout = (
                CheckinGuest.query.filter(CheckinGuest.CheckinId == previous_checkin.Id).first()
            )

            if(checkin_action_name != None and checkin_action_name != "EditMainGuestAction"):
                return None

            elif previous_checkout and previous_checkout.CheckoutDate:
                if (checkout_date_time > previous_checkout.CheckoutDate) and (
                    checkin_action_name != "AddEscortAction"
                ):
                    return f"The Checkout Date and Time should be before the primary checkout time: {previous_checkout.CheckoutDate}."
            
            

    return None

