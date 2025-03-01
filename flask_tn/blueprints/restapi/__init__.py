from flask import Blueprint, render_template, request, jsonify, send_file
from flask import current_app
from flask_tn.db_models import External_Resource, Te_Entry, db, Orf_Summary
from flask_tn import utils
import os
import sys
import gzip
import time
from rq.job import Job
from worker import conn
from subprocess import PIPE, run

bp = Blueprint("restapi", __name__, url_prefix="/api")
dir_current = ""

def init_app(app):
    if app.config['URL_PREFIX'] != "/":
        app.register_blueprint(bp, url_prefix=app.config['URL_PREFIX']+"api")
    else:
        app.register_blueprint(bp)
    
    global dir_current

    dir_current = app.config['TNC_CURRENT_DIR']

def build_match_filter(search_text, match_type):
    if match_type == "c":
        search_text = f"%{search_text}%"
    elif match_type == "b":
        search_text = f"{search_text}%"
    elif match_type == "e":
        search_text = f"%{search_text}"
    elif match_type == "q" or match_type == "0":
        search_text = search_text
    else:
        print("Throw an exception")
    return search_text

def build_match_type(match_type):
    if match_type == "1":
        match_type = "insertion sequence"
    elif match_type == "2":
        match_type = "integron"
    elif match_type == "3":
        match_type = "transposon"
    return match_type

@bp.route("/")
def api_base():
    return "OK"

@bp.route("/status/<job_id>")
def job_status(job_id):
    """
        This function checks the status of the blast job submmited to the Redis Queue (RQ)
    """
    return_string = {}
    return_string['exists']='true'

    prefix_ext = current_app.config['RQ_JOB_PREFIX']
    if not job_id.startswith(prefix_ext):
        return_string['exists']='false'
        return jsonify(return_string)

    try:
        job = Job.fetch(job_id, connection=conn)

        if job.is_finished:
            return_string['finished']='true'
            return_string['failed']='false'
        else:
            # Possible values are queued, started, deferred, finished, stopped, scheduled, canceled and failed.
            # If refresh is True fresh values are fetched from Redis.
            if job.get_status() in ["failed", "canceled", "stopped", "deferred"]:
                return_string['finished']='true'
                return_string['failed']='true'
                return_string['status']='finished'
            else:
                return_string['finished']='false'
                return_string['failed']='false'
                return_string['status']=job.get_status()
    except:
        dir_jobs = os.path.join(dir_current, current_app.config['TNC_JOB_DIR'])
        dir_job = os.path.join(dir_jobs, job_id)
        if os.path.exists(dir_job):
            ext_info = current_app.config['RQ_INFO_EXT']
            ext_error = current_app.config['RQ_ERROR_EXT']
            file_info = os.path.join(dir_jobs, job_id,job_id+"."+ext_info)
            file_error = os.path.join(dir_jobs, job_id,job_id+"."+ext_error)
            if os.path.exists(file_error):
                # return_string['exists']='true'
                return_string['finished']='true'
                return_string['failed']='true'
            elif os.path.exists(file_info):
                if utils.job_utils.check_job_by_info(file_info):
                    blast_file = file_info = os.path.join(dir_jobs, job_id,job_id+".fa.out")
                    if os.path.exists(blast_file) and os.path.getsize(blast_file)>16:
                        # return_string['exists']='true'
                        return_string['finished']='true'
                        return_string['failed']='false'
                    else:
                        # return_string['exists']='true'
                        return_string['finished']='true'
                        return_string['failed']='true'
        else:
            return_string['exists']='false'
            return_string['finished']='false'
    return jsonify(return_string)

@bp.route("/blast_out/<job_id>")
def blast_out(job_id):
    dir_jobs = current_app.config['TNC_JOB_DIR']
    dir_jobs = os.path.join(dir_current, dir_jobs)
    return utils.job_utils.get_blast_result(dir_jobs, job_id)

