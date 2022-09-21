import csv

class VideoOcrResolution:
    width = 0
    height = 0
    
    def __init__(self, width = 0, height = 0):
        self.width = width
        self.height = height

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class VideoOcrMedia:
    filename = ""
    duration = 0
    frameRate = 0
    numFrames = 0
    resolution = VideoOcrResolution()

    def __init__(self, filename = "", duration = 0, frameRate = 0, numFrames = 0, resolution = VideoOcrResolution()):
        self.filename = filename
        self.duration = duration
        self.frameRate = frameRate
        self.numFrames = numFrames
        self.resolution = resolution

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class VideoOcrObjectScore:
    type = ""
    value = 0
    
    def __init__(self, type = "", value = 0):
        self.type = type
        self.value = value
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)
    

class VideoOcrObjectVertices:
    xmin = 0
    ymin = 0
    xmax = 0
    ymax = 0
    
    def __init__(self, xmin = 0, ymin = 0, xmax = 0, ymax = 0):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)
    
     
class VideoOcrObject:
    text = ""
    language = None 
    score = None
    vertices = VideoOcrObjectVertices()
    
    def __init__(self, text = "", language = None, score = None, vertices = VideoOcrObjectVertices()):
        self.text = text
        self.language = language
        self.score = score
        self.vertices = vertices
        
    # Return true if the text in this object equals that in the given object.
    # TODO We might want to match positions as well in some use cases.
    def match(self, object):
        return self.text == object.text
        
    @classmethod
    def from_json(cls, json_data: dict):
        language = None
        score = None
        if "language" in json_data.keys():
            language = json_data["language"]
        if "score" in json_data.keys():
            score = VideoOcrObjectScore.from_json(json_data["score"])
        return cls(json_data["text"], language, score, VideoOcrObjectVertices.from_json(json_data["vertices"]))


class VideoOcrFrame:
    start = 0
    content = None    # the concatenation of all texts in the objects list, with a space in between each
    objects = []
    
    def __init__(self, start = 0, content = None, objects = []):
        self.start = start
        self.content = content
        self.objects = objects
        
    # Return true if the given (previous) frame is a duplicate (by content if available, by words otherwise) of this one. 
    def duplicate(self, frame, dup_gap):
        # the given frame is assumed to be prior to this one, or None, 
        # in which case this frame is the first one, thus not a duplicate
        # content is optional and may not be populated, in which case use words for comparison;
        # note that compare by words are stricter as each correspond words pair in the lists must match        
        if frame == None:
            return False
        elif self.content and frame.content:
            return self.duplicate_content(frame, dup_gap)
        else:
            return self.duplicate_words(frame, dup_gap)

    # Return true if the given (previous) frame is a duplicate (by content) of this one.
    # Frames are considered duplicate if they have the same content (words concatenated) and are consecutive within the given dup_gap.
    def duplicate_content(self, frame, dup_gap):
        # if the given frame is not None, and
        # the difference between frames start times is within the dup_gap (i.e. considered consecutive), and
        # the frames contain same content (i.e. the concatenation of all words in the frame)
        # then they are duplicate
        return (frame != None) and (self.start - frame.start < dup_gap) and (self.content == frame.content)
    
    # Return true if the given (previous) frame is a duplicate (by words) of this one.
    # Frames are considered duplicate if they have the same list of words and are consecutive within the given dup_gap.
    def duplicate_words(self, frame, dup_gap):
        # if the given frame is None return false
        if frame == None:
            return False
          
        # the given frame is assumed to be prior to this one; 
        # if the difference between frames start times is beyond the dup_gap, they are not considered consecutive, thus not duplicate
#         print(f"self.start = {self.start}, frame.start = {frame.start}, dup_gap = {dup_gap}")
        if self.start - frame.start >= dup_gap:
            return False
          
        # if the frames contain different number of objects, return false
        if len(self.objects) != len(frame.objects):
            return False
          
        # otherwise compare the text in each object
        # TODO: In theory, the order of the objects could be random, in which case we can"t compare by index, 
        # but need to match whole list for each object; an efficient way is to use hashmap.
        # For our use case, it"s probably fine to assume that the VOCR tool will generate the list 
        # in the same order for duplicate frames.
        for i, object in enumerate(self.objects):
            if not object.match(frame.objects[i]):
                # if one doesn"t match return false
                return False
              
        # if all texts match return true
        return True
    
    @classmethod
    def from_json(cls, json_data: dict):                  
        content = None
        if "content" in json_data.keys():
            content = json_data["content"]
        objects = list(map(VideoOcrObject.from_json, json_data["objects"]))
        return cls(json_data["start"], content, objects)
    
    
class VideoOcr:
    media = VideoOcrMedia()
    texts = []
    frames = []
    
    def __init__(self, media = VideoOcrMedia(), texts = [], frames = []):
        self.media = media
        self.texts = texts
        self.frames = frames
   
    # Return a new VideoOcr instance with the duplicate frames removed. 
    def dedupe(self, dup_gap):
        frames = []
        previous = None
        for frame in self.frames:
            if not frame.duplicate(previous, dup_gap):
                frames.append(frame)
            previous = frame
        return VideoOcr(self.media, self.texts, frames)
          
    def toCsv(self, csvFile):
        # Write as csv
        with open(csvFile, mode='w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['Start Time', 'Text', 'Language', 'X Min', 'Y Min', 'X Max', 'Y Max', 'Score Type', 'Score Value'])
            for f in self.frames:
                for o in f.objects:
                    if o.score is not None:
                        scoreType = o.score.type
                        scoreValue = o.score.value
                    else:
                        scoreType = ''
                        scoreValue = ''
                    if o.language is not None:
                        language = o.language
                    else:
                        language = ''
                    v = o.vertices
                    csv_writer.writerow([f.start, o.text, language, v.xmin, v.ymin, v.xmax, v.ymax, scoreType, scoreValue])                    
        
    @classmethod
    def from_json(cls, json_data: dict):
        media = VideoOcrMedia.from_json(json_data["media"])   
        if "texts" in json_data.keys(): 
            texts = [] # TODO              
        frames = list(map(VideoOcrFrame.from_json, json_data["frames"]))
        return cls(media, texts, frames)
       
                                 

     