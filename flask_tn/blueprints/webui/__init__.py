"""
    In this submodule we create all web routes that are accessible through the
    webbrowser. If a request is coming from ajax calls or is a rest function,
    the route will be in the restapi submodule.
"""

from datetime import datetime, timezone
import shutil
import os
from subprocess import PIPE, run

from flask import Blueprint, current_app, flash, send_file, jsonify, send_from_directory
from flask import request, render_template, redirect, url_for
from werkzeug import exceptions
from werkzeug.utils import secure_filename

from rq import Queue
from rq.job import Job

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from worker import conn
from flask_tn.db_models import ChangeLog, External_Resource, Te_Entry, Orf_Summary, Te_Orf, UploadCategory, db
from flask_tn import utils as utils
from flask_tn.utils import Constants, job_utils
from flask_tn.exceptions import InvalidFileException

bp = Blueprint("webui", __name__, template_folder="templates")
# global variable current_dir holds the folder where all files are stored
current_dir = ""

# init_app initializes this blueprint when the application is created
def init_app(app):
    # The URL prefix is necessary when we want to keep the older website
    # version alive. We can set any prefix in the 'settings.toml' file,
    # and that prefix will be applied to all routes in this submodule.
    if app.config["URL_PREFIX"] != "/":
        app.register_blueprint(bp, url_prefix=app.config["URL_PREFIX"])
    else:
        app.register_blueprint(bp)

    # Register a handler for HTTP exceptions.
    app.register_error_handler(exceptions.HTTPException, handle_http_error)

    # Set the global variable 'current_dir' to the value specified in the app configuration.
    global current_dir
    current_dir = app.config["TNC_CURRENT_DIR"]


def handle_http_error(e):
    # we log the errors in our logs/tncentral.log file.
    # We filter some 404 errors because tnpedia throw a lot of 404 errors and
    # we dont want to 'polute' the log for tncentral.
    if bool(e.code == 404) != bool(filter_404(request.path)):
        current_app.logger.error(f"[{e.code} {e.name}] {e.description}. Endpoint: {request.path}")
    elif not e.code == 404:
        current_app.logger.error(f"[{e.code} {e.name}] {e.description}. Endpoint: {request.path}")

    # Render different error templates based on the error code.
    if e.code == 404:
        return render_template("public/404.html")
    elif e.code == 500:
        return render_template("public/500.html")
    elif e.code == 401:
        return render_template("public/login_error.html")
    
    # Return a generic error message if none of the above conditions are met.
    return "Something went wrong."

# function to filter some pages with 404 errors coming from TnPedia
def filter_404(request_path:str):
    return request_path.startswith(("/robots.txt"))

def check_file(accession, ext):
    """
    This function is a helper for Jinja2 to check if a file exists
    """
    if accession:
        dir_download = utils.get_dir_by_ext(current_app.config, ext)
        file = os.path.join(current_dir, dir_download, accession + f".{ext}")
        if os.path.exists(file):
            return True
    return False

def check_image(accession):
    """
    This function is a helper for Jinja2 to check if an image exists
    """
    if accession:
        image_dir = os.path.join(current_dir, current_app.config["TNC_IMAGE_DIR"])
        image_path = os.path.join(image_dir, accession + ".png")
        if os.path.exists(image_path):
            return 1
    return 0

def use_analytics():
    """
    This function is a helper for Jinja2. Return True if USE_GOOGLE_ANALYTICS is 1
    """
    if current_app.config["USE_GOOGLE_ANALYTICS"] == 1:
        return True
    return False

def use_recaptcha():
    """
    This function is a helper for Jinja2. Return True if USE_RECAPTCHA is 1
    """
    if current_app.config["USE_RECAPTCHA"] == 1:
        return True
    return False

