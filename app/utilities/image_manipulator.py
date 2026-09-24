import os
import base64
from PIL import Image
from io import BytesIO
import math
import logging
import hashlib
import uuid
import base64


from app.config import Config

BaseDirectoryPath = Config.BaseDirectoryPath


# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class AttachmentInfo:
    def __init__(self, name, attachment_code, content_base64_encoded, size, uid, is_duplicate=False):
        self.name = name
        self.attachment_code = attachment_code
        self.content_base64_encoded = content_base64_encoded
        self.size = size
        self.uid = uid
        # True when the content was already stored and this info points at the existing file
        self.is_duplicate = is_duplicate

class ImageManipulator:

    # @staticmethod
    # def save_bitmap_image_list(image_list, guest_id):
    #     """
    #     Saves a list of images to disk and returns a list of AttachmentInfo objects.
    #     """
    #     attach_info_list = []
    #     base_attachment_directory_path = DirectoryStructureManager.get_attachment_directory_path_for(str(guest_id))

    #     try:
    #         compressed_image_list = ImageManipulator.compress_bitmap_image_list(image_list)
    #         file_incrementer = 0

    #         for image in compressed_image_list:
    #             file_incrementer += 1
    #             image_name = f"Image_{file_incrementer}.jpg"
    #             current_attachment_path = os.path.join(base_attachment_directory_path, image_name)

    #             # Save the image to disk
    #             image.save(current_attachment_path, "JPEG")

    #             # Create AttachmentInfo object
    #             attach_info_list.append(AttachmentInfo(
    #                 name=image_name,
    #                 attachment_code=ImageManipulator.generate_attachment_code(),
    #                 content_base64_encoded=None,  # Set to None as in the C# code
    #                 size=os.path.getsize(current_attachment_path),
    #                 uid=None
    #             ))

    #     except Exception as ex:
    #         logger.error(f"Error in save_bitmap_image_list: {str(ex)}", exc_info=True)

    #     return attach_info_list
    # @staticmethod
    # def save_bitmap_image_list(image_list, guest_id):
    #     """
    #     Saves a list of images to disk and returns a list of AttachmentInfo objects.
    #     """
    #     attach_info_list = []
    #     base_attachment_directory_path = DirectoryStructureManager.get_attachment_directory_path_for(str(guest_id))

    #     try:
    #         compressed_image_list = ImageManipulator.compress_bitmap_image_list(image_list)

    #         # Check existing files to determine the next available file index
    #         existing_files = [f for f in os.listdir(base_attachment_directory_path) if f.endswith(".jpg")]
    #         file_incrementer = len(existing_files)  # Start counting from existing images

    #         for image in compressed_image_list:
    #             file_incrementer += 1  # Ensure unique names
    #             image_name = f"Image_{file_incrementer}.jpg"
    #             current_attachment_path = os.path.join(base_attachment_directory_path, image_name)

    #             # Save the image to disk
    #             image.save(current_attachment_path, "JPEG")

    #             # Create AttachmentInfo object
    #             attach_info_list.append(AttachmentInfo(
    #                 name=image_name,
    #                 attachment_code=ImageManipulator.generate_attachment_code(),
    #                 content_base64_encoded=None,  # Set to None as in the C# code
    #                 size=os.path.getsize(current_attachment_path),
    #                 uid=None
    #             ))

    #     except Exception as ex:
    #         logger.error(f"Error in save_bitmap_image_list: {str(ex)}", exc_info=True)

    #     return attach_info_list

    @staticmethod
    def save_bitmap_image_list(image_list, image_name, guest_id, duplicate_image_status, reserved_names=None):
        """
        Saves a list of images to disk and returns one AttachmentInfo per image.

        A file name is the guest's slot for one document. Re-sending that document with new
        content replaces the stored image instead of piling a second copy next to it, and
        re-sending it unchanged is recognised and not written at all - so repeating a request
        never grows the guest's attachments.

        reserved_names are the names already used by earlier attachments of the same request.
        An image landing on one of those is stored under a suffixed name, which is what keeps
        two attachments sent together from collapsing into a single file.
        """
        attach_info_list = []
        taken_names = list(reserved_names or [])
        base_attachment_directory_path = DirectoryStructureManager.get_attachment_directory_path_for(str(guest_id))

        try:
            compressed_image_list = ImageManipulator.compress_bitmap_image_list(image_list)

            existing_files = [f for f in os.listdir(base_attachment_directory_path) if f.endswith(".jpg")]

            # Hash the content of every stored image, keyed by its file name
            existing_hash_by_name = {}
            for existing_file in existing_files:
                existing_file_path = os.path.join(base_attachment_directory_path, existing_file)
                with open(existing_file_path, "rb") as f:
                    existing_hash_by_name[existing_file] = ImageManipulator.calculate_image_hash(f.read())

            for image in compressed_image_list:
                # Convert image to bytes and calculate its hash
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                image_bytes = buffer.getvalue()
                image_hash = ImageManipulator.calculate_image_hash(image_bytes)

                # A name taken earlier in this request belongs to another attachment, so this
                # one moves aside; the suffix is derived from the name only, which keeps it
                # the same on every request and stops repeats from adding files
                if image_name in taken_names:
                    current_name = ImageManipulator.get_unique_file_name(image_name, taken_names)
                elif existing_hash_by_name.get(image_name) == image_hash:
                    # Unchanged document: point at the stored file instead of writing it twice
                    duplicate_image_status = True
                    stored_path = os.path.join(base_attachment_directory_path, image_name)
                    print(f"Reusing already stored image {image_name} for hash: {image_hash}")

                    attach_info_list.append(AttachmentInfo(
                        name=image_name,
                        attachment_code=ImageManipulator.generate_attachment_code(),
                        content_base64_encoded=None,
                        size=os.path.getsize(stored_path),
                        uid=None,
                        is_duplicate=True
                    ))
                    taken_names.append(image_name)
                    continue
                else:
                    # New content for this document: it replaces the stored version
                    current_name = image_name

                current_attachment_path = os.path.join(base_attachment_directory_path, current_name)

                # Save the image to disk
                with open(current_attachment_path, "wb") as f:
                    f.write(image_bytes)

                # Create AttachmentInfo object
                attach_info_list.append(AttachmentInfo(
                    name=current_name,
                    attachment_code=ImageManipulator.generate_attachment_code(),
                    content_base64_encoded=None,  # Set to None as in the C# code
                    size=os.path.getsize(current_attachment_path),
                    uid=None
                ))

                # Remember the new image so the next one in the batch does not clash with it
                taken_names.append(current_name)
                existing_hash_by_name[current_name] = image_hash

        except Exception as ex:
            logger.error(f"Error in save_bitmap_image_list: {str(ex)}", exc_info=True)


        print("duplicate_image_status1",duplicate_image_status )
        return attach_info_list, duplicate_image_status

    @staticmethod
    def get_unique_file_name(image_name, taken_names):
        """
        Returns image_name, or 'Name_1.jpg', 'Name_2.jpg', ... when that name is already taken.
        """
        base_name, extension = os.path.splitext(image_name)
        candidate = image_name
        counter = 1

        while candidate in taken_names:
            candidate = f"{base_name}_{counter}{extension}"
            counter += 1

        return candidate

    @staticmethod
    def calculate_image_hash(image_bytes):
        """
        Calculates a hash (e.g., MD5) for the image bytes.
        """
        return hashlib.md5(image_bytes).hexdigest()

    @staticmethod
    def compress_bitmap_image_list(image_list):
        """
        Compresses a list of images and returns the compressed images.
        """
        compressed_image_list = []

        for image in image_list:
            try:
                # Resize the image to reduce file size
                resized_image = ImageManipulator.resize_image(image)

                # Compress the image
                compressed_image = ImageManipulator.compress_image(resized_image)

                compressed_image_list.append(compressed_image)

            except Exception as ex:
                logger.error(f"Error compressing image: {str(ex)}", exc_info=True)

        return compressed_image_list

    @staticmethod
    def resize_image(image, target_size=(1080, 720)):
        """
        Resizes the image to the target size.
        """
        return image.resize(target_size,  Image.Resampling.LANCZOS)

    @staticmethod
    def compress_image(image, quality=85):
        """
        Compresses the image by reducing its quality.
        """
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        return Image.open(buffer)

    @staticmethod
    def generate_attachment_code():
        """
        Generates a unique attachment code (replace with your logic).
        """
        return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=')



