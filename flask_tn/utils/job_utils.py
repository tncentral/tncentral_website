import os
import re
import shutil
import time
import zipfile
from werkzeug.utils import secure_filename
from subprocess import PIPE, run
from secrets import token_hex



def get_new_job(job_folder, job_prefix=""):
    """
    Generates a new unique job identifier.

    This function generates a new job ID using a random token, optionally
    prefixed with a provided string. It checks if the generated job ID
    already exists as a folder within the specified job folder and ensures
    the uniqueness of the generated job ID.

    Parameters:
    job_folder (str): The folder where job folders are stored.
    job_prefix (str, optional): An optional prefix for the job ID.

    Returns:
    str: A unique job identifier.
    """
    job_id = ""  # Initialize the job ID
    number_of_tries = 2000  # Maximum number of attempts to find a unique job ID
    count_tries = 1  # Initialize the try count
    
    while True:
        # Generate a random token (hex) as the job ID
        job_id = token_hex(3).upper()
        
        # Prefix the job ID with the provided prefix, if any
        if job_prefix:
            job_id = job_prefix + job_id
        
        # Form the path for the new job folder
        new_job = os.path.join(job_folder, job_id)
        
        # Check if the path does not exist and the maximum tries have not been reached
        if not os.path.exists(new_job) and count_tries < number_of_tries:
            break  # Exit the loop if conditions are met
        else:
            count_tries += 1  # Increment try count if conditions are not met
    
    return job_id  # Return the generated unique job identifier


from flask_tn.db_models import Te_Entry, Te_Orf
from flask_tn.exceptions import InvalidFileException
from subprocess import run, PIPE
import re

def check_fasta(f_path:str):
    with open(f_path, "r") as reader:
        first_line = reader.readline()
        first_line = first_line.strip()
        if not re.match("^>\s*\w+", first_line):
            raise InvalidFileException(f_path, "The file provided is not a fasta file.")

def check_textfile(f_path:str):
    output = run(f"file -b {f_path}", stdout=PIPE, stderr=PIPE,shell=True)
    stdout = output.stdout.decode("utf-8")
    if not stdout.lower().startswith("ascii text"):
        raise InvalidFileException(f_path, "The file provided is not a text file.")

def upload_fasta_blast(upload_folder, request_file, job_id):
    """
    Uploads a FASTA file for a BLAST job.

    This function takes a request file (FASTA format), a destination folder,
    and a job ID, and saves the uploaded file with the provided job ID
    in the specified upload folder.

    Parameters:
    upload_folder (str): The destination folder where the file will be saved.
    request_file (FileStorage): The uploaded FASTA file from the request.
    job_id (str): The unique identifier for the job.

    Returns:
    str: The path to the saved job file.
    """
    # Secure the filename to prevent any potential security vulnerabilities
    filename = secure_filename(request_file.filename)
    
    # Create the full path to save the uploaded file
    filename = os.path.join(upload_folder, filename)
    request_file.save(filename)
    try:
        check_textfile(filename)
        check_fasta(filename)
        job_file = os.path.join(upload_folder, job_id + ".fa")
        shutil.copyfile(filename, job_file)
    except InvalidFileException as exc:
        raise
    
    return job_file
    

def create_fasta_blast(upload_folder, sequence, job_id):
    job_file = os.path.join(upload_folder, job_id+".fa")
    with open(job_file, "w") as writer:
        writer.write(f">{job_id}\n")
        lines = sequence.split('\n')
        has_symbol = False
        for line in lines:
            if not line.startswith('>'):
                writer.write(f"{line}\n")
            else:
                if has_symbol: # if there is more than one sequence
                    writer.write(f"{line}\n")
                has_symbol = True
    return job_file

from datetime import datetime, timezone
def update_blast_info(file, text, print_time=True,extra_info=None):
    with open(file, "a") as writer:
        dt = datetime.now(timezone.utc)
        writer.write(text)
        if print_time:
            writer.write(f"\t{dt.strftime('%m/%d/%Y %H:%M:%S')}")
        if extra_info:
            writer.write(f"\t{extra_info}")
        writer.write("\n")

