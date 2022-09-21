import logging

class SpeechToText:
	def __init__(self, media=None, results=None):
		if media is None:
			self.media = SpeechToTextMedia()
		else:
			self.media = media
		if results is None:
			self.results = SpeechToTextResult()
		else:
			self.results = results
			 
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(json_data['media'], SpeechToTextResult().from_json(json_data['results']))


class SpeechToTextMedia:
	filename = ""
	duration = 0.00
	
	def __init__(self, duration = 0.00, filename = ""):
		self.duration = duration
		self.filename = filename
		
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)


class SpeechToTextResult:
	transcript = ""
	words = []
	
	def __init__(self, words=[], transcript=""):
		self.transcript = transcript
		self.words = words
		
	# Add new word to the word list.
	def addWord(self, type, text, offset:int, start:float, end:float, scoreType, scoreValue:float):
		newWord = SpeechToTextWord(type, text, offset, start, end, scoreType, scoreValue)
		self.words.append(newWord)
		
	# Compute the offset of each word in the list, after transcript and word list are populated.
	def compute_offset(self):
		# point offset to the beginning of the transcript
		offset = 0
		
		# compute offset by accumulating word length, adding space or not depending on word type
		for word in self.words:
			# if the current word is not the first or it's a pronunciation, count a space in front of it;
			# otherwise (for the first word or punctuation), there should be no space in front of it.
			if offset > 0 and word.type == "pronunciation":
				offset = offset + 1
			
			# populate word offset and point offset to the next char after the current word
			word.offset = offset
			length = len(word.text)
			offset = offset + length				
			tword = self.transcript[word.offset : offset];			
			
			# give a warning for invalid word type
			# TODO alternatively, we could fail the job
			if word.type != "pronunciation" and word.type != "punctuation":
				logging.warning(f"Word {word.text} at offset {offset} is of invalid type {word.type}")

			# give a warning if the word doesn't match the transcript
			# TODO alternatively, we could fail the job, or search the word in the transcript starting from the offset
			if word.text != tword:
				logging.warning(f"Word {word.text} at offset {word.offset} doesn't match the content {tword} in the transcript")
				
		logging.info(f"Computed offset for {len(self.words)} words with ending offset {offset}.")
	
	@classmethod
	def from_json(cls, json_data: dict):
		words_dict = json_data['words']
		words = []
		words = list(map(SpeechToTextWord.from_json, words_dict))
		return cls(words, json_data['transcript'])


class SpeechToTextWord:
	type = ""
	text = ""
	offset = None # corresponding to the start offset of the word in the transcript, counting punctuations
	start = None
	end = None
	score = None
	
	def __init__(self, type = None, text = None, offset = None, start = None, end = None, scoreType = None, scoreValue = None):
		self.type = type
		self.text = text
		if offset is not None and int(offset) >= 0:	
			self.offset = offset
		if start is not None and float(start) >= 0.00:
			self.start = start
		if end is not None and float(end) >= 0.00:
			self.end = end
		if scoreValue is not None:
			self.score = SpeechToTextScore(scoreType, scoreValue)
		
	@classmethod
	def from_json(cls, json_data: dict):
		start = None
		end = None
		if 'start' in json_data.keys():
			start = json_data['start']
		if 'end' in json_data.keys():
			end = json_data['end']
		scoreType = None
		scoreValue = None
		if 'score' in json_data.keys():
			score = json_data['score']
			scoreValue = score['value']
			scoreType = score['type']
		return cls(json_data['type'], json_data['text'], json_data['offset'], start, end, scoreType, scoreValue)


class SpeechToTextScore:
	type = ""
	value = 0.0
	
	def __init__(self, type = None, value = None):
		self.type = type
		self.value = value
		
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)


	