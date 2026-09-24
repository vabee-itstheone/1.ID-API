from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from app.config import Config


class Checkin(db.Model):
    __tablename__ = 'checkin'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    CheckinUID = db.Column(db.String(45), nullable=True)  # nvarchar(45)
    RoomNumber = db.Column(db.String(10), nullable=False)  # nvarchar(10)
    CheckinDate = db.Column(db.DateTime, nullable=False)  # datetime2
    IsActive = db.Column(db.Boolean, nullable=False)  # bit
    ChargeExtra = db.Column(db.Boolean, nullable=False)  # bit
    IsFeeUpdated = db.Column(db.Boolean, nullable=False)  # bit
    TDFee = db.Column(db.Float, nullable=True)  # float(53)
    AddedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # datetime2
    AddedFrom = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    CheckinTypeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkintype.Id'), nullable=False)
    PaymentId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.payment.Id'), nullable=False)
    ChildEscortCount = db.Column(db.Integer, nullable=True)  # int
    AdultEscortCount = db.Column(db.Integer, nullable=True)  # int

    
    payment = db.relationship('Payment', backref='checkins')

    def __repr__(self):
        return f"<Checkin Id={self.Id}, RoomNumber={self.RoomNumber}, CheckinDate={self.CheckinDate}>"
    

class Checkout(db.Model):
    __tablename__ = 'checkout'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    CheckoutDate = db.Column(db.DateTime, nullable=False)  # datetime2
    ChargeExtra = db.Column(db.Boolean, nullable=False)  # bit
    AddedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # datetime2
    AddedFrom = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    CheckinId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkin.Id'), nullable=False)
    CancellationReasonId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.cancellationreason.Id'), nullable=True)
    CheckoutTypeId = db.Column(db.Integer, nullable=False)  # int

    def __repr__(self):
        return f"<Checkout Id={self.Id}, CheckoutDate={self.CheckoutDate}, CheckinId={self.CheckinId}>"
    

class RoomChange(db.Model):
    __tablename__ = 'roomchange'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    FromRoomNumber = db.Column(db.String(10), nullable=False)  # nvarchar(10)
    ToRoomNumber = db.Column(db.String(10), nullable=False)  # nvarchar(10)
    CheckinId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkin.Id'), nullable=False)
    EffectiveDateTime = db.Column(db.DateTime, nullable=False)  # datetime2
    AddedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # datetime2
    AddedFrom = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    LogId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.log.Id'), nullable=False)
    


    def __repr__(self):
        return f"<RoomChange Id={self.Id}, FromRoomNumber={self.FromRoomNumber}, ToRoomNumber={self.ToRoomNumber}, CheckinId={self.CheckinId}>"
    

class AccessibilityType(db.Model):
    __tablename__ = 'accessibilitytype'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name


    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    EnglishName = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    ArabicName = db.Column(db.String(100), nullable=False)  # nvarchar(100)
    DtcmCode = db.Column(db.String(25), nullable=False)  # nvarchar(25)

    def __repr__(self):
        return f"<AccessibilityType Id={self.Id}, EnglishName={self.EnglishName}, ArabicName={self.ArabicName}, DtcmCode={self.DtcmCode}>"
    

class CancellationReason(db.Model):
    __tablename__ = 'cancellationreason'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    Reason = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    DtcmCode = db.Column(db.String(45), nullable=False)  # nvarchar(45)

    def __repr__(self):
        return f"<CancellationReason Id={self.Id}, Reason={self.Reason}, DtcmCode={self.DtcmCode}>"
    

