# File utilities

import json

def read_json_file(input_file):
    "Read/parse the given JSON input_file and return the validated JSON dictionary"
    with open(input_file, 'r', encoding='utf8') as file:
        input_json = json.load(file)
    return input_json
        
                 
def write_json_file(object, output_file):
    "Serialize the given object and write it to the given JSON output_file"
    with open(output_file, 'w', encoding='utf8') as file:
        json.dump(object, file, indent = 4, default = lambda x: x.__dict__)
        

def write_text_file(string, output_file):
    "Write the given string to the given text output_file"
    with open(output_file, 'w', encoding='utf8') as file:
        file.write(string)