def update_blast_error(file, text):
    with open(file, "a") as writer:
        writer.write(f"{text}\n")

from rq.command import send_stop_job_command
def on_success_blast(job, connection, result, *args, **kwargs):
    job_meta = job.get_meta(refresh=True)
    update_blast_info(job_meta['info_file'], "Ended at")

def on_failure_blast(job, connection, type, value, traceback):
    job_meta = job.get_meta(refresh=True)
    update_blast_info(job_meta['info_file'], "Failed at", print_time=False,extra_info=str(value))
    update_blast_info(job_meta['error_file'], str(value), print_time=False)

def on_stopped_blast(job, connection):
    job_meta = job.get_meta(refresh=True)
    update_blast_info(job_meta['info_file'], "Stopped at", print_time=False)

def stop_job(job_id, connection):
    send_stop_job_command(connection, job_id)

import re
import os
import signal
def stop_blast_command(job_id:str):
    local_command = "ps -auxfww"
    cmd_output = run(f"{local_command}",stdout=PIPE,stderr=PIPE,shell=True)
    if cmd_output.returncode == 0:
        lines = cmd_output.stdout.decode('ascii').split('\n')
        pids = []
        for line in lines:
            if line.rfind(f'{job_id}/{job_id}.fa -gapopen') != -1:
                ps = re.split('\s+', line)
                pids.append(int(ps[1]))
    try:
        cmd_output = run(["/usr/bin/kill","-9",str(pids[0])],stdout=PIPE,stderr=PIPE)
        print("stdout: "+cmd_output.stdout.decode('ascii'))
        print("stderr: "+cmd_output.stderr.decode('ascii'))
    except Exception as exc:
        print("----------------------deu BO")
        print(exc)
        print("----------------------------")

def format_blast_parameters(program, n_display, expect, word, comp_based,filter1,
                            filter2, lcase_mask, scores, matrix, gap_extend):
    formatted_p = f"-p {program}"
    # program, n_display, expect, word,
    # comp_based, filter1, filter2, lcase_mask, scores, matrix, gap_extend
    if n_display:
        formatted_p += f" -v {n_display}"
        formatted_p += f" -b {n_display}"
    
    if expect and expect != '10': # default 10
        formatted_p += f" -e {expect}"
    
    if word and word != '0': # default 0
        formatted_p += f" -W {word}"
        
    if filter1 or filter2:
        formatted_p += ' -F '+(filter1+filter2)

    if lcase_mask:
        formatted_p += ' -U T'
    
    if program == "blastp": 
        if matrix != "BLOSUM62": # default BLOSUM62
            formatted_p += f" -M {matrix}"
         # TODO check this parameter
        if comp_based == "no":
            formatted_p += " -C 0"
            
    else:
        scores = scores.split(',')
        reward = scores[0] # -r
        penalty = scores[1] # -q
        formatted_p += f' -r {reward} -q {penalty}'
    
    if gap_extend:
        gap_extend = gap_extend.split(',')
        formatted_p += f" -G {gap_extend[0]}"  # cost of opening gap
        formatted_p += f" -E {gap_extend[1]}" # extend gap cost

   
    return formatted_p