def configure_active(menu_item):
    """
    This function is a helper for Jinja2 to configure the active menu item
    in the base template.
    """
    url_end_poind = request.url_rule.endpoint
    class_return = ""
    if url_end_poind in ["webui.index"]:
        if menu_item == 0:
            class_return = "active"
        else:
            class_return = ""

    if url_end_poind in [
        "webui.tn_search",
        "webui.process_tn_search",
        "webui.te_report",
        "webui.process_gene_search",
        "webui.gene_report",
    ]:
        if menu_item == 1:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["webui.tn_blast", "webui.blast_result"]:
        if menu_item == 2:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["webui.tn_finder"]:
        if menu_item == 3:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["webui.data_download"]:
        if menu_item == 6:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["webui.related_links"]:
        if menu_item == 9:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["webui.feedback"]:
        if menu_item == 10:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["webui.about","webui.about2"]:
        if menu_item == 11:
            class_return = "active"
        else:
            class_return = ""

    return class_return

def site_traffic_logging(remote_addr, request_path):
     # logging the ip address of the user
    current_app.logger.info(f"{request_path} accessed from {remote_addr}")

@bp.route("/home")
@bp.route("/index")
@bp.route("/")
def index(): # funcion to be called as the index page of tncentral
    # logging the ip address of the user
    site_traffic_logging(request.remote_addr, request.path)
    # current_app.logger.info(f"{request.path} accessed from {request.remote_addr}")

    # Calculating the amount of transposons by family to show on homepage
    tn3 = Te_Entry.query.filter(
        Te_Entry.entry_id_parent == None,
        Te_Entry.in_production == 1,
        Te_Entry.family == "Tn3",
    )
    tn7 = Te_Entry.query.filter(
        Te_Entry.entry_id_parent == None,
        Te_Entry.in_production == 1,
        Te_Entry.family == "Tn7",
    )
    tn402 = Te_Entry.query.filter(
        Te_Entry.entry_id_parent == None,
        Te_Entry.in_production == 1,
        Te_Entry.family == "Tn402",
    )
    compound = Te_Entry.query.filter(
        Te_Entry.entry_id_parent == None,
        Te_Entry.in_production == 1,
        Te_Entry.family.ilike("%compound%"),
    )
    tn554 = Te_Entry.query.filter(
        Te_Entry.entry_id_parent == None,
        Te_Entry.in_production == 1,
        Te_Entry.family == "Tn554",
    )
    integrall = External_Resource.query.filter_by(database_name="integrall")

    return render_template(
        "public/index.html",
        tn3=tn3.count(),
        tn402=tn402.count(),
        compound=compound.count(),
        tn554=tn554.count(),
        tn7=tn7.count(),
        integrall=integrall.count(),
    )

# The following functions are endpoints of the application,
# each corresponding to an HTML page to be rendered.
@bp.route("/login")
def login():
    return render_template("public/login.html")

@bp.route("/data_download")
def data_download():
    custom_query = ChangeLog.query.join(UploadCategory).filter(
            UploadCategory.category_name==Constants.UPLOAD_CUSTOM,
            ).order_by(ChangeLog.time_changed).all()
    favorites_query = ChangeLog.query.join(UploadCategory).filter(
        UploadCategory.category_name==Constants.UPLOAD_FAVORITE
                ).order_by(ChangeLog.time_changed).all()
    # c_dt = datetime.datetime.strptime(custom[-1].time_changed, "%Y-%m-%d %H:%M:%S.%f")
    # f_dt = datetime.datetime.strptime(favorites[-1].time_changed, "%Y-%m-%d %H:%M:%S.%f")

    base_dir = current_app.config["TNC_BASE_DIR"]
    snapgene = current_app.config["TNC_SNAPGENE_BASE_LIBRARY"]
    upload_snapgene = current_app.config["TNC_UPLOAD_FOLDER"]
    config_custom = current_app.config["TNC_SNAPGENE_CUSTOM"]
    config_dna = current_app.config["TNC_SNAPGENE_COMMON_DNA"]
    config_favorites = current_app.config["TNC_SNAPGENE_FAVORITES"]
    dt_custom = ""
    if len(custom_query) > 0:
        dt_custom = custom_query[-1].time_changed.strftime('%m_%d_%Y')
        custom_file_ftrs = f"{config_custom}_{dt_custom}.ftrs"
        custom_file_dna = f"{config_dna}_{dt_custom}.dna"

        file_to_download = os.path.join(base_dir, snapgene, upload_snapgene, custom_file_ftrs)
        
        if not os.path.exists(file_to_download):
            custom_file_ftrs=f"{config_custom}.ftrs"
            custom_file_dna=f"{config_dna}.dna"
    else:
        custom_file_ftrs=f"{config_custom}.ftrs"
        custom_file_dna=f"{config_dna}.dna"
    dt_fav=""
    if len(favorites_query) > 0:
        dt_fav = favorites_query[-1].time_changed.strftime('%m_%d_%Y')
        favorites_file = f"{config_favorites}_{dt_fav}.zip"

        file_to_download = os.path.join(base_dir, snapgene, upload_snapgene, favorites_file)
        
        if not os.path.exists(file_to_download):
            favorites_file=f"{config_favorites}.zip"
    else:
        favorites_file=f"{config_favorites}.zip"
    dict_data = {
        'dt_custom': dt_custom,
        'dt_fav': dt_fav,
        'config_ftrs': f'{config_custom}',
        'config_dna': f'{config_dna}',
        'config_fav': f'{config_favorites}',
        'ftrs_file': custom_file_ftrs,
        'dna_file': custom_file_dna,
        'fav_file': favorites_file,
    }
    return render_template("public/data_download.html", dict_data=dict_data)

