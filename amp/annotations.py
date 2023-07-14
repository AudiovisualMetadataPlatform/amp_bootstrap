"""
Additive Annotations
"""
from pathlib import Path
from .fileutils import read_json_file, write_json_file
from time import time
import subprocess
import json
import logging
import copy

class Annotations:
    def __init__(self, annotation_file, media_file=None,
                 mgm_name=None, mgm_version=None, params: dict=None,
                 load_only=False):
        "Load or Create an annotation file"        
        self.load_only = load_only
        if load_only:
            # don't contruct anything, just load it and save it
            self.data = read_json_file(annotation_file)
            return
        
        assert media_file is not None, "Media file must be specified"
        assert mgm_name is not None, "MGM name must be specified" 
        assert mgm_version is not None, "MGM version must be specified"
        if params is None:
            params = {}
        
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
        self.mgm_id = self._new_mgmid() 
        self.data['mgms'][self.mgm_id] = {
            'name': mgm_name,
            'version': mgm_version,
            'start': time(),
            'end': 0,
            'params': params,
        }


    def save(self, filename):
        "save the annotations file"
        if not self.load_only:
            # don't update the mgm end time
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


    def filter(self, start: float=None, end: float=None, atype=None, invert=False):
        "Filter annotations and return them"
        results = []
        for a in self.data['annotations']:
            keep = True            
            if start is not None and a['start'] < start:
                keep = False
            if end is not None and a['end'] > end:
                keep = False
            if atype is not None:
                if type(atype) == str and a['type'] != atype:
                    keep = False
                elif type(atype) in (list, set) and a['type'] not in atype:
                    keep = False
            if invert:
                keep = not keep
            if keep:
                results.append(a)
        return results




    def merge(self, other):
        "Merge the other annotation into this one"
        for other_mgm in other.data['mgms']:
            # if this MGM is the exact same as an MGM we already have
            # then we skip it because we have those annotations
            duplicate_mgm = False
            for smgm in self.data['mgms']:
                if self.data['mgms'][smgm] == other.data['mgms'][other_mgm]:
                    logging.info(f"Our MGM {smgm} is the same as the merging MGM {other_mgm}: skipping")
                    duplicate_mgm = True
                    break
            if duplicate_mgm:
                continue
            
            newid = self._new_mgmid()
            logging.info(f"Copying annotations for MGM {other_mgm} as {newid}")
            # copy the MGM
            self.data['mgms'][newid] = copy.deepcopy(other.data['mgms'][other_mgm])
            # copy the annotations
            for anno in other.data['annotations']:
                if anno['mgm'] == other_mgm:
                    t = copy.deepcopy(anno)
                    t['mgm'] = newid
                    self.data['annotations'].append(t)


    def _new_mgmid(self):
        "Generate a new MGM id"
        i = 0
        while f'mgm{i}' in self.data['mgms']:
            i += 1
        return f"mgm{i}"