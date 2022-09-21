import ffmpeg
import logging
import tempfile
import os
import datetime
from datetime import timedelta
from datetime import datetime
import math
import subprocess
import shutil
from PIL import Image, ImageDraw

class ContactSheet:
	def __init__(self, input_file, output_file, ncols = 4, thumbw = 300, margin = 10, padding = 3):
		self.temporary_directory = tempfile.TemporaryDirectory()
		self.input_file = input_file
		self.output_file = output_file
		self.video_duration = self.get_duration(input_file)
		self.ncols = ncols # number of thumbnail columns
		self.thumbw = thumbw # width of each thumbnail, in px
		self.marl, self.mart, self.marr, self.marb = margin, margin, margin, margin # margin around edge of contact sheet, in px
		self.padding = padding # space between each image, in px
		
		
	def create_interval(self, frame_interval):
		valid_input = self.validate_interval(frame_interval, self.video_duration)
		if valid_input == False:
			exit(1)
		times, labels = self.getTimesInterval(self.video_duration, frame_interval)
		filenames = self.get_thumbs(self.input_file, times, self.temporary_directory.name)
		logging.debug(filenames)
		self.create_contact_sheet(filenames, labels)

	def create_quantity(self, frame_quantity):
		valid_input = self.validate_quantity(frame_quantity, self.video_duration)
		if valid_input == False:
			exit(1)
		times, labels = self.getTimesQuantity(self.video_duration, frame_quantity)
		filenames = self.get_thumbs(self.input_file, times, self.temporary_directory.name)
		logging.debug(filenames)
		self.create_contact_sheet(filenames, labels)

	def create_faces(self, amp_faces):
		valid_input = self.validate_faces(amp_faces)
		if valid_input == False:
			exit(1)		
		times, labels = self.getTimesFrames(amp_faces)
		filenames = self.get_thumbs(self.input_file, times, self.temporary_directory.name)
		logging.debug(filenames)
		self.create_contact_sheet(filenames, labels)

	def create_shots(self, amp_shots):
		valid_input = self.validate_shots(amp_shots)
		if valid_input == False:
			exit(1)
		times, labels = self.getTimesShots(amp_shots)
		filenames = self.get_thumbs(self.input_file, times, self.temporary_directory.name)
		logging.debug(filenames)
		self.create_contact_sheet(filenames, labels)

	def create_vocr(self, amp_vocr):
		valid_input = self.validate_vocr(amp_vocr)
		if valid_input == False:
			exit(1)
		times, labels = self.getTimesFrames(amp_vocr)
		filenames = self.get_thumbs(self.input_file, times, self.temporary_directory.name)
		logging.debug(filenames)
		self.create_contact_sheet(filenames, labels)


	def create_contact_sheet(self, filenames, labels):
		nrows = math.ceil(len(filenames)/self.ncols) # number of rows of images
		
		if len(filenames) > 0:
			sample_image = Image.open(filenames[0]) # A sample image to get aspect ratio from
			width, height = sample_image.size
			ratio = height/width
		else:
			ratio = 1.0	# default ratio if no frame	
			
		thumbh = round(self.thumbw * ratio) # calculated height based on aspect ratio & set width
		filename = self.input_file.split('/')[-1] # Get filename for labelling purposes
		image = self.contact_sheet_assembly(filenames, labels, "file: %s\nLabel: %s" % (filename, 'AMP Contact Sheet'), nrows, thumbh)		
		
		temp_file = self.output_file + ".png"
		image.save(temp_file)		
		shutil.copyfile(temp_file, self.output_file)
		if os.path.exists(temp_file):
			os.remove(temp_file)

	def contact_sheet_assembly(self, fnames, ftimes, headerInfo, nrows, thumbh):
		"""\
		Make a contact sheet from a group of filenames:
		
		fnames       A list of names of the image files
		
		ncols        Number of columns in the contact sheet
		nrows        Number of rows in the contact sheet
		thumbw       The width of the thumbnails in pixels
		thumbh       The height of the thumbnails in pixels
		
		marl         The left margin in pixels
		mart         The top margin in pixels
		marr         The right margin in pixels
		marl         The left margin in pixels
		
		padding      The padding between images in pixels
		
		returns a PIL image object.
		"""
		# Calculate the size of the output image, based on the
		#  photo thumb sizes, margins, and padding
		self.mart = self.mart + 100
		marw = self.marl + self.marr
		marh = self.mart + self.marb

		padw = (self.ncols - 1) * self.padding
		if nrows == 0:
			padh = 0
		else:
			padh = (nrows - 1) * self.padding
		isize = (self.ncols*self.thumbw+marw+padw, nrows*thumbh+marh+padh)

		# Create the new image. The background doesn't have to be white
		white = (255,255,255)
		inew = Image.new('RGB', isize, white)
		# Write the header
		ImageDraw.Draw(inew).text((10,10), str(headerInfo), fill=(0,0,0))
		count = 0

		# Insert each thumb:
		for irow in range(nrows):
			for icol in range(self.ncols):
				left = self.marl + icol * (self.thumbw + self.padding)
				right = left + self.thumbw
				upper = self.mart + irow * (thumbh + self.padding)
				lower = upper + thumbh
				bbox = (left,upper,right,lower)
				try:
					# Read in an image and resize appropriately
					img = Image.open(fnames[count]).resize((self.thumbw,thumbh))
					ImageDraw.Draw(img).text((10,10), str(ftimes[count]), fill=(255,255,0))
				except:
					break
				inew.paste(img,bbox)
				count += 1
				if (count >= len(fnames)):
					break
			
			if (count >= len(fnames)):
				break
		return inew
	
	
	def get_duration(self, input_video):
		result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_video], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		len = math.floor(float(result.stdout))
		return int(len)

	def getTimesInterval(self, videoLength, interval):
		# extract first frame from time 0 so we have at least 1 frame in result, even if interval > videoLength
		times = [t for t in range(0, videoLength, interval)]
		labels = []
		for t in times:
			labels.append(str(timedelta(seconds=round(t))))
		logging.debug(f"Video length: {videoLength}")
		logging.debug(f"Number of frames: {len(times)}")
		logging.debug(f"Frame interval: {interval}")
		return times, labels

	def getTimesQuantity(self, videoLength, numFrames):
		# use ceil instead of floor to ensure interval > 0, and the right number of frames get extracted starting at time 0
		interval = math.ceil(videoLength/numFrames)
		return self.getTimesInterval(videoLength, interval)

	# for Faces and VOCR
	def getTimesFrames(self, data):
		times = []
		labels = []		
		for i, frame in enumerate(data["frames"]):
			# Find the timestamp for the middle frame of the frame
			start = float(frame["start"])
			times.append(start)

			# Save a formatted time range for this frame in the list of times
			range = str(timedelta(seconds=round(start)))
			labels.append(range)
		return times, labels

	def getTimesShots(self, data):
		times = []
		labels = []
		for i, shot in enumerate(data["shots"]):
			if shot["type"] == "scene": # for Azure-- skip things labeled "scene"
				continue
			# Find the timestamp for the middle frame of the shot
			start = float(shot["start"])
			end = float(shot["end"])
			middle = str(timedelta(seconds=(end-start)/2 + start))
			times.append(middle)
			# Save a formatted time range for this shot in the list of times
			range = str(timedelta(seconds=round(start))) + " - " + str(timedelta(seconds=round(end)))
			labels.append(range)
		return times, labels
	
	def get_seconds_from_time_string(self, time_string):
		pt = datetime.strptime(time_string,'%H:%M:%S.%f')
		total_seconds = pt.second + pt.minute*60 + pt.hour*3600
		return total_seconds


	def validate_interval(self, frame_interval, video_duration):
		# frame interval should be not empty and greater than 0
		if frame_interval is None or frame_interval <= 0:
			logging.error(f"Error: Invalid seconds input for time: {frame_interval}")
			return False
		# give a warning if frame interval is greater than video_duration
		if frame_interval > video_duration:
			logging.warning(f"Warning: the frame interval in seconds {frame_interval} is greater than the video length {video_duration}, so only one frame will be extracted.")
		return True

	def validate_quantity(self, frame_quantity, video_duration):
		# frame quantity should be not empty and greater than 0
		if frame_quantity is None or frame_quantity <= 0:
			logging.error(f"Invalid quantity input for quantity: {frame_quantity}")
			return False
		# give a warning if frame quantity is greater than video_duration
		if frame_quantity > video_duration:
			logging.warning(f"Warning: the frame quantity {frame_quantity} is greater than the video length {video_duration}, so only {video_duration} frames will be extracted.")
		return True

	def validate_faces(self, amp_faces):
		if amp_faces is None or 'frames' not in amp_faces.keys():
			logging.error("Invalid amp_faces json")
			return False
		return True

	def validate_shots(self, amp_shots):
		if amp_shots is None or 'shots' not in amp_shots.keys():
			logging.error("Invalid amp_shots json")
			return False
		return True

	def validate_vocr(self, amp_vocr):
		if amp_vocr is None or 'frames' not in amp_vocr.keys():
			logging.error("Invalid amp_vocr json")
			return False
		return True

	def get_thumbs(self, video, times, temporary_directory):
		fnames = []
		logging.debug(times)
		# For every shot...
		for i,t in enumerate(times):
			# Set the name for the temp image file, and add that to the list of filenames
			outname = os.path.join(temporary_directory, str(i) + ".jpg")
			fnames.append(outname)
			logging.debug(t)
			(
				ffmpeg
				.input(video, ss=t)
				.output(outname, vframes=1)
				.run()
			)
			logging.info("Saved thumbnail: %d/%d" % (i+1, len(times)))
		return fnames