@bp.route("/annotation_tool")
def annotation_tool():
    return render_template("public/annotation.html", step=1)

@bp.route("/search/")
def tn_search():
    site_traffic_logging(request.remote_addr, request.path)
    return render_template("public/transposon_search.html")

@bp.route("/feedback")
def feedback():
    site_traffic_logging(request.remote_addr, request.path)
    return render_template("public/feedback.html")

@bp.route("/about")
def about():
    site_traffic_logging(request.remote_addr, request.path)
    return render_template("public/help.html")

@bp.route("/about2")
def about2():
    return render_template("public/help2.html")

@bp.route("/form_annotation")
def form_annotation():
    return render_template("public/annotation.html")

@bp.route("/blast/")
def tn_blast():
    site_traffic_logging(request.remote_addr, request.path)
    return render_template("public/tn_blast.html")

@bp.route("/tnfinder/")
def tn_finder():
    site_traffic_logging(request.remote_addr, request.path)
    return render_template("public/tnfinder.html")

@bp.route("/related_links/")
def related_links():
    site_traffic_logging(request.remote_addr, request.path)
    return render_template("public/related_links.html")

@bp.route("/table/integrall", methods=["GET"])
def get_integrall_table():
    site_traffic_logging(request.remote_addr, request.path)
    return render_template("public/integrall.html")

@bp.route("/quick_tn", methods=["GET"])
def quick_tn_search():
    """
        This function will be called to handle the homepage search
        by transposable elements.
    """
    all_fields = utils.get_request_value(request.args, "all_fields")
    error_tn = ""
    if all_fields != "":
        query = Te_Entry.query.filter(
            Te_Entry.entry_id_parent == None, Te_Entry.in_production == 1
        )
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
                Te_Entry.date.like(f"%{all_fields}%"),
            )
        )
        total_query = query.count()
        if total_query == 0:
            error_tn = f"The search '{all_fields}' returned zero results."
        elif total_query == 1:
            te = query.first()
            return redirect(url_for("webui.te_report", accession=te.accession))
        else:
            return redirect(url_for("webui.process_tn_search", all_fields=all_fields))
    else:
        error_tn = "Empty search."

    if error_tn != "":
        flash(error_tn, category="error_tn")
    return redirect(url_for("webui.index"))

@bp.route("/quick_gene", methods=["GET"])
def quick_gene_search():
    """
        This function will be called to handle the homepage search by gene.
    """
    gene_all_fields = utils.get_request_value(request.args, "gene_all_fields")
    local_args = {}
    error_gn = ""
    if gene_all_fields != "":
        query = Orf_Summary.query.filter(
            db.or_(
                Orf_Summary.orf_name.like(f"%{gene_all_fields}%"),
                Orf_Summary.orf_class.like(f"%{gene_all_fields}%"),
                Orf_Summary.subclass.like(f"%{gene_all_fields}%"),
            )
        )
        total_query = query.count()
        if total_query == 0:
            error_gn = f"The search '{gene_all_fields}' returned zero results."
        elif total_query == 1:
            gene = query.first()
            return redirect(url_for("webui.gene_report", id=gene.id))
        else:
            local_args["gene_all_fields"] = gene_all_fields
            return redirect(
                url_for("webui.process_gene_search", gene_all_fields=gene_all_fields)
            )
    else:
        error_gn = "Empty search."

    if error_gn != "":
        flash(error_gn, category="error_gn")
    return redirect(url_for("webui.index"))