def is_nucleotide(sequence=None, file=None):
    """
    Checks if a given sequence or sequences in a file contain valid nucleotides.

    This function determines whether a given sequence (provided as a string)
    or sequences within a file contain valid nucleotide characters. It scans
    each line of the input sequence(s), excluding lines with ">" headers if
    present. If any invalid nucleotide characters are found, the function
    returns False. Otherwise, it returns True.

    Parameters:
    sequence (str, optional): The sequence containing nucleotides.
    file (str, optional): The path to a file containing sequence(s).

    Returns:
    bool: True if all nucleotides are valid, False otherwise.
    """
    is_nuc = True  # Initialize the nucleotide validity flag
    pattern = "B|D|E|F|H|I|K|L|M|N|P|Q|R|S|V|W|Y|Z"  # Invalid nucleotide pattern

    # Check if input is from a file
    if file is not None:
        sequence = ""  # Initialize sequence to be read from the file
        with open(file, "r") as reader:
            for line in reader:
                if re.search("^\s*>.+$", line) is not None:
                    pass  # Skip lines with ">" headers
                elif re.search(pattern, line, re.I) is not None:
                    is_nuc = False
                    break  # Invalid nucleotide found, break the loop
    else:  # Sequence is provided as a string
        lines = sequence.split('\n')
        for line in lines:
            if re.search("^\s*>.+$", line) is not None:
                pass  # Skip lines with ">" headers
            elif re.search(pattern, line, re.I) is not None:
                is_nuc = False
                break  # Invalid nucleotide found, break the loop

    return is_nuc  # Return the nucleotide validity status

def run_blast(commands):    
    from subprocess import PIPE, Popen
    from rq import get_current_job
    from rq.job import JobTimeoutException

    stdout=""
    with Popen(commands, shell=True, stdout=PIPE, stderr=PIPE) as process:
        try:        
            job = get_current_job()
            job_meta=job.get_meta(refresh=True)
            update_blast_info(job_meta['info_file'], "Started at")
            stdout, stderr = process.communicate()
            if stderr:
                job.meta['stderr']=stderr
                job.save_meta()
        except JobTimeoutException as exc:
            update_blast_info(job_meta['error_file'], str(exc), print_time=False)
            job.meta['stderr']=str(exc)
            job.save_meta()
        except Exception as err:
            job.meta['stderr']=str(err)
            job.save_meta()
        finally:
            update_blast_info(job_meta['info_file'], "Ended at")
    return stdout

def blast_result_file(dir_jobs, job_id):
    return os.path.join(dir_jobs, job_id, job_id+".fa.out")


def get_dict_from_info(filepath):
    return_dict = {}
    with open(filepath) as reader:
        for line in reader:
            cols = line.rstrip('\n').split("\t")
            return_dict[cols[0]]=cols[1]
    return return_dict

def clean_jobs(dir_jobs, cron_days = 60):
    import os, shutil
    from datetime import datetime, timezone
    from flask import current_app
    import worker
    from rq import Queue
    from rq.job import Job

    removed_jobs = 0
    for job in os.listdir(dir_jobs):
        dir_job = os.path.join(dir_jobs, job)
        info_ext = current_app.config['RQ_INFO_EXT']
        info_file = os.path.join(dir_job, f"{job}.{info_ext}")
        is_removeable = False
        if os.path.exists(info_file):
            info_dict = get_dict_from_info(info_file)
            if "Ended at" in info_dict:
                dt_now = datetime.now(timezone.utc)
                dt_ended = datetime.strptime(info_dict["Ended at"], "%m/%d/%Y %H:%M:%S")
                diff = dt_now.date()-dt_ended.date()
                if diff.days >= cron_days:
                    is_removeable = True
            elif "Started at" in info_dict:
                dt_now = datetime.now(timezone.utc)
                dt_ended = datetime.strptime(info_dict["Started at"], "%m/%d/%Y %H:%M:%S")
                diff = dt_now.date()-dt_ended.date()
                if diff.days >= cron_days:
                    is_removeable = True
            elif "Enqueued at" in info_dict:
                dt_now = datetime.now(timezone.utc)
                dt_ended = datetime.strptime(info_dict["Enqueued at"], "%m/%d/%Y %H:%M:%S")
                diff = dt_now.date()-dt_ended.date()
                if diff.days >= cron_days:
                    is_removeable = True
            else:
                is_removeable = True
        else:
            is_removeable = True

        if is_removeable:
            shutil.rmtree(dir_job)
            removed_jobs += 1
            try:
                rq_job = Job.fetch(job, worker.conn)
                rq_job.delete()
            except:
                pass
    print(f"{removed_jobs} job", end="")
    if removed_jobs > 1:
        print("s have been removed.")
    else:
        print(" has been removed.")

