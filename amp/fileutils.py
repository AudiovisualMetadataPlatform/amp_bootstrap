# File utilities

import json
from pathlib import Path
import os
import logging

# Big note here -- jsonschema is only loaded if it is actually used, so 
# things that can't be run under amp_python.sif will still work, minus
# that functionality.


def read_json_file(input_file, schema=None):
    "Read/parse the given JSON input_file and return the validated JSON dictionary"
    with open(input_file, 'r', encoding='utf8') as file:
        input_json = json.load(file)
    validate_schema(input_json, schema)
    return input_json
        
                 
def write_json_file(object, output_file, schema=None):
    "Serialize the given object and write it to the given JSON output_file"
    validate_schema(object, schema)
    with open(output_file, 'w', encoding='utf8') as file:
        json.dump(object, file, indent = 4, default = lambda x: x.__dict__)    


def validate_schema(data, schema):
    "Validate the data against the supplied schema"
    if schema is None:
        return
    try:
        import jsonschema
        jsonschema.validate(data, schema)
    except ImportError:
        logging.warning("Cannot load jsonschema, skipping validation")


def write_text_file(string, output_file):
    "Write the given string to the given text output_file"
    with open(output_file, 'w', encoding='utf8') as file:
        file.write(string)


def valid_file(file):
    "Return True if the file exists and the size is nonzero"
    file = Path(file)
    return file.exists() and file.stat().st_size > 0

def create_empty_file(file):
    "Create an empty file or truncate it if it exists"
    file = Path(file)
    if file.exists():
        os.truncate(file)
    else:
        file.touch()