class CardType(db.Model):
    __tablename__ = 'cardtype'  # Table name
    __table_args__ = {'schema':Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    Type = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    MinLength = db.Column(db.Integer, nullable=False)  # int
    MaxLength = db.Column(db.Integer, nullable=False)  # int
    DtcmCode = db.Column(db.String(45), nullable=False)  # nvarchar(45)

    def __repr__(self):
        return f"<CardType Id={self.Id}, Type={self.Type}, MinLength={self.MinLength}, MaxLength={self.MaxLength}, DtcmCode={self.DtcmCode}>"


class CheckinGuest(db.Model):
    __tablename__ = 'checkinguest'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    CheckinDate = db.Column(db.DateTime, nullable=False)  # datetime2
    IsMainGuest = db.Column(db.Boolean, nullable=False)  # bit
    GuestCode = db.Column(db.String(75), nullable=True)  # nvarchar(75), nullable
    GuestUID = db.Column(db.String(45), nullable=True)  # nvarchar(45), nullable
    CheckoutDate = db.Column(db.DateTime, nullable=True)  # datetime2, nullable
    IsFirstGuest = db.Column(db.Boolean, nullable=False)  # bit
    GuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.guest.Id'), nullable=False)
    CheckinId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkin.Id'), nullable=False)
    RelationshipName = db.Column(db.String(45), nullable=True)  # nvarchar(45), nullable
    EscortTypeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.escorttype.Id'), nullable=True)
    VisitPurposeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.visitpurpose.Id'), nullable=False)
    

    guest = db.relationship('Guest', backref='checkinguests')
    checkin = db.relationship('Checkin', backref='checkinguests')
   

    def __repr__(self):
        return f"<CheckinGuest Id={self.Id}, GuestCode={self.GuestCode}, GuestUID={self.GuestUID}, CheckinDate={self.CheckinDate}, CheckoutDate={self.CheckoutDate}>"
    

class CheckinType(db.Model):
    __tablename__ = 'checkintype'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    Type = db.Column(db.String(45), nullable=False)  # nvarchar(45)

    def __repr__(self):
        return f"<CheckinType Id={self.Id}, Type={self.Type}>"
    

class CheckoutType(db.Model):
    __tablename__ = 'checkouttype'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    Type = db.Column(db.String(45), nullable=False)



class Country(db.Model):
    __tablename__ = 'country'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    Name = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    ThreeCode = db.Column(db.String(5), nullable=False)  # nvarchar(5)
    TwoCode = db.Column(db.String(5), nullable=False)  # nvarchar(5)
    MobileCode = db.Column(db.String(10), nullable=False)  # nvarchar(10)
    CidCode = db.Column(db.String(10), nullable=False)  # nvarchar(10)
    CidCodeTwo = db.Column(db.String(10), nullable=False)  # nvarchar(10)

    def __repr__(self):
        return f"<Country Id={self.Id}, Name={self.Name}, TwoCode={self.TwoCode}, MobileCode={self.MobileCode}>"
    
class DocumentType(db.Model):
    __tablename__ = 'documenttype'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    Type = db.Column(db.String(45), nullable=False)
    DtcmCode = db.Column(db.String(45), nullable=False)

    def __repr__(self):
        return f"<DocumentType Id={self.Id}, Type={self.Type}, DtcmCode={self.DtcmCode}>"
    


class Dtcmaction(db.Model):
    __tablename__ = 'dtcmaction'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    Name = db.Column(db.String(45), nullable=False)  # nvarchar(45)

    def __repr__(self):
        return f"<Dtcmaction Id={self.Id}, Name={self.Name}>"
    
    
class Emirate(db.Model):
    __tablename__ = 'emirate'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(45), nullable=False)
    DtcmCode = db.Column(db.String(45), nullable=False)

    def __repr__(self):
        return f"<Emirate Id={self.Id}, Name={self.Name}, DtcmCode={self.DtcmCode}>"
    

class EscortType(db.Model):
    __tablename__ = 'escorttype'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    Type = db.Column(db.String(45), nullable=False)

    def __repr__(self):
        return f"<EscortType Id={self.Id}, Type={self.Type}, "
    