@bp.route("/quick_job_id", methods=["GET"])
def quick_job_id():
    job_id = utils.get_request_value(request.args, "job_id")
    error_bl = ""
    has_job = False
    try:
        job = Job.fetch(job_id, connection=conn)

        if job.is_finished:
            has_job = True
        else:
            # Possible values are queued, started, deferred, finished, stopped, scheduled, canceled and failed.
            # If refresh is True fresh values are fetched from Redis.
            job_status = ["queued", "started", "deferred", "failed", "canceled",
                          "scheduled"]
            if job.get_status() in job_status:
                has_job = True
            else:
                error_bl = "Job not found."
    except:
        dir_jobs = current_app.config["TNC_JOB_DIR"]
        dir_jobs = os.path.join(current_dir, dir_jobs)
        blast_file = utils.job_utils.blast_result_file(dir_jobs, job_id)
        if os.path.exists(blast_file):
            has_job = True
        else:
            error_bl = "Job not found."
    finally:
        if has_job:
            return redirect(url_for("webui.blast_result", job_id=job_id))
        else:
            error_bl = "Job not found."
            flash(error_bl, category="error_bl")
    return redirect(url_for("webui.index"))


@bp.route("/table/mges", methods=["GET"])
def process_tn_search():
    """
    This function is called from the transposon_search.html page, specifically
    from the 'Transposon Search' form. Here, we send the valid values to
    transposon_table.html page, where we will build the table via AJAX.
    """
    site_traffic_logging(request.remote_addr, request.path)
    local_args = {}
    all_fields = utils.get_request_value(request.args, "all_fields")
    if all_fields == "":
        fields_with_drop = ["name", "synon", "family", "group", "accession", "host"]
        for field in fields_with_drop:
            field_value = utils.get_request_value(request.args, field)
            if field_value != "":
                local_args[field] = field_value
                local_args["s_" + field] = request.args.get("s_" + field)

        internals = utils.get_request_value(request.args, "internals")
        if internals == "1":
            local_args["internals"] = internals
        s_type = utils.get_request_value(request.args, "s_type")
        if s_type != "" and s_type != "0":
            local_args["s_type"] = s_type

        country = utils.get_request_value(request.args, "country")
        if country != "":
            local_args["country"] = country

        isolation = utils.get_request_value(request.args, "isolation")
        if isolation != "":
            local_args["isolation"] = isolation
    else:
        local_args["all_fields"] = all_fields

    return render_template("public/transposon_table.html", args=local_args)


@bp.route("/table/genes", methods=["GET"])
def process_gene_search():
    """
    This function is called from the transposon_search.html page, specifically
    from the 'Gene Search' form. Here, we send the valid values to
    gene_table.html page, where we will build the table via AJAX.
    """
    site_traffic_logging(request.remote_addr, request.path)
    local_args = {}

    fields = ["gene_all_fields", "gene_name", "gene_class", "gene_function"]

    for field in fields:
        field_value = utils.get_request_value(request.args, field)
        if field_value != "":
            local_args[field] = field_value

    return render_template("public/gene_table.html", args=local_args)

# @bp.route("/index.php", methods=["GET"])
# def redirect_tnp():
#     id = request.args["id"]
#     if id != None:
#         return redirect("tnp/tnp.php?id="+id)
#     else:
#         return redirect("TnPedia/index.php")

# @bp.route("/test.php", methods=["GET"])
# @bp.route("/test.php/", methods=["GET"])
# def test():
#     id = utils.get_request_value(request.args, "id")
#     if id:
#         return "ID: "+id
#     return "/test.php/"

# @bp.route("/test.php/<path:params>", methods=["GET"])
# def test1(params):
#     if params:
#         return "PATH: "+params
#     return "/test.php/"