@bp.route("/blast/out/<job_id>")
def blast_file(job_id):
    """
        This function is called by the blast report page to render the chart
        and table.
    """
    dir_jobs = current_app.config['TNC_JOB_DIR']
    dir_jobs = os.path.join(dir_current, dir_jobs)
    # check if the job is finished:
    file = os.path.join(dir_jobs, job_id, job_id+".fa.out")
    lines = ""
    with open(file, "r") as reader:
        for line in reader:
            lines += line
    return lines

@bp.route("/blast/error/<job_id>")
def blast_error(job_id):
    """
        This function is called by the blast report page to render the chart
        and table.
    """
    return_status = {"error": ""}
    try:
        job = Job.fetch(job_id, conn)
        if not job.is_finished and not job.is_started:
            job_meta = job.get_meta(refresh=True)
            if 'stderr' in job_meta:
                return_status['error']=job_meta['stderr']
    finally:
        if return_status['error'] == "":
            error_ext = current_app.config['RQ_ERROR_EXT']
            dir_jobs = current_app.config['TNC_JOB_DIR']
            dir_job = os.path.join(dir_current, dir_jobs, job_id)
            file = os.path.join(dir_job, job_id+"."+error_ext)
            if os.path.exists(file):
                with open(file) as reader:
                    lines = reader.readlines()
                    return_status['error'] = "<br>".join(lines)
    return jsonify(return_status)

@bp.route("/blast/file/<job_id>")
def blast_result_file(job_id):
    """
        This function download the file result from the blast
    """
    dir_jobs = current_app.config['TNC_JOB_DIR']
    perl_command = current_app.config['PERL']
    dir_jobs = os.path.join(dir_current, dir_jobs)
    file = os.path.join(dir_jobs, job_id, job_id+".fa.out")
    new_comm = f"{perl_command} -pi -e 's/^\s*Database: \/.+\/(\S+.fa)$/Database: $1/g' {file}"
    run(new_comm, stdout=PIPE, stderr=PIPE, shell=True)
    return send_file(file, as_attachment=True)

@bp.route("/blast/fasta/<job_id>")
def blast_fasta_file(job_id):
    """
        This function download the file result from the blast
    """
    dir_jobs = current_app.config['TNC_JOB_DIR']
    dir_jobs = os.path.join(dir_current, dir_jobs)
    file = os.path.join(dir_jobs, job_id, job_id+".fa")
    return send_file(file, as_attachment=True)

def is_empty(value):
    return value is None or value.strip() == ""

def get_query_from_drop(query, filter_text, drop_value, db_class, col_name):
    filter_text = build_match_filter(filter_text, drop_value)
    query = query.filter( getattr(db_class, col_name).like(filter_text) )
    return query