class Guest(db.Model):
    __tablename__ = 'guest'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    FirstName = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    LastName = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    ArabicFirstName = db.Column(db.Unicode(45), nullable=False)  # nvarchar(45)
    ArabicLastName = db.Column(db.Unicode(45), nullable=False)  # nvarchar(45)
    Gender = db.Column(db.String(10), nullable=False)  # nvarchar(10)
    BirthDate = db.Column(db.DateTime, nullable=False)  # datetime2
    ResidenceCountryPhone = db.Column(db.String(45), nullable=True)  # nvarchar(45), nullable
    MobileCode = db.Column(db.String(45), nullable=True)  # nvarchar(45), nullable
    MobileNumber = db.Column(db.String(45), nullable=True)  # nvarchar(45), nullable
    Email = db.Column(db.String(45), nullable=True)  # nvarchar(45), nullable
    RequiresAccessibilityJson = db.Column(db.String(255), nullable=True)  # nvarchar(255), nullable
    DocumentNumber = db.Column(db.String(45), nullable=False)  # nvarchar(45)
    NationalityId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.country.Id'), nullable=False)
    EmirateId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.emirate.Id'), nullable=True)
    BirthPlaceName = db.Column(db.String(255), nullable=False)  # nvarchar(255)
    ResidenceCountryTwoCode = db.Column(db.String(5), nullable=False)  # nvarchar(5)

    

    def __repr__(self):
        return f"<Guest Id={self.Id}, FirstName={self.FirstName}, LastName={self.LastName}, DocumentNumber={self.DocumentNumber}>"
    

class GuestAttachment(db.Model):
    __tablename__ = 'guestattachment'  # Table name
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    # Columns
    Id = db.Column(db.Integer, primary_key=True)  # Primary key
    ExpiryDate = db.Column(db.DateTime, nullable=False)  # datetime2
    IssueDate = db.Column(db.DateTime, nullable=False)  # datetime2
    AttachmentInfoListJson = db.Column(db.String(1000), nullable=False)  # nvarchar(1000)
    DocumentTypeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.documenttype.Id'), nullable=False)
    IssueCountryId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.country.Id'), nullable=False)
    GuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.guest.Id'), nullable=False)

    # def __repr__(self):
    #     return f"<GuestAttachment Id={self.Id}, GuestId={self.GuestId}, DocumentTypeId={self.DocumentTypeId}>"

class GuestDocumentImage(db.Model):
    __tablename__ = 'guestdocumentimages'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # replace with your schema if needed

    DocumentId = db.Column(db.Integer, primary_key=True)
    GuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.guest.Id'), nullable=False)
    DocumentUID = db.Column(db.String(255), nullable=True)
    AttachmentCode = db.Column(db.String(255), nullable=True)
    FileName = db.Column(db.String(255), nullable=True)
    FileSizeKB = db.Column(db.Integer, nullable=True)
    ImageData = db.Column(db.LargeBinary, nullable=True)
    UploadedAt = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    


class GuestVersion(db.Model):
    __tablename__ = 'guestversion'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    CheckinGuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkinguest.Id'), primary_key=True, nullable=False)
    LogId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.log.Id'), primary_key=True, nullable=False)



    FirstName = db.Column(db.String(45), nullable=False)
    LastName = db.Column(db.String(45), nullable=False)
    ArabicFirstName = db.Column(db.Unicode(45), nullable=False)
    ArabicLastName = db.Column(db.Unicode(45), nullable=False)
    Gender = db.Column(db.String(10), nullable=False)
    BirthDate = db.Column(db.DateTime, nullable=False)
    ResidenceCountryPhone = db.Column(db.String(45), nullable=True)
    MobileCode = db.Column(db.String(45), nullable=True)
    MobileNumber = db.Column(db.String(45), nullable=True)
    Email = db.Column(db.String(45), nullable=True)
    RequiresAccessibilityJson = db.Column(db.String(255), nullable=True)
    CheckinId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkin.Id'), nullable=False)
    DocumentNumber = db.Column(db.String(45), nullable=False)
    NationalityId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.country.Id'), nullable=False)
    EmirateId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.emirate.Id'), nullable=True)
    CheckinDate = db.Column(db.DateTime, nullable=False)
    CheckoutDate = db.Column(db.DateTime, nullable=True)
    IsMainGuest = db.Column(db.Boolean, nullable=False)
    GuestCode = db.Column(db.String(75), nullable=True)
    GuestUID = db.Column(db.String(45), nullable=True)
    GuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.guest.Id'), nullable=False)
    RelationshipId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.relationship.Id'), nullable=True)
    EscortTypeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.escorttype.Id'), nullable=True)
    VisitPurposeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.visitpurpose.Id'), nullable=False)
    ExpiryDate = db.Column(db.DateTime, nullable=False)
    IssueDate = db.Column(db.DateTime, nullable=False)
    DocumentTypeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.documenttype.Id'), nullable=False)
    # LogId = db.Column(Integer, ForeignKey('log.Id'), nullable=False)
    # CheckinGuestId = db.Column(Integer, ForeignKey('checkinguest.Id'), nullable=False)
    BirthPlaceName = db.Column(db.String(255), nullable=False)
    ResidenceCountryTwoCode = db.Column(db.String(5), nullable=False)
    IssueCountryTwoCode = db.Column(db.String(5), nullable=False)
    AttachmentInfoListJson = db.Column(db.String(1000), nullable=False)
    CurrentMainCheckinGuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkinguest.Id'), nullable=False)

