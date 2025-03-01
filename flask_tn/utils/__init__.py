import pathlib
from subprocess import PIPE, run
import requests, json

def get_dir_by_ext(app_config, ext):
    directory = app_config['TNC_FASTA_DIR']
    if ext == "genbank" or ext == "gb":
        directory = app_config['TNC_GENBANK_DIR']
    elif ext == "csv":
        directory = app_config['TNC_CSV_DIR']
    elif ext == "dna":
        directory = app_config['TNC_SNAP_DIR']
    return directory

def rm_carriage(filename, perl_command="perl"):
   command = f"{perl_command} -pi -e 's/\r//g' '{filename}'"
   result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
   return result

import os
def join_and_create_folder(*args):
    local_folder = os.path.join(*args)
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)
    return local_folder

def download_pubmed_file(pmid):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    url = f"{url}?db=pubmed&id={pmid}&retmode=text&rettype=medline"
    timeout = 20
    headers = {"User-agent": "Mozilla/5.0"}
    response = requests.get(url=url, headers=headers, timeout=timeout)
    return response

def save_pubmed_file(response, filepath):
    if not response.text.startswith("ID+list+is+empty!"):
        with open(filepath, "w") as writer:
            writer.write(response.text)
        return True
    return False

from werkzeug.datastructures import MultiDict
def get_request_value(request_dict:MultiDict, arg_name:str) -> str:
    """
        The main idea of this function is to avoid exceptions
        in case arg_name is not a key in request.args.
        @param request_dict: The MultiDict object from request.args or request.form
        @param arg_name: Name of the key to get the value from request.args or request.form
        @return: value from request.args.get(arg_name);
                    return an empty string if arg_name is not in request.args
    """
    value = "" # Initialize value as an empty string.
    # Check if the argument name is present in the request_dict object.
    if arg_name in request_dict:
        value = request_dict.get(arg_name)
    return value

def is_human(secret, captcha_response):
    """ Validating recaptcha response from google server
        Returns True captcha test passed for submitted form else returns False.
    """
    payload = {'response':captcha_response, 'secret':secret}
    response = requests.post("https://www.google.com/recaptcha/api/siteverify", payload)
    response_text = json.loads(response.text)
    return response_text['success']

# def get_form_value(request_form, form_name):
#     """
#         The main idea of this function is to avoid exceptions
#         in case form_name is not a key in request.args.
#         request_form: It is an copy of a request.form or a request.args object.
#         form_name: the name of input from the html page.
#     """
#     value = ""
#     if request_form.get(form_name):
#         value = request_form.get(form_name)
#     return value

def create_directory(dir):
    obj_path = pathlib.Path(dir)
    if not obj_path.exists():
        obj_path.mkdir()

def get_dict_from_type(mobile_type):
    type_array = mobile_type.split(":")
    dict_return = {}
    dict_return['type']=type_array[0].strip()
    dict_return['name']=":".join(type_array[1:])
    return dict_return

def update_column_value(obj, column_name, new_value):
    if type(column_name) is not list:
        column_name = [ column_name ]
        new_value = [new_value]
    for idx in range(0,len(column_name)):
        if obj.__getattribute__(column_name[idx]) != new_value[idx]:
            obj.__setattr__(column_name[idx],new_value[idx])

def reverse_complement(sequence):
    # complement strand
    rev_comp = ""
    for i in sequence.lower():
        if i == "a":
            rev_comp += "t"
        elif i == "c":
            rev_comp += "g"
        elif i == "t":
            rev_comp += "a"
        elif i == "g":
            rev_comp += "c"
    # reverse strand
    rev_comp = rev_comp[::-1]
    return rev_comp

def compare_entries(entry1, list_entries):
    eq_entries = False
    for entry in list_entries:
        cmp1 = entry1.name == entry.name
        cmp2 = entry1.start == entry.start
        cmp3 = entry1.end == entry.end
        if cmp1 and cmp2 and cmp3:
            eq_entries = True
            break
    return eq_entries

def is_gzipped(file_path):
    obj_path = pathlib.Path(file_path)
    if obj_path.exists() and ".gz" in obj_path.suffixes:
        return True
    return False

def new_release_number(upload_path):
    files = pathlib.Path(upload_path).iterdir()
    return len(list(files))+1
