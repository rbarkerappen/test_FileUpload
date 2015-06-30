#!/usr/bin/env python

"""
A simple file upload demo for uploading files
either locally or to Amazon S3.
"""

import boto
import os
import simplejson
import datetime
from argparse import ArgumentParser
from flask import Flask, render_template, request, url_for, send_file, abort
from flask.ext.sqlalchemy import SQLAlchemy
from uuid import uuid4
from werkzeug import secure_filename


class Config(object):
	DEBUG = True
	SQLALCHEMY_DATABASE_URI = "postgresql://localhost/fileuploadexample"

	# for s3 upload
	S3_UPLOAD = False
	S3_BUCKET = None
	AWS_ACCESS_KEY = None
	AWS_SECRET_KEY = None
	
	# for local upload
	UPLOAD_FOLDER = None


class LocalConfig(Config):
	S3_UPLOAD = False
	UPLOAD_FOLDER = "uploads"


class S3Config(Config):
	S3_UPLOAD = True
	#TODO set these values before attempting S3 upload
	S3_BUCKET = None
	AWS_ACCESS_KEY = None
	AWS_SECRET_KEY = None


ALLOWED_FILE_TYPES = {
	# ext -> mime type
	".png" : "image/png",
	".gif" : "image/gif",
	".jpg" : "image/jpeg",
	".jpeg" : "image/jpeg",
	".doc" : "application/msword",
	".docx" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	".pdf" : "application/pdf",
}


app = Flask(__name__)
db = SQLAlchemy(app)


class FileUpload(db.Model):
	__tablename__ = "fileuploads"

	fileUploadID = db.Column(db.Integer, primary_key=True)
	originalFilename = db.Column(db.String, nullable=False)
	savedFilename = db.Column(db.String, nullable=False, unique=True)
	url = db.Column(db.String, nullable=False)
	uploaded = db.Column(db.DateTime, default=datetime.datetime.utcnow())

	def __init__(self, fileUploadID=None, originalFilename=None, savedFilename=None, url=None):
		self.fileUploadID = fileUploadID
		self.originalFilename = originalFilename
		self.savedFilename = savedFilename
		self.url = url

	def serialise(self):
		return {
			"fileUploadID" : self.fileUploadID,
			"originalFilename" : self.originalFilename,
			"savedFilename" : self.savedFilename,
			"url" : self.url,
			"uploaded" : self.uploaded.strftime("%Y-%m-%d %H:%M:%S"),
			"deleteURL" : url_for("uploads", savedFilename=self.savedFilename),
		}

	def __repr__(self):
		return "<FileUpload %d>" %self.fileUploadID


def getS3Bucket():
	"""
	Returns the S3 Bucket object which stores 
	the uploaded files.
	"""
	s3 = boto.connect_s3(app.config["AWS_ACCESS_KEY"], app.config["AWS_SECRET_KEY"])
	return s3.get_bucket(app.config["S3_BUCKET"])


def getS3FileURL(filename):
	"""
	Returns the URL for a file uploaded to S3.
	"""
	return "https://%s.s3.amazonaws.com/%s" %(app.config["S3_BUCKET"], filename)


@app.route("/")
def index():
	fileUploads = FileUpload.query.all()
	fileUploads = [fu.serialise() for fu in fileUploads]
	return render_template("index.html", fileUploads=fileUploads)


@app.route("/uploadFiles", methods=["POST"])
def uploadFiles():

	fileUploads = []

	for uploadedFile in request.files.getlist("files"):
	
		# check for allowed file type
		_, ext = os.path.splitext(uploadedFile.filename)

		try:
			mimeType = ALLOWED_FILE_TYPES[ext]
		except KeyError:
			raise ValueError("File type not allowed: %r" %ext)

		# format the filename
		inputFilename = secure_filename(uploadedFile.filename)

		# construct a (hopefully) unique output filename
		outputFilename = "%s_%s" %(str(uuid4()), inputFilename)

		# upload to s3
		if app.config["S3_UPLOAD"]:
			bucket = getS3Bucket()
			key = bucket.new_key(outputFilename)
			key.content_type = mimeType
			key.set_contents_from_string(uploadedFile.read())
			url = getS3FileURL(outputFilename)

		# upload locally
		else:
			destination = os.path.join(app.config["UPLOAD_FOLDER"], outputFilename)
			uploadedFile.save(destination)
			url = url_for("uploads", savedFilename=outputFilename)
	
		# save upload details to db
		fileUpload = FileUpload(originalFilename=uploadedFile.filename, savedFilename=outputFilename, url=url)
		db.session.add(fileUpload)
		fileUploads.append(fileUpload)

	db.session.commit()

	return simplejson.dumps([fu.serialise() for fu in fileUploads])


@app.route("/uploads/<savedFilename>", methods=["GET", "DELETE"])
def uploads(savedFilename):

	fileUpload = FileUpload.query.filter_by(savedFilename=savedFilename).first_or_404()

	# serve uploaded file (local only)
	if request.method == "GET":
		if app.config["S3_UPLOAD"]:
			abort(404)
		return send_file(os.path.join(app.config["UPLOAD_FOLDER"], fileUpload.savedFilename), attachment_filename=fileUpload.originalFilename)

	# deleting the file
	elif request.method == "DELETE":
		if app.config["S3_UPLOAD"]:
			bucket = getS3Bucket()
			bucket.delete_key(fileUpload.savedFilename)
		else:
			location = os.path.join(app.config["UPLOAD_FOLDER"], fileUpload.savedFilename)
			os.remove(location)
		
		db.session.delete(fileUpload)
		db.session.commit()

	return simplejson.dumps(True)


if __name__ == '__main__':
	parser = ArgumentParser(__doc__)
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("--local", action="store_true", default=False, help="Upload files locally")
	group.add_argument("--s3", action="store_true", default=False, help="Upload files to AWS S3")
	args = parser.parse_args()

	if args.local:
		app.config.from_object(LocalConfig)
	
	elif args.s3:
		app.config.from_object(S3Config)

	db.create_all()
	app.run()