class Log(db.Model):
    __tablename__ = 'log'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    AddedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    RoomNumber = db.Column(db.String(10), nullable=False)
    RequestType = db.Column(db.String(45), nullable=False)
    DtcmStatus = db.Column(db.Integer, nullable=False)
    CidStatus = db.Column(db.Integer, nullable=False)
    CheckinUID = db.Column(db.String(45), nullable=True)
    PayloadIdentifier = db.Column(db.String(45), nullable=True)
    Error = db.Column(db.String(255), nullable=True)
    CheckinGuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkinguest.Id'), nullable=False)
    CheckinId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkin.Id'), nullable=False)

class MainGuestChange(db.Model):
    __tablename__ = 'mainguestchange'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    FormerMainCheckinGuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkinguest.Id'), nullable=False)
    NewMainCheckinGuestId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkinguest.Id'), nullable=False)
    CheckinId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkin.Id'), nullable=False)
    EffectiveDateTime = db.Column(db.DateTime, nullable=False)
    AddedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    AddedFrom = db.Column(db.String(45), nullable=False)
    LogId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.log.Id'), nullable=False)

class Payment(db.Model):
    __tablename__ = 'payment'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name
    
    Id = db.Column(db.Integer, primary_key=True)
    CardNumber = db.Column(db.String(45), nullable=True)
    PaidAmount = db.Column(db.Float, nullable=False)
    AddedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    AddedFrom = db.Column(db.String(45), nullable=False)
    PaymentTypeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.paymenttype.Id'), nullable=False)
    CardTypeId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.cardtype.Id'), nullable=True)

class PaymentType(db.Model):
    __tablename__ = 'paymenttype'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    Type = db.Column(db.String(45), nullable=False)
    DtcmCode = db.Column(db.String(45), nullable=False)

class Relationship(db.Model):
    __tablename__ = 'relationship'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    Relation = db.Column(db.String(45), nullable=False)
    DtcmCode = db.Column(db.String(45), nullable=False)

class Room(db.Model):
    __tablename__ = 'room'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name

    Id = db.Column(db.Integer, primary_key=True)
    RoomNumber = db.Column(db.String(45), nullable=False)
    BedCount = db.Column(db.Integer, nullable=False)
    IsChecked = db.Column(db.Boolean, nullable=False)
    CheckinId = db.Column(db.Integer, db.ForeignKey(f'{Config.SCHEMA_NAME}.checkin.Id'), nullable=True)
    IsWaitingRoom = db.Column(db.Boolean, nullable=False)
    IsActive = db.Column(db.Boolean, nullable=False)


    checkin = db.relationship('Checkin', backref='rooms')

class VisitPurpose(db.Model):
    __tablename__ = 'visitpurpose'
    __table_args__ = {'schema': Config.SCHEMA_NAME}  # Schema name
    
    Id = db.Column(db.Integer, primary_key=True)
    Purpose = db.Column(db.String(45), nullable=False)
    CidCode = db.Column(db.String(45), nullable=False)
    DtcmCode = db.Column(db.String(45), nullable=False)
    DctCode = db.Column(db.String(45), nullable=False)
    PurposeType = db.Column(db.String(45), nullable=False)


# # class AccessibilityType(db.Model):
# #     __tablename__ = 'accessibilitytype'
# #     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

# #     Id = Column(Integer, primary_key=True, autoincrement=True)
# #     EnglishName = Column(String(45), nullable=False)
# #     ArabicName = Column(String(100), nullable=False)
# #     DtcmCode = Column(String(25), nullable=False)