@bp.route("/te/")
def get_data():
    """
        This function is the endpoint of the search by Transposable Elements.
        Given the parameters sent by GET method, this function searches the
        database and return the list of transposable elements as a json like
        format with the keys: data, recordsFiltered, recordsTotal, draw.
    """
    query = Te_Entry.query.filter(Te_Entry.entry_id_parent==None, Te_Entry.in_production==1)
    total_query = query.count()
    all_fields = utils.get_request_value(request.args, "all_fields")

    # It's not possible to work with the size of the 
    # request.args because this variable is manipulated
    # by datatable.js and they send a lot of values for
    # their own control. Since we are sending our values together
    # with the table variables we have to check one by one if the value exists
    if all_fields != "":
        query = query.filter(
            db.or_(
                Te_Entry.accession.like(f"%{all_fields}%"),
                Te_Entry.name.like(f"%{all_fields}%"),
                Te_Entry.synonyms.like(f"%{all_fields}%"),
                Te_Entry.type.like(f"%{all_fields}%"),
                Te_Entry.family.like(f"%{all_fields}%"),
                Te_Entry.group.like(f"%{all_fields}%"),
                Te_Entry.organism.like(f"%{all_fields}%"),
                Te_Entry.country.like(f"%{all_fields}%"),
                Te_Entry.date.like(f"%{all_fields}%")
            )
        )
        total_query = query.count()
    else:
        fields_with_drop = {"name":"name", "synon":"synonyms", "family":"family",
                            "group":"group", "accession":"accession", "host": "organism"}
        # for each text with dropdown we check if it's empty and modify the database
        # query.
        for field in fields_with_drop.keys():
            field_value = utils.get_request_value(request.args, field)
            if field_value != "":
                query = get_query_from_drop(query, request.args.get(field),
                            request.args.get("s_"+field), Te_Entry, fields_with_drop[field])

        filter_text = utils.get_request_value(request.args, "s_type")
        if filter_text != "" and filter_text != "0":
            filter_text = build_match_type(filter_text)
            query = query.filter( Te_Entry.type.like(filter_text) )

        filter_text = utils.get_request_value(request.args, "country")
        if filter_text != "":
            query = query.filter( Te_Entry.country.like(f"%{filter_text}%") )
            
        filter_text = utils.get_request_value(request.args, "isolation")
        if filter_text != "":
            query = query.filter( Te_Entry.date.like(f"%{filter_text}%") )
        
        # new case: return internals when searching accession
        chk_internals = utils.get_request_value(request.args, "internals")
        accession = utils.get_request_value(request.args, "accession")
        if chk_internals == "1" and accession != "":
            list_accession = [r.accession for r in query]
            internal_query = Te_Entry.query.filter(Te_Entry.in_production==1,
                                                   Te_Entry.entry_id_parent!=None,
                                                   Te_Entry.accession.in_(list_accession))
            list_internals = [r.entry_id_parent for r in internal_query]
            internal_query = Te_Entry.query.filter(Te_Entry.entry_id.in_(list_internals))
            query = query.union(internal_query)
        # end new case: return internals when searching accession

        total_query = query.count()
    total_filtered = total_query
    # search filter
    search = request.args.get("search[value]")
    if search:
        query = query.filter(
            db.or_(
                Te_Entry.accession.like(f"%{search}%"),
                Te_Entry.name.like(f"%{search}%"),
                Te_Entry.synonyms.like(f"%{search}%"),
                Te_Entry.type.like(f"%{search}%"),
                Te_Entry.family.like(f"%{search}%"),
                Te_Entry.group.like(f"%{search}%"),
                Te_Entry.organism.like(f"%{search}%"),
                Te_Entry.country.like(f"%{search}%"),
                Te_Entry.date.like(f"%{search}%")
            )
        )
        total_filtered = query.count()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f"order[{i}][column]")
        if col_index is None:
            break
        col_name = request.args.get(f"columns[{col_index}][data]")
        view_db = {"select": "entry_id","accession": "accession", "name": "name",
            "synonyms": "synonyms", "type": "type","family": "family",
            "group": "group","organism": "organism",
            "country": "country","date": "date"
        }
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        col = getattr(Te_Entry, view_db[col_name])
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        query = query.order_by(*order)
    
    # # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    query = query.offset(start).limit(length)
    
    
    return {
        "data": [te.datatable() for te in query],
        "recordsFiltered": total_filtered,
        "recordsTotal": total_query,
        "draw": request.args.get("draw", type=int)
    }