def get_blast_result(dir_jobs, job_id):
    job_file = blast_result_file(dir_jobs, job_id)
    lines = ""
    with open(job_file, "r") as reader:
        for line in reader:
            line = line.replace(" ", "&nbsp;")
            lines += line+"<br>"
    return lines

# for rq queue
def recreate_blast():
    import os
    from subprocess import PIPE, run
    from flask_tn import create_app
    app = create_app()
    app.app_context().push()

    cmd_makeblastdb = app.config["CMD_MAKEBLASTDB"]
    base_dir = app.config["TNC_BASE_DIR"]
    current_dir = app.config["TNC_CURRENT_DIR"]
    fasta_dir = os.path.join(current_dir, app.config["TNC_FASTA_DIR"])
    # fasta_nc = app.config["TNC_FASTA_FILE"]
    blast_basename = app.config["BLAST_NAMEBASE"]
    fasta_nc = blast_basename +".fa"
    fasta_prot = blast_basename +".prot.fa"
    ext_nc_to_remove = ["nhr", "nin", "nog", "nsd", "nsi", "nsq"]
    ext_prot_to_remove = ["phr", "pin", "psq"]

    # recreate tncentral.fa
    fasta_final = os.path.join(current_dir, fasta_nc)
    remove_blast_files(fasta_final, ext_nc_to_remove)

    command = f"cat {fasta_dir}/*.fa > {fasta_final}"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)

    command = f"{cmd_makeblastdb} -in {fasta_final} -dbtype nucl -parse_seqids"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
    create_blast_zip(current_dir, fasta_nc, ext_nc_to_remove, "nc")

    external_nc = app.config["EXTERNAL_NC_BLAST"]
    full_fasta_base = f"{blast_basename}_{'_'.join(list(external_nc.keys()))}.fa"
    full_fasta = os.path.join(current_dir, full_fasta_base)
    remove_blast_files(full_fasta, ext_nc_to_remove)
    result = run(f"cat {fasta_final} >> {full_fasta}", stdout=PIPE, stderr=PIPE, shell=True)

    for key, value in external_nc.items():
        ext_path = os.path.join(base_dir, value)
        result = run(f"{app.config['PERL']} -pi -e 's/\r//g' {ext_path}", stdout=PIPE, stderr=PIPE, shell=True)
        base_name = f"{blast_basename}_{key}.fa"
        new_fasta = os.path.join(current_dir, base_name)
        remove_blast_files(new_fasta, ext_nc_to_remove)
        result = run(f"cat {fasta_final} > {new_fasta}", stdout=PIPE, stderr=PIPE, shell=True)
        result = run(f"cat {ext_path} >> {new_fasta}", stdout=PIPE, stderr=PIPE, shell=True)
        result = run(f"cat {ext_path} >> {full_fasta}", stdout=PIPE, stderr=PIPE, shell=True)
        
        command = f"{cmd_makeblastdb} -in {new_fasta} -dbtype nucl -parse_seqids"
        result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
        create_blast_zip(current_dir, base_name, ext_nc_to_remove, "nc")
    
    command = f"{cmd_makeblastdb} -in {full_fasta} -dbtype nucl -parse_seqids"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
    create_blast_zip(current_dir, full_fasta_base, ext_nc_to_remove, "nc")

    fasta_prot_final = os.path.join(current_dir, fasta_prot)
    remove_blast_files(fasta_prot_final, ext_prot_to_remove)
    
    with open(fasta_prot_final, "w") as writer:
        list_entries = Te_Entry.query.filter_by(in_production=1, entry_id_parent=None).all()
        for entry in list_entries:
            list_orf = Te_Orf.query.filter_by(entry_id=entry.entry_id).all()
            accession = entry.accession
            for (idx,orf) in enumerate(list_orf):
                sequence = orf.sequence
                sequence = sequence.replace(" ", "")
                writer.write(f">{accession}|{idx+1}\n")
                writer.write(f"{sequence}\n")
    command = f"{cmd_makeblastdb} -in {fasta_prot_final} -dbtype prot"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
    create_blast_zip(current_dir, fasta_prot, ext_prot_to_remove, "")

    external_aa = app.config["EXTERNAL_AA_BLAST"]
    for key, value in external_aa.items():
        ext_path = os.path.join(base_dir, value)
        result = run(f"{app.config['PERL']} -pi -e 's/\r//g' {ext_path}", stdout=PIPE, stderr=PIPE, shell=True)
        base_name = f"{blast_basename}_{key}.prot.fa"
        new_fasta = os.path.join(current_dir, base_name)
        remove_blast_files(new_fasta, ext_prot_to_remove)
        result = run(f"cat {fasta_prot_final} > {new_fasta}", stdout=PIPE, stderr=PIPE, shell=True)
        result = run(f"cat {ext_path} >> {new_fasta}", stdout=PIPE, stderr=PIPE, shell=True)
        command = f"{cmd_makeblastdb} -in {new_fasta} -dbtype prot"
        result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
        create_blast_zip(current_dir, base_name, ext_prot_to_remove, "")