# class CancellationReason(db.Model):
#     __tablename__ = 'cancellationreason'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Reason = Column(String(45), nullable=False)
#     DtcmCode = Column(String(45), nullable=False)

# class CardType(db.Model):
#     __tablename__ = 'cardtype'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Type = Column(String(45), nullable=False)
#     MinLength = Column(Integer, nullable=False)
#     MaxLength = Column(Integer, nullable=False)
#     DtcmCode = Column(String(45), nullable=False)

# # class Checkin(db.Model):
# #     __tablename__ = 'checkin'
# #     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

# #     Id = Column(Integer, primary_key=True, autoincrement=True)
# #     CheckinUID = Column(String(45), nullable=True)
# #     RoomNumber = Column(String(10), nullable=False)
# #     CheckinDate = Column(DateTime, nullable=False)
# #     IsActive = Column(Boolean, nullable=False)
# #     ChargeExtra = Column(Boolean, nullable=False)
# #     IsFeeUpdated = Column(Boolean, nullable=False)
# #     TDFee = Column(Float, nullable=True)
# #     AddedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
# #     AddedFrom = Column(String(45), nullable=False)
# #     CheckinTypeId = Column(Integer, ForeignKey('checkintype.Id'), nullable=False)
# #     PaymentId = Column(Integer, ForeignKey('payment.Id'), nullable=False)
# #     ChildEscortCount = Column(Integer, nullable=True)
# #     AdultEscortCount = Column(Integer, nullable=True)

# class CheckinGuest(db.Model):
#     __tablename__ = 'checkinguest'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     CheckinDate = Column(DateTime, nullable=False)
#     IsMainGuest = Column(Boolean, nullable=False)
#     GuestCode = Column(String(75), nullable=True)
#     GuestUID = Column(String(45), nullable=True)
#     CheckoutDate = Column(DateTime, nullable=True)
#     IsFirstGuest = Column(Boolean, nullable=False)
#     GuestId = Column(Integer, ForeignKey('guest.Id'), nullable=False)
#     CheckinId = Column(Integer, ForeignKey('checkin.Id'), nullable=False)
#     RelationshipName = Column(String(45), nullable=True)
#     EscortTypeId = Column(Integer, ForeignKey('escorttype.Id'), nullable=True)
#     VisitPurposeId = Column(Integer, ForeignKey('visitpurpose.Id'), nullable=False)

# class CheckinType(db.Model):
#     __tablename__ = 'checkintype'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Type = Column(String(45), nullable=False)

# # class Checkout(db.Model):
# #     __tablename__ = 'checkout'
# #     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

# #     Id = Column(Integer, primary_key=True, autoincrement=True)
# #     CheckoutDate = Column(DateTime, nullable=False)
# #     ChargeExtra = Column(Boolean, nullable=False)
# #     AddedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
# #     AddedFrom = Column(String(45), nullable=False)
# #     CheckinId = Column(Integer, ForeignKey('checkin.Id'), nullable=False)
# #     CancellationReasonId = Column(Integer, ForeignKey('cancellationreason.Id'), nullable=True)
# #     CheckoutTypeId = Column(Integer, ForeignKey('checkouttype.Id'), nullable=False)

# class CheckoutType(db.Model):
#     __tablename__ = 'checkouttype'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Type = Column(String(45), nullable=False)

# class Country(db.Model):
#     __tablename__ = 'country'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Name = Column(String(45), nullable=False)
#     ThreeCode = Column(String(5), nullable=False)
#     TwoCode = Column(String(5), nullable=False)
#     MobileCode = Column(String(10), nullable=False)
#     CidCode = Column(String(10), nullable=False)
#     CidCodeTwo = Column(String(10), nullable=False)

# class DocumentType(db.Model):
#     __tablename__ = 'documenttype'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Type = Column(String(45), nullable=False)
#     DtcmCode = Column(String(45), nullable=False)

# class DtcmAction(db.Model):
#     __tablename__ = 'dtcmaction'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Name = Column(String(45), nullable=False)

# class Emirate(db.Model):
#     __tablename__ = 'emirate'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Name = Column(String(45), nullable=False)
#     DtcmCode = Column(String(45), nullable=False)