@bp.route("/tg/")
def get_gene_data():
    """
        This function is the endpoint of the search by Gene.
        Given the parameters sent by GET method, this function searches the
        database and return the list of transposable elements as a json like
        format with the keys: data, recordsFiltered, recordsTotal, draw.
    """
    # query = Te_Orf.query
    # total_query = Te_Entry.query.count()
    # gene_name = request.args.get("gene_name")
    # gene_class = request.args.get("gene_class")
    # gene_function = request.args.get("gene_function")
    gene_all_fields = utils.get_request_value(request.args, "gene_all_fields")
    gene_name = utils.get_request_value(request.args, "gene_name")
    gene_class = utils.get_request_value(request.args, "gene_class")
    gene_function = utils.get_request_value(request.args, "gene_function")
    start_time = time.time()
    query = Orf_Summary.query
    # query = query.order_by(Entry_Orf.name)
    # query = Entry_Orf.query
    if gene_all_fields != "":
        query = query.filter(
            db.or_(
                Orf_Summary.orf_name.like(f"%{gene_all_fields}%"),
                Orf_Summary.orf_class.like(f"%{gene_all_fields}%"),
                Orf_Summary.subclass.like(f"%{gene_all_fields}%")
            )
        )
    else:
        if gene_name != "":
            query = query.filter(
                Orf_Summary.orf_name.like(f"%{gene_name}%")
            )
            # total_query = query.count()

        if gene_class != "" and gene_class != "0":
            dict_class = {'1': 'Transposase', '2': 'Accessory Gene',
                        '3': 'Integron Integrase', '4':'Passenger Gene',
                        }
            filter = dict_class[gene_class]
            query = query.filter(
                Orf_Summary.orf_class.like(f"%{filter}%")
            )
            # total_query = query.count()
        if gene_function != "" and gene_function != "0":
            dict_class = {'1': 'Antibiotic Resistance', '2': 'ATPase Transposition Helper',
                        '3': 'Heavy Metal Resistance', '4':'Inhibitor',
                        '5': 'Resolvase', '6': 'Other'
                        }
            query = query.filter(
                Orf_Summary.subclass.like(f"%{dict_class[gene_function]}%")
            )
            # total_query = query.count()
    total_query = query.count()
    total_filtered = query.count()

    search = request.args.get("search[value]")
    if search:
        query = query.filter(
            db.or_(
                Orf_Summary.orf_name.like(f"%{search}%"),
                Orf_Summary.orf_class.like(f"%{search}%"),
                Orf_Summary.subclass.like(f"%{search}%"),
                Orf_Summary.target.like(f"%{search}%")
            )
        )
        total_filtered = query.count()
    
    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f"order[{i}][column]")
        if col_index is None:
            break
        col_name = request.args.get(f"columns[{col_index}][data]")
        view_db = {"id": "id","orf_name": "orf_name", "orf_class": "orf_class",
                   "subclass": "subclass", "target": "target",
            
        }
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        col = getattr(Orf_Summary, view_db[col_name])
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        query = query.order_by(*order)

    # # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    query = query.offset(start).limit(length)
    end = time.time()
    # print(f"Time {end - start_time}")
    return {
        "data": [orf.serialize() for orf in query],
        "recordsFiltered": total_filtered,
        "recordsTotal": total_query,
        "draw": request.args.get("draw", type=int),
    }

@bp.route("/tbl_ext/")
def get_ext_table():
    database_name = utils.get_request_value(request.args, "database_name")
    query = External_Resource.query.filter_by(database_name=database_name)
    total_query = query.count()
    total_filtered = total_query

    # search filter
    search = request.args.get("search[value]")
    if search:
        query = query.filter(
            db.or_(
                External_Resource.resource_id.like(f"%{search}%")
            )
        )
        total_filtered = query.count()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f"order[{i}][column]")
        if col_index is None:
            break
        col_name = request.args.get(f"columns[{col_index}][data]")
        # view_db = {"select": "external_id","resource_id": "resource_id"}
        view_db = {"resource_id": "resource_id"}
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        col = getattr(External_Resource, view_db[col_name])
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        query = query.order_by(*order)
    
    # # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    query = query.offset(start).limit(length)
    
    
    return {
        "data": [ext.datatable() for ext in query],
        "recordsFiltered": total_filtered,
        "recordsTotal": total_query,
        "draw": request.args.get("draw", type=int)
    }


@bp.route('/check_direct/<accession>/<ext>')
def check_direct(accession, ext):
    dir_download = utils.get_dir_by_ext(current_app.config,ext)
    file = os.path.join(dir_current, dir_download, accession+f".{ext}")
    if os.path.exists(file):
        return "True"
    else:
        return "False"

@bp.route('/direct_download/<accession>')
def direct_download(accession):
    ext = request.args.get('ext')
    dir_download = utils.get_dir_by_ext(current_app.config,ext)
    # the default format of download is genbank
    file = os.path.join(dir_current, dir_download, accession+f".{ext}")

    return send_file(file, as_attachment=True)

