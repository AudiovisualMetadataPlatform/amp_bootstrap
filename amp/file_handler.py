import csv
from pathlib import Path
import logging, json
from itertools import chain
import os

def create_csv_from_dict(filename, data):
    logging.info(f"Creating file {filename}")
    fieldnames = list(set(chain.from_iterable(sub.keys() for sub in data)))
    writer = csv.DictWriter(open(filename, 'w'), fieldnames=fieldnames)
    writer.writeheader()
    for d in data:
        writer.writerow(d)
    logging.info(f"File created: {filename}")

def is_file_existed(file_path):
    logging.info(f"Checking if file {file_path} existed.")
    if not os.path.exists(file_path):
        raise Exception(F"File path {file_path} doesn't exists.")
    return True

def read_text_file(file_path):
    logging.info(f"Reading file {file_path}")
    data = ""
    if is_file_existed(file_path):
        with open(file_path, "r") as f:
            data = f.read()
    return data

def get_file_name(file_path):
    return Path(file_path).stem


def read_json_file(file_path):
    logging.info(f"Reading file {file_path}")
    if is_file_existed(file_path):
        return json.load(open(file_path))
    return ""


def read_csv_file(filename):
    logging.info(f"Reading CSV file {filename}")
    if is_file_existed(filename):
        return csv.DictReader(open(filename, 'r', encoding='utf-8-sig'))
    else:
        raise Exception(f"File {filename} not found!!")

def create_json_file(output_path, filename, data):
    Path(output_path).mkdir(parents=True, exist_ok=True)
    json_object = json.dumps(data, indent=2)
    logging.info(f"Creating JSON file {filename}")
    abs_path = os.path.join(output_path, filename)
    with open(abs_path, "w") as outfile:
        outfile.write(json_object)
    return abs_path