# class EscortType(db.Model):
#     __tablename__ = 'escorttype'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Type = Column(String(45), nullable=False)

# class Guest(db.Model):
#     __tablename__ = 'guest'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     FirstName = Column(String(45), nullable=False)
#     LastName = Column(String(45), nullable=False)
#     ArabicFirstName = Column(String(45), nullable=False)
#     ArabicLastName = Column(String(45), nullable=False)
#     Gender = Column(String(10), nullable=False)
#     BirthDate = Column(DateTime, nullable=False)
#     ResidenceCountryPhone = Column(String(45), nullable=True)
#     MobileCode = Column(String(45), nullable=True)
#     MobileNumber = Column(String(45), nullable=True)
#     Email = Column(String(45), nullable=True)
#     RequiresAccessibilityJson = Column(String(255), nullable=True)
#     DocumentNumber = Column(String(45), nullable=False)
#     NationalityId = Column(Integer, ForeignKey('country.Id'), nullable=False)
#     EmirateId = Column(Integer, ForeignKey('emirate.Id'), nullable=True)
#     BirthPlaceName = Column(String(255), nullable=False)
#     ResidenceCountryTwoCode = Column(String(5), nullable=False)

# class GuestAttachment(db.Model):
#     __tablename__ = 'guestattachment'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     ExpiryDate = Column(DateTime, nullable=False)
#     IssueDate = Column(DateTime, nullable=False)
#     AttachmentInfoListJson = Column(String(1000), nullable=False)
#     DocumentTypeId = Column(Integer, ForeignKey('documenttype.Id'), nullable=False)
#     IssueCountryId = Column(Integer, ForeignKey('country.Id'), nullable=False)
#     GuestId = Column(Integer, ForeignKey('guest.Id'), nullable=False)

# class GuestVersion(db.Model):
#     __tablename__ = 'guestversion'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     FirstName = Column(String(45), nullable=False)
#     LastName = Column(String(45), nullable=False)
#     ArabicFirstName = Column(String(45), nullable=False)
#     ArabicLastName = Column(String(45), nullable=False)
#     Gender = Column(String(10), nullable=False)
#     BirthDate = Column(DateTime, nullable=False)
#     ResidenceCountryPhone = Column(String(45), nullable=True)
#     MobileCode = Column(String(45), nullable=True)
#     MobileNumber = Column(String(45), nullable=True)
#     Email = Column(String(45), nullable=True)
#     RequiresAccessibilityJson = Column(String(255), nullable=True)
#     CheckinId = Column(Integer, ForeignKey('checkin.Id'), nullable=False)
#     DocumentNumber = Column(String(45), nullable=False)
#     NationalityId = Column(Integer, ForeignKey('country.Id'), nullable=False)
#     EmirateId = Column(Integer, ForeignKey('emirate.Id'), nullable=True)
#     CheckinDate = Column(DateTime, nullable=False)
#     CheckoutDate = Column(DateTime, nullable=True)
#     IsMainGuest = Column(Boolean, nullable=False)
#     GuestCode = Column(String(75), nullable=True)
#     GuestUID = Column(String(45), nullable=True)
#     GuestId = Column(Integer, ForeignKey('guest.Id'), nullable=False)
#     RelationshipId = Column(Integer, ForeignKey('relationship.Id'), nullable=True)
#     EscortTypeId = Column(Integer, ForeignKey('escorttype.Id'), nullable=True)
#     VisitPurposeId = Column(Integer, ForeignKey('visitpurpose.Id'), nullable=False)
#     ExpiryDate = Column(DateTime, nullable=False)
#     IssueDate = Column(DateTime, nullable=False)
#     DocumentTypeId = Column(Integer, ForeignKey('documenttype.Id'), nullable=False)
#     LogId = Column(Integer, ForeignKey('log.Id'), nullable=False)
#     CheckinGuestId = Column(Integer, ForeignKey('checkinguest.Id'), nullable=False)
#     BirthPlaceName = Column(String(255), nullable=False)
#     ResidenceCountryTwoCode = Column(String(5), nullable=False)
#     IssueCountryTwoCode = Column(String(5), nullable=False)
#     AttachmentInfoListJson = Column(String(1000), nullable=False)
#     CurrentMainCheckinGuestId = Column(Integer, ForeignKey('checkinguest.Id'), nullable=False)