class DirectoryStructureManager:

    @staticmethod
    def get_attachment_directory_path_for(guest_id):
        """
        Generates the attachment directory path for a given guest ID.
        """
        try:
            relative_attachment_path = DirectoryStructureManager.get_relative_attachment_directory_path(guest_id)
            attachment_directory_path = os.path.join(BaseDirectoryPath, "Attachments", relative_attachment_path)

            if not DirectoryStructureManager.ensure_directory_structure(attachment_directory_path):
                return ""

            return attachment_directory_path

        except Exception as ex:
            logger.error(f"Error in get_attachment_directory_path_for: {str(ex)}", exc_info=True)
            return ""

    @staticmethod
    def get_relative_attachment_directory_path(guest_id_number):
        """
        Generates the relative attachment directory path based on the guest ID number.
        """
        try:
            id_number = float(guest_id_number)
            top_level_folder_number = 0
            intermediate_level_folder_number = 0
            bottom_level_folder_number = id_number

            thousand_rounded_id_number = math.floor(id_number / 1000)
            hundred_rounded_id_number = math.floor(id_number / 100)

            if thousand_rounded_id_number >= 1:
                top_level_folder_number = thousand_rounded_id_number * 1000
                remainder = id_number - top_level_folder_number
                hundred_rounded_remainder = math.floor(remainder / 100)

                if hundred_rounded_remainder >= 1:
                    intermediate_level_folder_number = top_level_folder_number + (hundred_rounded_remainder * 100)
                else:
                    intermediate_level_folder_number = top_level_folder_number + 0

            elif hundred_rounded_id_number >= 1:
                top_level_folder_number = 0
                intermediate_level_folder_number = hundred_rounded_id_number * 100

            else:
                top_level_folder_number = 0
                intermediate_level_folder_number = 0

            return os.path.join(
                str(int(top_level_folder_number)),
                str(int(intermediate_level_folder_number)),
                str(int(bottom_level_folder_number))
            )

        except Exception as ex:
            logger.error(f"Error in get_relative_attachment_directory_path: {str(ex)}", exc_info=True)
            return ""

    @staticmethod
    def ensure_directory_structure(directory_path):
        """
        Ensures the directory structure exists. Creates it if it doesn't.
        """
        if not directory_path:
            return False

        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as ex:
            logger.error(f"Error in ensure_directory_structure: {str(ex)}", exc_info=True)
            return False