@bp.route("/index.php", methods=["GET"])
@bp.route("/index.php/", methods=["GET"])
def redirect_tnpedia():
    id = utils.get_request_value(request.args, "id")
    if id:
        return redirect("tnp/tnp.php?id="+id)
    return redirect("/TnPedia/index.php/")

@bp.route("/index.php/<path:params>", methods=["GET"])
def redirect_tnindex(params):
    if params:
        return redirect("/TnPedia/index.php/"+params)
    return redirect("/TnPedia/index.php/")

@bp.route("/tnp.php", methods=["GET"])
def redirect_tnp():
    id = request.args["id"]
    return redirect("tnp/tnp.php?id="+id)

@bp.route("/favicon.ico", methods=["GET"])
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'images'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# @bp.route("/index.php", methods=["GET"])
# def redirect_tnpedia():
#     return redirect("TnPedia/index.php")

# @bp.route("/index.php/", methods=["GET"])
# def redirect_tnpedia2():
#     return redirect("TnPedia/index.php/")


@bp.route("/report/te/<accession>", methods=["GET"])
def te_report(accession):
    """
    accession: the accession for the entry to be returned
    """
    site_traffic_logging(request.remote_addr, request.path)

    te_entry = Te_Entry.query.filter_by(
        accession=accession, entry_id_parent=None, in_production=1
    ).first()

    if te_entry:
        te_internals = Te_Entry.query.filter_by(entry_id_parent=te_entry.entry_id).all()

        recombs = utils.gb_utils.sort_internals(te_entry, te_internals, "recombs")
        repeats = te_entry.repeats.all()
        repeats_internals = utils.gb_utils.sort_internals(None, te_internals, "repeats")

        orfs = utils.gb_utils.sort_internals(te_entry, te_internals, "orfs")
        
    else:
        te_entry = None
        te_internals = None
        recombs = None
        repeats = None
        repeats_internals = None
        orfs = None

    return render_template(
        "public/te_report.html",
        accession=accession,
        te=te_entry,
        te_int=te_internals,
        te_rep=repeats,
        te_rep_int=repeats_internals,
        te_recomb=recombs,
        te_orf=orfs,
    )

@bp.route("/report/gene/<accession>/<rank>", methods=["GET"])
def report_from_acc_rank(accession, rank):
    """
    
    """
    # site_traffic_logging(request.remote_addr, request.path)
    te_entry = Te_Entry.query.filter_by(accession=accession, in_production=1, entry_id_parent=None).first()
    print(te_entry.accession)
    te_orf = Te_Orf.query.filter_by(entry_id=te_entry.entry_id).all()
    print(f"len {len(te_orf)}")
    protein_name = te_orf[int(rank)-1].name
    print(f"protein name ---------- {protein_name}")
    orf_summary = Orf_Summary.query.filter_by(orf_name=protein_name).first()
    return render_template("public/gene_report.html", orf=orf_summary)

@bp.route("/report/gene/<id>", methods=["GET"])
def gene_report(id):
    """
    id: the primary key for the table orf_summary
    """
    site_traffic_logging(request.remote_addr, request.path)
    orf_summary = Orf_Summary.query.filter_by(id=id).first()
    return render_template("public/gene_report.html", orf=orf_summary)

@bp.route("/report/blast/<job_id>")
def blast_result(job_id):
    site_traffic_logging(request.remote_addr, request.path)
    retrieve = request.args.get("retrieve")
    return render_template("public/blast_table.html", job_id=job_id, retrieve=retrieve)

@bp.route("/report/test/<job_id>")
def blast_result_test(job_id):
    return render_template("public/blast_table2.html", job_id=job_id)

