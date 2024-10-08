import time
from .timeutils import timestamp2hhmmss
from statistics import median
import logging

def gen_vtt(subtitles: list) -> str:
    """Generate VTT text based on the list subtitles given. 
    
    Each subtitle consists of a dict with these keys:
    * start:  start time in seconds
    * end:    end time in seconds
    * text:   subtitle text
    * speaker:  If present and not None, the speaker for the text
    
    Returns a string which is the VTT file
    """
    result = "WEBVTT\n\n"
    for s in subtitles:
        result += f"{timestamp2hhmmss(s['start'])} --> {timestamp2hhmmss(s['end'])}\n"        
        speaker = s.get('speaker', None)
        if speaker:
            result += f"<v {speaker}>"
        result += f"{s['text']}\n\n"
    return result


def alignwords(words: list) -> list:
    """If there are words in the list which have a zero duration, provide a
       reasonable start/end value so they can be timed correctly elsewhere."""
    # find the median duration of the words.  We don't want to use the average
    # since sometimes whisper will include non-verbal bits in the timing and
    # skew it long, as in "AHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH" for 29
    # seconds.    
    #med_duration = median([x['end'] - x['start'] for x in words if x['end'] - x['start'] > 0])
    med_duration = 0.2
    last_end = 0
    for i, w in enumerate(words):
        if w['end'] - w['start'] == 0:
            # find the next word with a valid duration.
            nduration = 0
            for j, x in enumerate(words[i:]):
                if x['end'] - x['start'] > 0.02:
                    logging.debug(f"Found next real word for {i}, {w} at: {j + i}, {x}, {last_end}")
                    nduration = (x['start'] - last_end) / j
                    break
            else:
                logging.debug(f"Cannot find a next real word...so just use median duration {med_duration}")
                nduration = med_duration

            w['end'] = w['start'] + nduration
            for j, x in enumerate(words[i + 1:]):
                if x['start'] == w['start']:                    
                    x['end'] = x['start'] = w['end']
            logging.debug(f"New word: {w}")
        last_end = w['end']


def words2phrases(words: list, phrase_gap: float=1.5, max_duration: float=3) -> list:
    """Convert a list of words to readable phrases which can be used for subtitling
    Each word in words consists of:
    * start and end:  in seconds
    * word: the text of the word
    * speaker: optional.  Another split point.
    
    The words are grouped into phrases separated by the number of seconds specified
    by the phrase_gap parameter or if the speaker changes.  
    If the phrases are longer than max_duration, they
    are further split into smaller phrases, on punctuation if possible.
    
    Returns a list of phrases, each consisting of start, stop, and text, suitable
    for sending through gen_vtt
    """
    # Group words together into phrases based on the phrase gap and speaker.
    phrases = []
    buffer = []
    last_end = None
    last_speaker = None
    #alignwords(words)
    #for word in sorted(words, key=lambda x: x['start']):
    for word in words:
        speaker = word.get('speaker', None)
        if speaker != last_speaker:
            # we have to split on speaker, regardless of the length
            if not buffer:
                # first word in the buffer for this speaker
                buffer.append(word)
            else:
                phrases.append({'start': buffer[0]['start'],
                                'end': buffer[-1]['end'],
                                'phrase': buffer,
                                'speaker': last_speaker})
                buffer = [word]
        else:
            if last_end == None or (word['start'] - last_end) < phrase_gap:
                # append to the current phrase
                buffer.append(word)
            else:
                # the gap's too big so start a new buffer
                phrases.append({'start': buffer[0]['start'],
                                'end': buffer[-1]['end'],
                                'phrase': buffer,
                                'speaker': last_speaker})
                buffer = [word]
        last_end = word['end']
        last_speaker = speaker
    # catch any leftover words in the buffer
    if buffer:
        phrases.append({'start': buffer[0]['start'],
                        'end': buffer[-1]['end'],
                        'phrase': buffer,
                        'speaker': last_speaker})

    # Now that we have a list of phrases, we need to rephrase them to be 
    # usable chunks
    results = []
    for p in phrases:
        logging.debug(p)
        results.extend([{'start': x['start'],
                         'end': x['end'],
                         'text': renderwords(x['phrase']),
                         'speaker': x['speaker']} for x in splitphrase(p, max_duration)])
        logging.debug(results)
    return results


def renderwords(words: list) -> str:
    """Given a list of words concatenate them together in a way that is
    pleasing."""
    text = ""    
    for w in [x['word'] for x in words]:
        if not text:
            text = w
        else:
            if w[0] in '-%,':
                # these characters are directly appended to the previous
                # word.
                text += w
            else:
                text += " " + w
    return text


def splitphrase(phrase: dict, max_duration: float) -> list:
    """Split a phrase into phrases which are less than the max_duration.
    
    The phrases are split into smaller phrases if they overrun the max_duration.
    If possible, the phrase will end on punctuation so each phrase will be a
    (semi-)complete thought.  If that's not possible, then we have to split it
    where it falls because we don't want to overrun the reader's brain.
    """
    results = []
    start = duration = 0
    buffer = []
    #logging.debug(f"Phrase: {phrase['phrase']}")
    for word in phrase['phrase']:
        # add the next word to the buffer
        if not buffer:
            buffer.append(word)
            start = word['start']
            duration = word['end'] - word['start']
        else:
            duration = word['end'] - start
            buffer.append(word)
        # check the duration...
        if duration < 0.01:
            logging.debug(f"Found zero duration word: {word}")
        if duration > max_duration:
            if buffer[-1]['word'][-1] in '.,?!':
                # if the last word ends in punctuation, we'll let it
                # slide and start a new phrase.
                results.append(buffer)
                buffer = []
            else:
                # we need to back up a bit to find the last punctuated word
                for i in range(1, len(buffer) - 1):
                    if buffer[-i]['word'][-1] in '.,?!':
                        # found punctation word, so push all of the words up to
                        # that one and reset the buffer to contain the rest.
                        results.append(buffer[0 : -i + 1])
                        buffer = buffer[-(i - 1):]
                        duration = buffer[-1]['end'] - buffer[0]['start']
                        start = buffer[0]['start']
                        break
                else:
                    # we didn't find a puncutated word, so we'll just split it here.
                    results.append(buffer)
                    buffer = []

    # pick up anything that's leftover
    if buffer:
        results.append(buffer)

    # convert the results into phases....
    phrases = []
    for r in results:
        phrases.append({'start': r[0]['start'],
                        'end': r[-1]['end'],
                        'speaker': phrase['speaker'],
                        'phrase': r})
    
    return phrases


#
# Old implementation follows.  Needs to be removed at some point.
#

# Get the header of the vtt file
def get_header():
    return "WEBVTT"+"\n"
                
# Get a new line of the vtt text
def get_line(speaker, text):    
    return "<v "+speaker+">"+text+"\n" if speaker else text+"\n"

# Get an empty line to the vtt output
def get_empty_line():
    return "\n"

# Get a time entry to the vtt output
def get_time(start_time, end_time):
    return convert(start_time) + " --> "+ convert(end_time) + "\n"
    
# Convert seconds to HH:MM:SS.fff string
def convert(seconds): 
    # get milliseconds str
    ms = str(int(seconds * 1000))[-3:] if seconds else "000"    
    # get %H:%M:%S timestamp
    ts = time.strftime("%H:%M:%S", time.gmtime(seconds))
    return ts + "." + ms