# class Log(db.Model):
#     __tablename__ = 'log'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     AddedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
#     RoomNumber = Column(String(10), nullable=False)
#     RequestType = Column(String(45), nullable=False)
#     DtcmStatus = Column(Integer, nullable=False)
#     CidStatus = Column(Integer, nullable=False)
#     CheckinUID = Column(String(45), nullable=True)
#     PayloadIdentifier = Column(String(45), nullable=True)
#     Error = Column(String(255), nullable=True)
#     CheckinGuestId = Column(Integer, ForeignKey('checkinguest.Id'), nullable=False)
#     CheckinId = Column(Integer, ForeignKey('checkin.Id'), nullable=False)

# class MainGuestChange(db.Model):
#     __tablename__ = 'mainguestchange'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     FormerMainCheckinGuestId = Column(Integer, ForeignKey('checkinguest.Id'), nullable=False)
#     NewMainCheckinGuestId = Column(Integer, ForeignKey('checkinguest.Id'), nullable=False)
#     CheckinId = Column(Integer, ForeignKey('checkin.Id'), nullable=False)
#     EffectiveDateTime = Column(DateTime, nullable=False)
#     AddedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
#     AddedFrom = Column(String(45), nullable=False)
#     LogId = Column(Integer, ForeignKey('log.Id'), nullable=False)

# class Payment(db.Model):
#     __tablename__ = 'payment'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name
#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     CardNumber = Column(String(45), nullable=True)
#     PaidAmount = Column(Float, nullable=False)
#     AddedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
#     AddedFrom = Column(String(45), nullable=False)
#     PaymentTypeId = Column(Integer, ForeignKey('paymenttype.Id'), nullable=False)
#     CardTypeId = Column(Integer, ForeignKey('cardtype.Id'), nullable=True)

# class PaymentType(db.Model):
#     __tablename__ = 'paymenttype'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Type = Column(String(45), nullable=False)
#     DtcmCode = Column(String(45), nullable=False)

# class Relationship(db.Model):
#     __tablename__ = 'relationship'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Relation = Column(String(45), nullable=False)
#     DtcmCode = Column(String(45), nullable=False)

# class Room(db.Model):
#     __tablename__ = 'room'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     RoomNumber = Column(String(45), nullable=False)
#     BedCount = Column(Integer, nullable=False)
#     IsChecked = Column(Boolean, nullable=False)
#     CheckinId = Column(Integer, ForeignKey('checkin.Id'), nullable=True)
#     IsWaitingRoom = Column(Boolean, nullable=False)
#     IsActive = Column(Boolean, nullable=False)

# # class RoomChange(db.Model):
# #     __tablename__ = 'roomchange'
# #     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

# #     Id = Column(Integer, primary_key=True, autoincrement=True)
# #     FromRoomNumber = Column(String(10), nullable=False)
# #     ToRoomNumber = Column(String(10), nullable=False)
# #     CheckinId = Column(Integer, ForeignKey('checkin.Id'), nullable=False)
# #     EffectiveDateTime = Column(DateTime, nullable=False)
# #     AddedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
# #     AddedFrom = Column(String(45), nullable=False)
# #     LogId = Column(Integer, ForeignKey('log.Id'), nullable=False)

# class Settings(db.Model):
#     __tablename__ = 'settings'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name

#     SettingName = Column(String(45), primary_key=True)
#     ApplicationSettingsJson = Column(String(255), nullable=True)
#     EstablishmentSettingsJson = Column(String(255), nullable=True)
#     ThemeSettingsJson = Column(String(255), nullable=True)
#     OtherSettingsJson = Column(String(255), nullable=True)

# class VisitPurpose(db.Model):
#     __tablename__ = 'visitpurpose'
#     __table_args__ = {'schema': '[itsthe1.id].[itsthe1.id]'}  # Schema name
    
#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     Purpose = Column(String(45), nullable=False)
#     CidCode = Column(String(45), nullable=False)
#     DtcmCode = Column(String(45), nullable=False)
#     DctCode = Column(String(45), nullable=False)
#     PurposeType = Column(String(45), nullable=False)