@bp.route("/process/blast", methods=["POST"])
def process_blast():
    """
    This page is called from the page tn_blast.html and process the form
    input before redirecting to the '/report/blast' page. The job will be
    submitted using redis library and the queue name is defined in the
    settings.toml file.
    """
    # job_id = utils.get_form_value(request.form, "job_id")
    job_id = utils.get_request_value(request.form, "job_id")
    retrieve = 0
    job_dir = os.path.join(current_dir, current_app.config["TNC_JOB_DIR"])
    if job_id == "":
        job_id = job_utils.get_new_job(job_dir, current_app.config["RQ_JOB_PREFIX"])
        local_job = os.path.join(job_dir, job_id)
        os.makedirs(local_job)

        db_tn = utils.get_request_value(request.form, "db_tn")
        db_in = utils.get_request_value(request.form, "db_in")
        db_is = utils.get_request_value(request.form, "db_is")

        program = utils.get_request_value(request.form, "blast_program")

        n_display = utils.get_request_value(request.form, "select_display")
        expect = utils.get_request_value(request.form, "select_expect")
        word = utils.get_request_value(request.form, "select_word")
        comp_based = utils.get_request_value(request.form, "comp_based")

        filter1 = utils.get_request_value(request.form, "filter1")
        filter2 = utils.get_request_value(request.form, "filter2")
        lcase_mask = utils.get_request_value(request.form, "lcase_mask")

        scores = utils.get_request_value(request.form, "select_scores")
        matrix = utils.get_request_value(request.form, "select_matrix")
        gap_extend = utils.get_request_value(request.form, "select_costs")

        if request.files["fasta_file"]:
            filename = secure_filename(request.files["fasta_file"].filename)
            try:
                query_filename = job_utils.upload_fasta_blast(
                    local_job, request.files["fasta_file"], job_id
                )
            except InvalidFileException as exc:
                shutil.rmtree(local_job)
                flash(exc.message)
                return redirect(url_for("webui.tn_blast"))
        else:
            sequence = request.form.get("txt_sequence")
            query_filename = job_utils.create_fasta_blast(local_job, sequence, job_id)

        fasta_database = current_app.config["BLAST_NAMEBASE"]

        if program == "blastp":
            # fasta_database = current_app.config["TNC_PROTEIN_FILE"]
            if db_is == "is":
                fasta_database = f"{fasta_database}_isfinder.prot.fa"
            else:
                fasta_database = f"{fasta_database}.prot.fa"
        else:
            if db_in == "in" and db_is == "is":
                fasta_database = f"{fasta_database}_integrall_isfinder.fa"
            elif db_in == "in":
                fasta_database = f"{fasta_database}_integrall.fa"
            elif db_is == "is":
                fasta_database = f"{fasta_database}_isfinder.fa"
            else:
                fasta_database = f"{fasta_database}.fa"

        fasta_database = os.path.join(current_dir, fasta_database)

        parameters = job_utils.format_blast_parameters(
            program,
            n_display,
            expect,
            word,
            comp_based,
            filter1,
            filter2,
            lcase_mask,
            scores,
            matrix,
            gap_extend,
        )

        queue = current_app.config["RQ_QUEUE_DEFAULT"]
        blast_command = current_app.config["BLAST_COMMAND"]
        commands = f"{blast_command} {parameters} -d {fasta_database} "
        commands += f"-i {query_filename} -o {query_filename}.out"

        perl_command = current_app.config["PERL"]
        # removing possible \r in the file
        result = run(
            f"{perl_command} -pi -e 's/\r//g' {query_filename}",
            stdout=PIPE,
            stderr=PIPE,
            shell=True,
        )
        size_kb = os.path.getsize(query_filename) / 1000

        # create file to store log and info to avoid letting them in the redis db        
        queue = current_app.config["RQ_QUEUE_HIGH"]

        job_timeout = current_app.config["RQ_TIMEOUT_HIGH"]
        result_ttl = current_app.config["RQ_RESULT_TTL"]
        if size_kb > 200:
            queue = current_app.config["RQ_QUEUE_DEFAULT"]
            job_timeout = current_app.config["RQ_TIMEOUT_DEFAULT"]
        q = Queue(name=queue, connection=conn)
        from flask_tn.utils.job_utils import run_blast

        info_ext=current_app.config['RQ_INFO_EXT']
        error_ext=current_app.config['RQ_ERROR_EXT']
        cmd_ext=current_app.config['RQ_CMD_EXT']

        info_filename = os.path.join(local_job, job_id+"."+info_ext)

        job_utils.update_blast_info(info_filename, "Enqueued at")

        error_filename = os.path.join(local_job, job_id+"."+error_ext)
        cmd_filename = os.path.join(local_job, job_id+"."+cmd_ext)

        job_utils.update_blast_info(cmd_filename, commands, print_time=False)

        q.enqueue(run_blast,
                  commands,
                  job_id=job_id,
                  job_timeout=job_timeout,
                  result_ttl=result_ttl,
                  meta={
                      'info_file':info_filename,
                      'error_file':error_filename,
                      'file_size':size_kb
                    }
                )
    else:
        local_job = os.path.join(job_dir, job_id)
        if os.path.exists(local_job) and os.path.isdir(local_job):
            retrieve = 1
        else:
            # if we return -1, the job doesn't exist
            retrieve = -1
    return redirect(url_for("webui.blast_result", job_id=job_id, retrieve=retrieve))