@bp.route('/check_external/')
def check_external():
    database_name = request.args.get('database_name')
    resource_id = request.args.get('resource_id')
    ext = request.args.get('ext')
    resources_dir = os.path.join(dir_current, current_app.config["TNC_RESOURCES_DIR"])
    db_dir = os.path.join(resources_dir, database_name)
    if ext == "fa":
        db_dir = os.path.join(db_dir, current_app.config["TNC_FASTA_DIR"])
    elif ext == "dna":
        db_dir = os.path.join(db_dir, current_app.config["TNC_SNAP_DIR"])
    elif ext == "gb":
        db_dir = os.path.join(db_dir, current_app.config["TNC_GENBANK_DIR"])
    
    file_to_download = resource_id+"."+ext
    full_path = os.path.join(db_dir, file_to_download)
    return_status={}
    if os.path.exists(full_path):
        return_status["status"]="ok"
        return_status["file"]=file_to_download
    else:
        return_status["status"]="error"
        return_status["error"]="File not found."

    return jsonify(return_status)

@bp.route('/download_external/')
def download_external():
    database_name = request.args.get('database_name')
    resource_id = request.args.get('resource_id')
    ext = request.args.get('ext')
    resources_dir = os.path.join(dir_current, current_app.config["TNC_RESOURCES_DIR"])
    db_dir = os.path.join(resources_dir, database_name)
    if ext == "fa":
        db_dir = os.path.join(db_dir, current_app.config["TNC_FASTA_DIR"])
    elif ext == "dna":
        db_dir = os.path.join(db_dir, current_app.config["TNC_SNAP_DIR"])
    elif ext == "gb":
        db_dir = os.path.join(db_dir, current_app.config["TNC_GENBANK_DIR"])
    
    file_to_download = resource_id+"."+ext
    full_path = os.path.join(db_dir, file_to_download)
    return send_file(full_path, as_attachment=True)

@bp.route('/download_external/<db_name>')
def download_external_full(db_name):
    # database = request.args.get('database')
    resources_dir = os.path.join(dir_current, current_app.config["TNC_RESOURCES_DIR"])    
    database_dir = os.path.join(resources_dir, db_name)
    file_path = os.path.join(database_dir, db_name+".zip")
    return send_file(file_path, as_attachment=True)


@bp.route('/check_download/')
def check_download():
    list_acc = request.args.getlist('accession')
    ext = request.args.get('ext')
    len_list = len(list_acc)
    return_status = {}
    if len_list > 0:
        # if the user selected the TE to download: just_hash will receive
        # the folder where the file results.ext.gz is available to download
        file_to_download = generate_list_download(list_acc, ext)
    else:
        # if the user does't select, we will use the
        # parameters from the search to define which files
        # we are going to download
        len_args = len(request.args)
        if len_args == 1: # only ext = download whole database
            file_to_download = get_full_fname(ext)+".zip"
        else:
            file_to_download = generate_search_download(request.args,ext)

    # current_dir = current_app.config["TNC_CURRENT_DIR"]
    full_path = os.path.join(dir_current, file_to_download)
    if os.path.exists(full_path):
        return_status["status"]="ok"
        return_status["file"]=file_to_download
    else:
        return_status["status"]="error"
        return_status["error"]="file_not_found"

    return jsonify(return_status)
    # return send_file(file_to_download, as_attachment=True)

@bp.route('/new_download/')
def new_download():
    file = request.args.get("file")
    # current_dir = current_app.config["TNC_CURRENT_DIR"]
    file_to_download = os.path.join(dir_current, file)
    # list_acc = request.args.getlist('accession')
    # ext = request.args.get('ext')
    # len_list = len(list_acc)
    # if len_list > 0:
    #     # if the user selected the TE to download: just_hash will receive
    #     # the folder where the file results.ext.gz is available to download
    #     file_to_download = generate_list_download(list_acc, ext)
    # else:
    #     # if the user does't select, we will use the
    #     # parameters from the search to define which files
    #     # we are going to download
    #     len_args = len(request.args)
    #     if len_args == 1: # only ext = download whole database
    #         file_to_download = get_full_fname(ext)+".zip"
    #         file_to_download = os.path.join(dir_current, file_to_download)
    #     else:
    #         file_to_download = generate_search_download(request.args,ext)
    # if not os.path.exists(file_to_download):
    #     return render_template("public/file_not_found.html")
    return send_file(file_to_download, as_attachment=True)

