import csv
from os.path import exists
from pathlib import Path
import logging, json

def create_csv_from_dict(filename, data):
    logging.info(f"Creating file {filename}")
    longestlen = 0
    longestlenindex = 0
    for i, t in enumerate(data):
        if len(t) > longestlen:
            longestlen = len(t)
            longestlenindex = i
    if len(data[longestlenindex]) > 0:
        fieldnames = data[longestlenindex].keys()
    writer = csv.DictWriter(open(filename, 'w'), fieldnames=fieldnames)
    writer.writeheader()
    for d in data:
        writer.writerow(d)
    logging.info(f"File created: {filename}")

def is_file_existed(file_path):
    logging.info(f"Checking if file {file_path} existed.")
    if not exists(file_path):
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
        return csv.DictReader(open(filename, 'r'))
    else:
        raise Exception(f"File {filename} not found!!")