@bp.route("/image/<accession>")
def get_image(accession):
    image_dir = os.path.join(current_dir, current_app.config["TNC_IMAGE_DIR"])
    image_path = os.path.join(image_dir, accession + ".png")
    if not os.path.exists(image_path):
        image_path = os.path.join(image_dir, "error.png")
    return send_file(image_path, mimetype="image/png")


@bp.route("/sequence/<accession>")
def get_sequence(accession):
    fasta_fmt_dir = os.path.join(current_dir, current_app.config["TNC_FASTA_FMT_DIR"])
    fasta_path = os.path.join(fasta_fmt_dir, accession + ".fmt")
    return send_file(fasta_path, mimetype="text/plain")

@bp.route("/send_email", methods=["POST"])
def send_email():
    status = {"status": "ok"}
    recaptcha = utils.get_request_value(request.form, 'g-recaptcha-response')
    # validate recaptcha
    if recaptcha == "":
        status = {"status": "error"}
        status["error"] = "Invalid Recaptcha"
        return jsonify(status)
    secret = current_app.config['RECAPTCHA_SECRET_KEY']
    if not utils.is_human(secret, recaptcha):
        status = {"status": "error"}
        status["error"] = "Invalid Recaptcha"
        return jsonify(status)
    
    email_subject = "[TnCentral] New Message"
    email_message = f"{request.form['title']} "
    email_message = f"{request.form['name']+' '+request.form['last_name']}\n"
    if request.form["institution"]:
        email_message += f"Institution: {request.form['institution']}\n"
    if request.form["department"]:
        email_message += f"Department: {request.form['department']}\n"
    email_message += f"Email: {request.form['email']}\nMessage:\n"
    email_message += f"{request.form['message']}\n"

    sender_email = current_app.config["MAIL_USERNAME"]
    sender_password = current_app.config["MAIL_PASSWORD"]
    receiver_email = current_app.config["MAIL_RECEIVER"]
    receiver_email_cc = current_app.config["MAIL_RECEIVER_CC"]

    message = MIMEMultipart()
    message["From"] = sender_email

    message["To"] = receiver_email
    message["Cc"] = receiver_email_cc

    all_receivers = message["To"].split(",")
    if message["Cc"]:
        all_receivers.extend(message["Cc"].split(","))

    message["Subject"] = email_subject
    message.attach(MIMEText(email_message, "plain"))
    try:
        if current_app.config["USE_FEEDBACK_MAIL"] == 1:
            server = smtplib.SMTP_SSL(
                current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"]
            )
            server.set_debuglevel(2)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, all_receivers, message.as_string())
            server.quit()
        # save in file
        if current_app.config['ENV']=="development":
            home = current_app.config['TNC_HOME']
        else:
            home = current_app.config["TNC_HOME_PRODUCTION"]
        mail_log = os.path.join(home, current_app.config['TNC_LOG_DIR'])
        mail_file = os.path.join(mail_log, current_app.config['TNC_LOG_MAIL'])
        dt = datetime.now(timezone.utc)
        with open(mail_file, "a") as writer:
            writer.write(f"-----------------------------------------------\n")
            writer.write(f"New mail: {dt.strftime('%m/%d/%Y %H:%M:%S')}\n")
            writer.write(f"{email_message}\n")
    except smtplib.SMTPHeloError as e:
        pass
    except smtplib.SMTPRecipientsRefused as e:
        pass
    except smtplib.SMTPSenderRefused as e:
        pass
    except smtplib.SMTPNotSupportedError as e:
        pass
    except Exception as e:
        status = {"status": "error"}
        status["error"] = f"{e}"
    return jsonify(status)
