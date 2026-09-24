"""The one place a guest's document images are written.

Every endpoint that accepts Attachments goes through here, so that what a guest
holds after a request is exactly what that request declared: the files on disk,
the rows in guestdocumentimages and the list in AttachmentInfoListJson always
describe the same set of images.

That last part is what this module adds over storing the images one endpoint at a
time. A guest is recognised by document number, so the same person can be sent
again and again - a second check-in, an edit, a backdated entry - and each request
carries its own attachments. Anything the guest was holding from an earlier
request and that this one does not send is removed, which is what stops a guest
sent one document from showing the documents of a previous request.
"""

import base64
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO

from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.config import Config
from app.models import GuestDocumentImage
from app.utilities.image_manipulator import DirectoryStructureManager, ImageManipulator

logger = logging.getLogger(__name__)

# Only files a request could have put there are pruned, so nothing else that ends
# up in the folder is touched.
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

# Set once, when "auto" mode discovers that guestdocumentimages is not in this
# database. Without it every subsequent write would repeat the failing statement,
# and a failed statement poisons the surrounding transaction.
_db_storage_unavailable = False


def _use_database_rows():
    """True when this request should write the guestdocumentimages row."""
    if Config.DOCUMENT_IMAGE_STORAGE == 'filesystem':
        return False
    if Config.DOCUMENT_IMAGE_STORAGE == 'database':
        return True
    return not _db_storage_unavailable


def _note_database_unavailable(exc):
    """Degrade to disk-only storage for the rest of the process."""
    global _db_storage_unavailable
    if not _db_storage_unavailable:
        _db_storage_unavailable = True
        logger.warning(
            "guestdocumentimages is not usable (%s). Document images will be "
            "stored under BaseDirectoryPath only. Set DocumentImageStorage to "
            "\"database\" once the table exists, or to \"filesystem\" to silence "
            "this.", exc
        )
    db.session.rollback()


def store_guest_attachments(guest_id, attachments, retained_names=None):
    """Store the attachments a request sent for one guest.

    Each attachment dict is updated in place with the name and size its image was
    actually stored under, ready to be written to AttachmentInfoListJson by the
    caller. Returns (attachments_response, duplicate_image_status): one response
    entry per attachment sent, and whether any of them was already stored
    unchanged.

    retained_names are names the caller keeps besides the ones it is sending. The
    /guestattachment endpoint adds a document to a guest rather than restating the
    whole set, so it passes the names already listed for that guest; everything
    the guest holds under any other name is removed.
    """
    attachments_response = []
    duplicate_image_status = False
    # Names this guest is left holding: what the caller keeps, plus what it sends
    stored_names = list(retained_names or [])

    for attachment in attachments:
        image_data = base64.b64decode(attachment['ContentBase64Encoded'])
        image = Image.open(BytesIO(image_data))

        attachment_info_list, is_duplicate = ImageManipulator.save_bitmap_image_list(
            [image], attachment['Name'], guest_id, False, stored_names
        )
        duplicate_image_status = duplicate_image_status or is_duplicate

        # Keep the name/size the image was actually stored under: it differs from
        # the requested one when the name was taken or the content is already on disk
        if attachment_info_list:
            attachment['Name'] = attachment_info_list[0].name
            attachment['Size'] = attachment_info_list[0].size
            stored_names.append(attachment_info_list[0].name)

        attachments_response.append({
            "uid": _store_image_row(guest_id, attachment, image_data),
            "attachmenttCode": attachment.get('AttachmentCode') or attachment.get('attachmenttCode')
        })

    _remove_images_not_named(guest_id, stored_names)

    return attachments_response, duplicate_image_status


def _store_image_row(guest_id, attachment, image_data):
    """Write the image into guestdocumentimages and return its DocumentId.

    A stored file keeps one row: unchanged content is reused and new content
    replaces the row, so re-sending a guest never adds a second copy of a document.

    On a filesystem-only deployment there is no row to write, so the image's
    identity is the name it was stored under; a generated UID is returned instead
    so the response still carries one id per attachment.
    """
    if not _use_database_rows():
        return str(uuid.uuid4())

    try:
        return _write_image_row(guest_id, attachment, image_data)
    except SQLAlchemyError as exc:
        if Config.DOCUMENT_IMAGE_STORAGE == 'database':
            raise
        _note_database_unavailable(exc)
        return str(uuid.uuid4())


def _write_image_row(guest_id, attachment, image_data):
    image_hash = ImageManipulator.calculate_image_hash(image_data)
    file_size_kb = int(len(image_data) / 1024)
    attachment_code = (
        attachment.get('AttachmentCode') or attachment.get('attachmenttCode') or attachment['Name']
    )

    existing_blobs = db.session.query(GuestDocumentImage).filter_by(
        GuestId=guest_id, FileName=attachment['Name']
    ).all()

    for blob in existing_blobs:
        if ImageManipulator.calculate_image_hash(blob.ImageData) == image_hash:
            return blob.DocumentId

    if existing_blobs:
        stored_blob = existing_blobs[0]
        stored_blob.AttachmentCode = attachment_code
        stored_blob.FileSizeKB = file_size_kb
        stored_blob.ImageData = image_data
        stored_blob.UploadedAt = datetime.now()
        db.session.flush()
        return stored_blob.DocumentId

    new_blob = GuestDocumentImage(
        GuestId=guest_id,
        DocumentUID=None,
        AttachmentCode=attachment_code,
        FileName=attachment['Name'],
        FileSizeKB=file_size_kb,
        ImageData=image_data,
        UploadedAt=datetime.now()
    )
    db.session.add(new_blob)
    db.session.flush()
    return new_blob.DocumentId


def _remove_images_not_named(guest_id, stored_names):
    """Drop the images this guest holds under any other name.

    Guest ids are reused when the database is rebuilt, so the folder can also hold
    images left by a guest that no longer exists; those go the same way.
    """
    kept = set(stored_names)

    directory_path = DirectoryStructureManager.get_attachment_directory_path_for(str(guest_id))
    if directory_path and os.path.isdir(directory_path):
        for file_name in os.listdir(directory_path):
            if file_name in kept or not file_name.lower().endswith(IMAGE_EXTENSIONS):
                continue
            try:
                os.remove(os.path.join(directory_path, file_name))
            except OSError as ex:
                logger.warning("Could not remove %s for guest %s: %s", file_name, guest_id, ex)

    if not _use_database_rows():
        return

    try:
        stale_rows = db.session.query(GuestDocumentImage).filter(
            GuestDocumentImage.GuestId == guest_id
        )
        if kept:
            stale_rows = stale_rows.filter(GuestDocumentImage.FileName.notin_(kept))

        for row in stale_rows.all():
            db.session.delete(row)

        db.session.flush()
    except SQLAlchemyError as exc:
        if Config.DOCUMENT_IMAGE_STORAGE == 'database':
            raise
        _note_database_unavailable(exc)
