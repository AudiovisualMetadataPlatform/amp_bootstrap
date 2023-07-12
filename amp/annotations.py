"""
Additive Annotations
"""
from pathlib import Path
from .fileutils import read_json_file, write_json_file
from time import time
import subprocess
import json
import logging

class Annotations:
    def __init__(self, annotation_file, media_file,
                 mgm_name, mgm_version, params: dict):
        "Load or Create an annotation file"
        media_file = Path(media_file)
        if annotation_file is None or not Path(annotation_file).exists():
            # create an empty one.                    
            self.data = {
                'media': {
                    'filename': str(media_file.absolute()),
                    'size': media_file.stat().st_size,
                    'mtime': media_file.stat().st_mtime,
                    'duration': 0,
                    'mime': 0,
                    'probe': None
                },
                'mgms': {},
                'annotations': []
            }

            # populate the duration and probe data
            try:
                p = subprocess.run(["ffprobe", "-print_format", "json", 
                                    "-show_streams", '-show_format', str(media_file.absolute())],
                                    encoding='utf-8', check=True, stdout=subprocess.PIPE, 
                                    stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                probe = json.loads(p.stdout)
                if 'duration' in probe['format']:
                    self.data['media']['duration'] = float(probe['format']['duration'])
                else:
                    for stream in probe['streams']:
                        if stream['codec_type'] in ("video", "audio"):
                            self.data['media']['duration'] = float(stream['duration'])
                            break
                    else:
                        logging.error("This is not a file with a video in it")
                        exit(1)
                self.data['media']['probe'] = probe
            except Exception as e:
                # log the exception and just let it continue.
                logging.warning(f"Cannot probe {media_file.absolute()!s}: {e}")
                
            # populate the mimetype
            p = subprocess.run(['file', '--mime-type', '-b', str(media_file.absolute())],
                               stdout=subprocess.PIPE, encoding='utf-8', check=True)
            self.data['media']['mime'] = p.stdout.splitlines()[0]
        else:
            # this must be a continuation of a previous annotation
            # TODO: check against a schema
            self.data = read_json_file(annotation_file)
        
        # add this mgm.
        i = 0
        while f'mgm{i}' in self.data['mgms']:
            i += 1
        self.mgm_id = f'mgm{i}'
        self.data['mgms'][self.mgm_id] = {
            'name': mgm_name,
            'version': mgm_version,
            'start': time(),
            'end': 0,
            'params': params,
        }


    def save(self, filename):
        "save the annotations file"
        self.data['mgms'][self.mgm_id]['end'] = time()
        # sort annotations by start time to get an accurate picture of what's going on
        self.data['annotations'] = sorted(self.data['annotations'], key=lambda x: x['start'])
        # TODO: check against a schema
        write_json_file(self.data, filename)


    def add(self, start, end, annotation_type, details):
        "Add an annotation"

        self.data['annotations'].append({
            'mgm': self.mgm_id,
            'start': start,
            'end': end,
            'annotation_type': annotation_type,
            'details': details
        })