def remove_blast_files(file, exts):
    if os.path.exists(file):
        os.remove(file)
    for ext in exts:
        file_to_remove = os.path.join(file + "." + ext)
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)
def create_blast_zip(current_dir, filename, exts, preffix="nc"):
    if preffix:
        zip_name = preffix+"_"+filename+".zip"
    else:
        zip_name = filename+".zip"
    zip_name = os.path.join(current_dir, zip_name)
    if os.path.exists(zip_name):
        os.remove(zip_name)
    with zipfile.ZipFile(zip_name, 'w') as myzip:
        file_to_add = os.path.join(current_dir, filename)
        myzip.write(file_to_add, filename)
        for ext in exts:
            new_file = filename + "." + ext
            file_to_add = os.path.join(current_dir, new_file)
            if os.path.exists(file_to_add):
                myzip.write(file_to_add, new_file)

# for rq queue
def export_pubmed_files():
    import requests
    import os
    from flask_tn import create_app
    app = create_app()
    app.app_context().push()
    from flask_tn.ext.database import db
    from flask_tn.db_models import Te_Pubmed
    from flask_tn.utils import gb_utils
    base_dir = app.config["TNC_BASE_DIR"]
    dir_pubmed = os.path.join(base_dir, app.config["TNC_PUBMED_DIR"])

    list_pubmed = Te_Pubmed.query.filter_by(title=None)
    for pubmed_obj in list_pubmed:
        pubmed_id = str(pubmed_obj.pubmed_id)
        pub_path = os.path.join(dir_pubmed, pubmed_id)
        response = None
        if not os.path.exists(pub_path):
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            url = f"{url}?db=pubmed&id={pubmed_id}&retmode=text&rettype=medline"
            timeout = 20
            headers = {"User-agent": "Mozilla/5.0"}
            response = requests.get(url=url, headers=headers, timeout=timeout)
            time.sleep(1)
            with open(pub_path, "w") as writer:
                list_lines = response.text.split("\n")
                writer.write(response.text)
        else:
            list_lines = gb_utils.get_lines(pub_path)
        pubmed_dict = gb_utils.get_pubmed_from_lines(list_lines)

        pubmed_obj.title = pubmed_dict["title"]
        pubmed_obj.authors = pubmed_dict["authors"]
        pubmed_obj.summary = pubmed_dict["summary"]
        db.session.commit()
    
def check_job_by_info(filepath, check_key="Ended at"):
    with open(filepath) as reader:
        file_hash = {}
        for line in reader:
            line = line.rstrip("\n")
            cols = line.split('\t')
            file_hash[cols[0]]=cols[1]
        if check_key in file_hash:
            return True
    return False

def get_job_error_by_file(filepath):
    lines = ""
    with open(filepath) as reader:
        lines = reader.readlines()
    return lines
            