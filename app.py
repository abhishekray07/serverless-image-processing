import boto3
import re
import os
from flask import Flask, request
from pathlib import Path
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__)


S3_BUCKET = os.environ.get("S3_BUCKET")

# Image Upload
S3_UPLOAD_KEY_NAME = "uploads/{filename}"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
UPLOAD_FOLDER = Path(__file__).resolve().parent

# Image download / thumbnail creation
IMG_DOWNLOAD_FILENAME = "/tmp/{filename}"
THUMBNAIL_FILENAME = "/tmp/thumbnail_{filename}"
THUMBNAIL_SIZE = (128, 128)
S3_THUMBNAIL_KEY_NAME = "thumbnails/{filename}"


def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=["POST"])
def upload_image():
    """Receives a request to upload an image."""
    # Check if file was uploaded
    if "file" not in request.files:
        return "No file uploaded"

    file = request.files["file"]
    # Check if file is allowed
    if not allowed_file(file.filename):
        return "File extension not allowed"

    # save file locally
    filename = secure_filename(file.filename)
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    file_key = S3_UPLOAD_KEY_NAME.format(filename=filename)
    upload_image_to_s3(file_path, file_key)

    return "File uploaded successfully!"


def upload_image_to_s3(file_loc, s3_key):
    s3 = boto3.client("s3")
    with open(file_loc, "rb") as f:
        s3.upload_fileobj(f, S3_BUCKET, s3_key)

    print(f"Image: {s3_key} uploaded to S3")



def download_image(bucket, key, filename):
    """Download image from S3 to local storage."""
    s3 = boto3.client("s3")
    download_file = IMG_DOWNLOAD_FILENAME.format(filename=filename)
    s3.download_file(bucket, key, download_file)


def create_and_upload_thumbnail(filename):
    """Create a thumbnail and upload to S3."""
    image_path = IMG_DOWNLOAD_FILENAME.format(filename=filename)
    img = Image.open(image_path)
    img.thumbnail(THUMBNAIL_SIZE)

    thumbnail_path = THUMBNAIL_FILENAME.format(filename=filename)
    img.save(thumbnail_path)

    thumbnail_s3_key = S3_THUMBNAIL_KEY_NAME.format(filename=filename)
    upload_image_to_s3(thumbnail_path, thumbnail_s3_key)


def generate_thumbnail(event, context):
    """Lambda function which receives S3 event."""
    records = event["Records"]
    for record in records:
        s3_data = record["s3"]
        bucket = s3_data["bucket"]["name"]
        key = s3_data["object"]["key"]
        filename = re.sub("uploads/", "", key)
        download_image(bucket, key, filename)
        create_and_upload_thumbnail(filename)
        print(f"Successfully created thumbnail for file: {filename}")