@bp.route('/snap_library/<file>')
def download_snap(file):
    file_to_download=""
    base_dir = current_app.config["TNC_BASE_DIR"]
    snapgene = current_app.config["TNC_SNAPGENE_BASE_LIBRARY"]
    upload_snapgene = current_app.config["TNC_UPLOAD_FOLDER"]


    file_to_download = os.path.join(base_dir, snapgene, file)
    if os.path.exists(file_to_download):
        return send_file(file_to_download, as_attachment=True)
    
    file_to_download = os.path.join(base_dir, snapgene, upload_snapgene, file)
    if os.path.exists(file_to_download):
        return send_file(file_to_download, as_attachment=True)
    return "File not found"
    # if file == "favorites":
    #     file_to_download = os.path.join(dir_current, current_app.config["TNC_SNAPGENE_LIB_FAV"])
    # elif file == "custom":
    #     file_to_download = os.path.join(dir_current, current_app.config["TNC_SNAPGENE_LIB_FILE"])
    # if file_to_download:
    #     return send_file(file_to_download, as_attachment=True)
    # else:
    #     return 0

@bp.route('/download_full/<file>')
def download_full(file):
    file_to_download=""
    if file == "gb":
        file_to_download = os.path.join(dir_current, current_app.config["TNC_GENBANK_FILE"]+".zip")
    elif file == "fa":
        file_to_download = os.path.join(dir_current, current_app.config["TNC_FASTA_FILE"]+".zip")
    elif file == "dna":
        file_to_download = os.path.join(dir_current, current_app.config["TNC_SNAPGENE_FILE"]+".zip")
    if file_to_download:
        return send_file(file_to_download, as_attachment=True)
    else:
        return 0
    
@bp.route('/download_blast/<type>/<file>')
def download_blastdb(type, file):
    file_to_download=""

    if type == "nc":
        base_name = "nc_"+current_app.config["BLAST_NAMEBASE"]
        if file == "tn":
            # file_to_download = os.path.join(dir_current, base_name+".fa.zip")
            pass
        elif file == "tn_in":
            base_name += "_integrall"
        elif file == "tn_is":
            base_name += "_isfinder"
        elif file == "tn_in_is":
            base_name += "_integrall_isfinder"
        file_to_download = os.path.join(dir_current, base_name+".fa.zip")
    elif type == "prot":
        base_name = current_app.config["BLAST_NAMEBASE"]
        if file == "tn":
            pass
        elif file == "tn_is":
            base_name += "_isfinder"
        file_to_download = os.path.join(dir_current, base_name+".prot.fa.zip")

    if file_to_download:
        return send_file(file_to_download, as_attachment=True)
    else:
        return 0


import zipfile
from secrets import token_hex
def generate_list_download(list_acc, ext):
    dir_temp = current_app.config['TNC_TEMP_DIR']
    dir_temp = os.path.join(dir_current, dir_temp)
    temp_name = current_app.config['TNC_TEMP_DIR']
    len_list = len(list_acc)
    if len_list < 5:
        file_to_download = list_acc[0]
        for i in range(1,len_list):
            file_to_download += "_"+list_acc[i]
    else:
        file_to_download = "results"

    random_token = token_hex(3).upper()
    full_new_folder = os.path.join(dir_temp, random_token)
    os.makedirs(full_new_folder, exist_ok=True)

    source_dir = utils.get_dir_by_ext(current_app.config,ext)
    file_to_download += f".{ext}"
    return_folder = ""
    if len_list == 1:
        return_folder = os.path.join(source_dir, file_to_download)
    else:
        file_to_download += f".zip"
        return_folder = os.path.join(temp_name, random_token, file_to_download)
        download_name = os.path.join(full_new_folder, file_to_download)
        with zipfile.ZipFile(download_name, 'w') as myzip:
            for file in list_acc:
                filename = f"{file}.{ext}"
                full_path = os.path.join(dir_current, source_dir, filename)
                if os.path.exists(full_path):
                    myzip.write(full_path, filename)
    # return download_name
    return return_folder

