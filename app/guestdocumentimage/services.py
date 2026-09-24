import base64

from sqlalchemy.exc import SQLAlchemyError

from app.config import Config
from app.models import GuestDocumentImage
from app import db

def get_guestdocumentimage_data():
    # A filesystem-only deployment keeps document images under BaseDirectoryPath
    # and never populates this table, so there is nothing to serve. Answer with an
    # empty list rather than an error: the caller asked what is stored here, and
    # the honest answer is "nothing".
    if Config.DOCUMENT_IMAGE_STORAGE == 'filesystem':
        return []

    try:
        # Query the Guest table
        guestdocumentimages = GuestDocumentImage.query.all()

        # ImageData is raw bytes, which jsonify cannot serialise. Base64 is what
        # every other endpoint uses for image content, so use it here too.
        result = [
            {
                'DocumentId': guestdocumentimage.DocumentId,
                'GuestId': guestdocumentimage.GuestId,
                'DocumentUID': guestdocumentimage.DocumentUID,
                'AttachmentCode': guestdocumentimage.AttachmentCode,
                'FileName': guestdocumentimage.FileName,
                'FileSizeKB': guestdocumentimage.FileSizeKB,
                'ImageData': (
                    base64.b64encode(guestdocumentimage.ImageData).decode('ascii')
                    if guestdocumentimage.ImageData else None
                ),
                'UploadedAt': (
                    guestdocumentimage.UploadedAt.isoformat()
                    if guestdocumentimage.UploadedAt else None
                ),
            }
            for guestdocumentimage in guestdocumentimages
        ]

        return result

    except SQLAlchemyError as e:
        db.session.rollback()
        # In "auto" mode a missing table is a deployment shape, not a fault: this
        # database keeps its images on disk. Only a site that declared
        # "database" storage is genuinely broken here.
        if Config.DOCUMENT_IMAGE_STORAGE == 'auto':
            return []
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