def generate_search_download(args, ext):

    len_list = len(args) # this function will be called when len > 1
    if len_list < 1:
        return None
    
    query = Te_Entry.query.filter_by(entry_id_parent=None, in_production=1)
    
    if len_list == 2:
        # There are only four fields that can be submitted as a single
        # parameter. The rest of them will be submitted with the HTML
        # select regardind the type of search (contains, begins_with...)
        filter_fields = ["all_fields", "s_type", "country", "isolation"]
        columns_fields = ["all", "type", "country", "date"]
        for idx, field in enumerate(filter_fields):
            filter1 = args.get(field)
            if not is_empty(filter1):
                if field == "s_type":
                    filter1 = build_match_type(filter1)
                query = build_search_query(filter1, columns_fields[idx], query)
    else:
        filter_fields = ["s_type", "country", "isolation", "name",
                            "synon", "family", "group", "accession",
                            "host"
                        ]
        columns_fields = ["type", "country", "date", "name",
                        "synonyms", "family", "group", "accession",
                        "organism"
                        ]
        filter_match = ["", "", "", "s_name", "s_synon",
                            "s_family", "s_group", "s_accession",
                            "s_host"
                            ]
        for idx, field in enumerate(filter_fields):
            filter_text = args.get(field)
            if not is_empty(filter_text):
                if field == "s_type":
                    filter_text = build_match_type(filter_text)
                elif filter_match[idx] != "":
                    match_type = request.args.get(filter_match[idx])
                    filter_text = build_match_filter(filter_text, match_type)
                else:
                    filter_text = build_match_filter(filter_text, "")
                query = build_search_query(filter_text, columns_fields[idx], query)
    dir_temp = current_app.config['TNC_TEMP_DIR']
    dir_temp = os.path.join(dir_current, dir_temp)
    temp_name = current_app.config['TNC_TEMP_DIR']
    filename = f"search_result.{ext}.zip"
    random_token = token_hex(3).upper()
    full_download_folder = os.path.join(dir_temp, random_token)
    os.makedirs(full_download_folder, exist_ok=True)
    dir_to_download = utils.get_dir_by_ext(current_app.config,ext)
    
    full_download_name = os.path.join(full_download_folder, filename)
    return_file = os.path.join(temp_name, random_token, filename)
    with zipfile.ZipFile(full_download_name, 'w') as myzip:
        for tn in query.all():
            accession = tn.accession
            filename = f"{accession}.{ext}"
            full_path = os.path.join(dir_current, dir_to_download, filename)
            if os.path.exists(full_path):
                myzip.write(full_path, filename)
    return return_file

def get_full_fname(ext):
    dir_temp = current_app.config['TNC_TEMP_DIR']
    dir_temp = os.path.join(dir_current, dir_temp)

    fasta_name = current_app.config['TNC_FASTA_FILE']
    genbank_name = current_app.config['TNC_GENBANK_FILE']
    csv_name = current_app.config['TNC_CSV_FILE']
    snap_name = current_app.config['TNC_SNAPGENE_FILE']

    filename = genbank_name

    if ext == "fasta" or ext == "fa":
        filename = fasta_name
    elif ext == "csv":
        filename = csv_name
    elif ext == "dna":
        filename = snap_name

    return filename

# TODO: change columns from hard coded to an enum/constant type class
def build_search_query(filter, columns="all", query=None):
    if query is None:
        query = Te_Entry.query.filter_by(entry_id_parent=None, in_production=1)
    if columns == "all":
        query = query.filter(
            db.or_(
                Te_Entry.accession.like(f"%{filter}%"),
                Te_Entry.name.like(f"%{filter}%"),
                Te_Entry.synonyms.like(f"%{filter}%"),
                Te_Entry.type.like(f"%{filter}%"),
                Te_Entry.family.like(f"%{filter}%"),
                Te_Entry.group.like(f"%{filter}%"),
                Te_Entry.organism.like(f"%{filter}%"),
                Te_Entry.country.like(f"%{filter}%"),
                Te_Entry.date.like(f"%{filter}%")
            )
        )
    else:
        query = query.filter(getattr(Te_Entry, columns).like(f"%{filter}%"))
    return query