import time
from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
    current_app
)
from subprocess import PIPE, run
import datetime
import shutil
import os
import zipfile
from secrets import token_hex
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from flask_tn import utils
from flask_tn.utils import gb_utils, Constants, Genbank, job_utils
from flask_tn.db_models import (
    ChangeLog,
    Te_Orf,
    Te_Pubmed,
    Te_RecombSite,
    UploadCategory,
    User,
    UserGenbank,
    Te_Entry,
    Te_Repeat,
)
from flask_tn.ext.database import db
from flask_tn.ext.login import login_manager

from worker import conn
from rq import Queue

bp = Blueprint("admin", __name__, url_prefix="/admin")

current_dir = ""


def init_app(app):
    if app.config["URL_PREFIX"] != "/":
        app.register_blueprint(bp, url_prefix=app.config["URL_PREFIX"] + "admin")
    else:
        app.register_blueprint(bp)

    global current_dir
    current_dir = app.config["TNC_CURRENT_DIR"]


def configure_active2(menu_item):
    """
    This function is a helper for Jinja2 to configure the active menu item
    in the base template.
    """
    url_end_poind = request.url_rule.endpoint
    class_return = ""
    if url_end_poind in ["admin.userdata", "admin.edit_gb_user"]:
        if menu_item == 1:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["admin.dbdata", "admin.edit_gb_db"]:
        if menu_item == 2:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["admin.quality_control", "admin.qc_accessory_gene",
                           "admin.qc_ta_gene", "admin.qc_transposase",
                           "admin.qc_card_categories", "admin.qc_card_index",
                           "admin.qc_metal_targets"]:
        if menu_item == 3:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["admin.snapgene_library"]:
        if menu_item == 4:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["admin.blast_jobs"]:
        if menu_item == 5:
            class_return = "active"
        else:
            class_return = ""
    elif url_end_poind in ["admin.change_logs"]:
        if menu_item == 6:
            class_return = "active"
        else:
            class_return = ""


    return class_return

@bp.route("/submit_login", methods=["POST"])
def submit_login():
    username = utils.get_request_value(request.form, "username")
    password = utils.get_request_value(request.form, "password")
    user = User.query.filter_by(username=username).first()
    if user:
        if check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for("admin.home"))
        
    abort(401)


@bp.route("/")
@login_required
def home():
    return redirect(url_for("admin.userdata"))


@bp.route("/dbdata")
@login_required
def dbdata():
    return render_template("admin/dbdata.html")

@bp.route("/quality_control")
@login_required
def quality_control():
    filenames = [qc.ACCESSORY_GENE_FILE, qc.TA_GENE_FILE, qc.TRANSPOSASE_FILE,
                   qc.CARD_CATEGORIES_FILE, qc.CARD_INDEX_FILE, qc.METAL_TARGETS_FILE]
    return render_template("admin/quality_control.html", filenames=filenames)

@bp.route("/snapgene_library")
@login_required
def snapgene_library():
    # last date
    custom = ChangeLog.query.join(UploadCategory).filter(UploadCategory.category_name==Constants.UPLOAD_CUSTOM,
                ChangeLog.user_id==current_user.get_id()).order_by(ChangeLog.time_changed).all()
    favorites = ChangeLog.query.join(UploadCategory).filter(UploadCategory.category_name==Constants.UPLOAD_FAVORITE,
                ChangeLog.user_id==current_user.get_id()).order_by(ChangeLog.time_changed).all()
    # c_dt = datetime.datetime.strptime(custom[-1].time_changed, "%Y-%m-%d %H:%M:%S.%f")
    # f_dt = datetime.datetime.strptime(favorites[-1].time_changed, "%Y-%m-%d %H:%M:%S.%f")
    base_dir = current_app.config["TNC_BASE_DIR"]
    snapgene = current_app.config["TNC_SNAPGENE_BASE_LIBRARY"]
    upload_snapgene = current_app.config["TNC_UPLOAD_FOLDER"]
    
    if len(custom) > 0:
        custom_file = f"customCommonFeatures_{custom[-1].time_changed.strftime('%m_%d_%Y')}.ftrs"

        file_to_download = os.path.join(base_dir, snapgene, upload_snapgene, custom_file)
        print(file_to_download)
        if not os.path.exists(file_to_download):
            custom_file="customCommonFeatures.ftrs"
    else:
        custom_file="customCommonFeatures.ftrs"
    if len(favorites) > 0:
        favorites_file = f"Exported_Favorite_Features_{favorites[-1].time_changed.strftime('%m_%d_%Y')}.zip"

        file_to_download = os.path.join(base_dir, snapgene, upload_snapgene, favorites_file)
        print(file_to_download)
        if not os.path.exists(file_to_download):
            favorites_file="Exported_Favorite_Features.zip"
    else:
        favorites_file="Exported_Favorite_Features.zip"
    

    return render_template("admin/snapgene_library.html", custom=custom_file, favorites=favorites_file)

@bp.route("/jobs")
@login_required
def blast_jobs():
    return render_template("admin/jobs_management.html")


# @bp.route("/home")
@bp.route("/userdata")
@login_required
def userdata():
    return render_template("admin/userdata.html")

@bp.route("/qc_accessory_gene")
@login_required
def qc_accessory_gene():
    return render_template("admin/qc_accessory_gene.html", qc_name=qc.ACCESSORY_GENE_FILE)

@bp.route("/qc_ta_gene")
@login_required
def qc_ta_gene():
    return render_template("admin/qc_ta_gene.html", qc_name=qc.TA_GENE_FILE)

@bp.route("/qc_transposase")
@login_required
def qc_transposase():
    return render_template("admin/qc_transposase.html", qc_name=qc.TRANSPOSASE_FILE)

@bp.route("/qc_card_categories")
@login_required
def qc_card_categories():
    return render_template("admin/qc_card_categories.html", qc_name=qc.CARD_CATEGORIES_FILE)

@bp.route("/qc_card_index")
@login_required
def qc_card_index():
    return render_template("admin/qc_card_index.html", qc_name=qc.CARD_INDEX_FILE)

@bp.route("/qc_metal_targets")
@login_required
def qc_metal_targets():
    return render_template("admin/qc_metal_targets.html", qc_name=qc.METAL_TARGETS_FILE)

@bp.route("/change_logs")
@login_required
def change_logs():
    # return render_template("admin/qc_metal_targets.html", qc_name=qc.METAL_TARGETS_FILE)
    return render_template("admin/change_logs.html")


@bp.route("/edit/u/<accession>/")
@login_required
def edit_gb_user(accession):
    u_id = current_user.get_id()
    user_gb = UserGenbank.query.filter_by(user_id=u_id, accession=accession).first()
    is_loaded = Te_Entry.query.filter_by(in_production=1, accession=accession).first()
    if is_loaded:
        is_loaded = 1
    else:
        is_loaded = 0
    
    if user_gb:
        # te_entry = user_gb.te_entry
        repeats = user_gb.te_entry.repeats.all()
        orfs = user_gb.te_entry.orfs.all()
        recombs = user_gb.te_entry.recombs.all()
        pubmeds = user_gb.te_entry.pubmeds.all()
    else:
        te_entry = None
        repeats = None
        orfs = None
        recombs = None
    return render_template(
        "admin/edit_genbank_user.html",
        user_gb=user_gb,
        repeats=repeats,
        orfs=orfs,
        recombs=recombs,
        pubmeds=pubmeds,
        is_loaded=is_loaded,
    )

@bp.route("/edit/d/<accession>/")
@login_required
def edit_gb_db(accession):
    te_entry = Te_Entry.query.filter_by(in_production=1, accession=accession).first()
    repeats = te_entry.repeats.all()
    orfs = te_entry.orfs.all()
    recombs = te_entry.recombs.all()
    pubmeds = te_entry.pubmeds.all()
    return render_template(
        "admin/edit_genbank_db.html",
        te=te_entry,
        repeats=repeats,
        orfs=orfs,
        recombs=recombs,
        pubmeds=pubmeds,
    )


def get_upload_folder():
    upload_folder = os.path.join(
        current_app.config["TNC_DATA_DIR"], current_app.config["TNC_UPLOAD_FOLDER"]
    )
    username = current_user.username
    upload_folder = os.path.join(upload_folder, username)
    return upload_folder


@bp.route("/save/user", methods=["POST"])
@login_required
def save_gb():
    upload_folder = os.path.join(
        current_app.config["TNC_DATA_DIR"], current_app.config["TNC_UPLOAD_FOLDER"]
    )
    username = current_user.username
    upload_folder = os.path.join(upload_folder, username)

    entry_id = utils.get_request_value(request.form, "entry_id")
    if not entry_id:
        status = {"status": "error",
                  "error": "Failed to recover genbank information."
                  }
    te = Te_Entry.query.filter_by(entry_id=entry_id).first()

    int_columns = ["first_isolate", "partial", "transposition"]
    for int_column in int_columns:
        if int_column in request.form:
            if utils.get_request_value(request.form, int_column) == "None":
                value = None
            else:
                value = int(utils.get_request_value(request.form, int_column))
            if value != te.__getattribute__(int_column):
                te.__setattr__(int_column, value)

    # think about the column name and how it affects the other features
    str_columns = [
        "type",
        "family",
        "group",
        "synonyms",
        "organism",
        "molecular_source",
        "country",
        "date",
        "taxonomy",
        "bacteria_group",
        "region",
        "other_loc",
        "comment",
    ]
    for str_column in str_columns:
        if str_column in request.form:
            value = utils.get_request_value(request.form, str_column)
            if value != te.__getattribute__(str_column):
                te.__setattr__(str_column, value)
    db.session.commit()

    filename_origin = os.path.join(upload_folder, te.accession + ".ori.gb")
    filename = os.path.join(upload_folder, te.accession + ".gb")
    if not os.path.exists(filename_origin):
        shutil.copyfile(filename, filename_origin)
    
    gb_obj = Genbank.get_genbank_object(filename)
    main_feature = gb_obj.get_main_feature()
    if "type" in request.form:
        met_obj = main_feature.get_qualifier(Constants.QL_MOBILE_ELEMENT_TYPE)
        fmt_value = f'"{te.type}:{te.name}"'
        met_obj.value = fmt_value

    note_cols = Constants.NOTE_FIELDS[Constants.FT_MOBILE_ELEMENT].copy()
    note_cols.extend(Constants.HOST_FIELDS)

    dict_note = main_feature.dict_note
    for i in range(1, len(note_cols)):
        db_col = Constants.DB_FIELDS[note_cols[i]]
        if note_cols[i] in Constants.BOOLEAN_FIELDS:
            if getattr(te, db_col) == 1:
                value = "yes"
            elif getattr(te, db_col) == 0:
                value = "no"
            else:
                value = ""  # should be ND
        else:
            value = getattr(te, db_col)
        dict_note[note_cols[i]] = value

    note_qualifier = main_feature.get_qualifier("note")
    note = Genbank.qvalue_from_dict(main_feature)
    note_qualifier.value = note

    with open(filename, "w") as writer:
        writer.write(str(gb_obj))
    # log change
    save_change_log(Constants.UPLOAD_GENBANK, filename, "Genbank edited in user area.")
    status = {"status": "OK"}
    return jsonify(status)


@bp.route("/save/db", methods=["POST"])
@login_required
def save_gb_db():
    gb_dir = current_app.config["TNC_GENBANK_DIR"]
    current_dir = current_app.config["TNC_CURRENT_DIR"]
    file_folder = os.path.join(current_dir, gb_dir)

    entry_id = utils.get_request_value(request.form, "entry_id")
    te = Te_Entry.query.filter_by(entry_id=entry_id).first()
    int_columns = ["first_isolate", "partial", "transposition"]
    for int_column in int_columns:
        if int_column in request.form:
            if utils.get_request_value(request.form, int_column) == "None":
                value = None
            else:
                value = int(utils.get_request_value(request.form, int_column))
            if value != te.__getattribute__(int_column):
                te.__setattr__(int_column, value)

    # think about the column name and how it affects the other features
    str_columns = [
        "type",
        "family",
        "group",
        "synonyms",
        "organism",
        "molecular_source",
        "country",
        "date",
        "taxonomy",
        "bacteria_group",
        "region",
        "other_loc",
        "comment",
    ]
    for str_column in str_columns:
        if str_column in request.form:
            value = utils.get_request_value(request.form, str_column)
            if value != te.__getattribute__(str_column):
                te.__setattr__(str_column, value)
    db.session.commit()

    filename_origin = os.path.join(file_folder, te.accession + ".ori.gb")
    filename = os.path.join(file_folder, te.accession + ".gb")
    if not os.path.exists(filename_origin):
        shutil.copyfile(filename, filename_origin)

    gb_obj = Genbank.get_genbank_object(filename)
    main_feature = gb_obj.get_main_feature()
    if "type" in request.form:
        met_obj = main_feature.get_qualifier(Constants.QL_MOBILE_ELEMENT_TYPE)
        fmt_value = f'"{te.type}:{te.name}"'
        met_obj.value = fmt_value

    note_cols = Constants.NOTE_FIELDS[Constants.FT_MOBILE_ELEMENT].copy()
    note_cols.extend(Constants.HOST_FIELDS)

    dict_note = main_feature.dict_note
    for i in range(1, len(note_cols)):
        db_col = Constants.DB_FIELDS[note_cols[i]]
        if note_cols[i] in Constants.BOOLEAN_FIELDS:
            if getattr(te, db_col) == 1:
                value = "yes"
            elif getattr(te, db_col) == 0:
                value = "no"
            else:
                value = ""  # should be ND
        else:
            value = getattr(te, db_col)
        dict_note[note_cols[i]] = value

    note_qualifier = main_feature.get_qualifier("note")
    note = Genbank.qvalue_from_dict(main_feature)
    note_qualifier.value = note

    with open(filename, "w") as writer:
        writer.write(str(gb_obj))

    # log change
    save_change_log(Constants.UPLOAD_GENBANK, filename, "Genbank edited in db area.")

    status = {"status": "ok"}
    return jsonify(status)

@bp.route("/has_file/<accession>/<ext>")
def has_file(accession, ext):
    if ext == "dna":
        upload_folder = os.path.join(current_dir, current_app.config["TNC_SNAP_DIR"])
    elif ext == "png":
        upload_folder = os.path.join(current_dir, current_app.config["TNC_IMAGE_DIR"])
    filename = accession+"."+ext
    filepath = os.path.join(upload_folder, filename)
    if os.path.exists(filepath):
        return filename
    else:
        return ""

@bp.route("/run_qc/<type>/<gb_acc>/", methods=["POST"])
@login_required
def run_qc(type, gb_acc):
    # first we save the file

    if type == "u":
        upload_folder = os.path.join(
            current_app.config["TNC_DATA_DIR"], current_app.config["TNC_UPLOAD_FOLDER"]
        )
        upload_folder = os.path.join(upload_folder, current_user.username)
        user_gb = UserGenbank.query.filter_by(accession=gb_acc).first()
        filename = os.path.join(upload_folder, user_gb.filename + ".gb")
    else:
        gb_folder = current_app.config["TNC_GENBANK_DIR"]
        upload_folder = os.path.join(current_dir, gb_folder)
        filename = os.path.join(upload_folder, gb_acc + ".gb")

    # running script
    # tncentral_qc_v14.pl genbank_file accessory_folder output_file
    perl = current_app.config["PERL"]
    qc_script = current_app.config["QC_SCRIPT"]
    qc_acc = current_app.config["QC_ACCESSORY"]
    filename_out = filename + ".out"
    command = f"{perl} {qc_script} '{filename}' {qc_acc} '{filename_out}'"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
    if not os.path.exists(filename_out) and result.stderr != "b''":
        with open(filename_out, "wb") as writer:
            writer.write(
                b"There was an error running the script. Please contact admin.\n"
            )
            writer.write(result.stderr)

    stdout = result.stdout
    stderr = result.stderr
    text = ""
    return send_file(filename_out, mimetype="text/plain")


@bp.route("/load/<accession>/", methods=["POST"])
@login_required
def load_to_db(accession):
    return_status = {}

    u_id = current_user.get_id()
    user_gb = UserGenbank.query.filter_by(user_id=u_id, accession=accession).first()
    te_entry = user_gb.te_entry

    loaded_entry = Te_Entry.query.filter_by(
        in_production=1, accession=accession
    ).first()
    if loaded_entry:
        loaded_internals = Te_Entry.query.filter_by(
            in_production=1, entry_id_parent=loaded_entry.entry_id
        ).all()
        db.session.delete(loaded_entry)
        for te_internal in loaded_internals:
            db.session.delete(te_internal)
    db.session.commit()
    # will copy all internals elements, except
    # the internal mobile elements
    new_entry = te_entry.copy()
    new_entry.in_production = 1
    db.session.add(new_entry)

    te_internals = Te_Entry.query.filter_by(entry_id_parent=te_entry.entry_id).all()
    for te_internal in te_internals:
        internal_obj = te_internal.copy()
        internal_obj.entry_id_parent = new_entry.entry_id
        internal_obj.in_production = 1
        db.session.add(internal_obj)
    db.session.commit()

    # copying files
    upload_folder = get_upload_folder()
    gb_folder = os.path.join(current_dir, current_app.config["TNC_GENBANK_DIR"])
    img_folder = os.path.join(current_dir, current_app.config["TNC_IMAGE_DIR"])
    snap_folder = os.path.join(current_dir, current_app.config["TNC_SNAP_DIR"])
    fa_folder = os.path.join(current_dir, current_app.config["TNC_FASTA_DIR"])
    fa_fmt_folder = os.path.join(current_dir, current_app.config["TNC_FASTA_FMT_DIR"])
    csv_dir = os.path.join(current_dir, current_app.config["TNC_CSV_DIR"])
    # gb
    gb_src = os.path.join(upload_folder, accession + ".gb")
    shutil.copy2(gb_src, gb_folder)
    # log the change in log table
    save_change_log(Constants.UPLOAD_GENBANK, os.path.join(gb_folder, accession+".gb"),
                    "Genbank file loaded from user to db area.")
    # png
    img_src = os.path.join(upload_folder, accession + ".png")
    if os.path.exists(img_src):
        shutil.copy2(img_src, img_folder)
        # log the change in log table
        save_change_log(Constants.UPLOAD_IMAGE, os.path.join(img_folder, accession+".png"),
                        "Image file copied from user to db area.")
    # dna
    dna_src = os.path.join(upload_folder, accession + ".dna")
    if os.path.exists(dna_src):
        shutil.copy2(dna_src, snap_folder)
        # log the change in log table
        save_change_log(Constants.UPLOAD_SNAPGENE, os.path.join(snap_folder, accession+".dna"),
                        "Snapgene file copied from user to db area.")
    # export fa
    fa_src = os.path.join(upload_folder, accession + ".fa")
    shutil.copy2(fa_src, fa_folder)
    # export fa_fmt
    sequence = gb_utils.get_sequence_from_file(fa_src)
    gb_utils.export_fmt_fasta(sequence, accession, fa_fmt_folder)
    return_status["status"] = "ok"
    # export csv
    csv_line = new_entry.as_csv()
    gb_utils.export_csv_file(csv_line, csv_dir, accession)

    # now we will recreate the blast files
    queue = current_app.config["RQ_QUEUE_DEFAULT"]
    q = Queue(name=queue, connection=conn)
    # from flask_tn.utils.job_utils import recreate_blast
    q.enqueue(job_utils.recreate_blast)

    return jsonify(return_status)


@bp.route("/image/<type>/<acc>", methods=["GET"])
@login_required
def get_image(type, acc):
    image_path = ""
    if type == "u":
        upload_folder = get_upload_folder()

        user_gb = (
            UserGenbank.query.join(Te_Entry)
            .filter(
                Te_Entry.accession == acc, UserGenbank.user_id == current_user.get_id()
            )
            .first()
        )

        if user_gb.image_name != None:
            image_path = os.path.join(upload_folder, user_gb.image_name)
    else:
        img_folder = current_app.config["TNC_IMAGE_DIR"]
        image_path = os.path.join(current_dir, img_folder, acc+".png")
        if not os.path.exists(image_path):
            image_path = ""

    if image_path == "":
        img_folder = current_app.config["TNC_IMAGE_DIR"]
        image_path = os.path.join(current_dir, img_folder, "error.png")

    return send_file(image_path, mimetype="image/png")


@bp.route("/image/<type>/<acc>", methods=["DELETE"])
@login_required
def delete_image(type, acc):
    return_status = {}
    if type == "u":
        u_id = current_user.get_id()
        upload_folder = get_upload_folder()

        user_gb = (
            UserGenbank.query.join(Te_Entry)
            .filter(Te_Entry.accession == acc, UserGenbank.user_id == u_id)
            .first()
        )

        if user_gb.image_name != None:
            image_path = os.path.join(upload_folder, user_gb.image_name)
            user_gb.image_name = None
            user_gb.image_size = None
            user_gb.image_time = None
            db.session.commit()
            os.remove(image_path)
            # log the change in log table
            save_change_log(Constants.UPLOAD_IMAGE, image_path, "Image file deleted from user area.")
            return_status["status"] = "ok"
        else:
            return_status["status"] = "error"
            return_status["error"] = "There is no file to delete."
    elif type == "d":
        image_dir = os.path.join(current_dir, current_app.config["TNC_IMAGE_DIR"])
        filepath = os.path.join(image_dir, acc+".png")
        if os.path.exists(filepath):
            copypath = os.path.join(image_dir, acc+".png.last")
            shutil.copyfile(filepath, copypath)
            os.remove(filepath)
            # log the change in log table
            save_change_log(Constants.UPLOAD_IMAGE, filepath,"Image file deleted from db area.")
            return_status["status"] = "ok"
        else:
            return_status["status"] = "error"
            return_status["error"] = "There is no file to delete."
    return jsonify(return_status)


@bp.route("/snapgene/<type>/<acc>", methods=["DELETE"])
@login_required
def delete_snapgene(type, acc):
    return_status = {}
    try:
        if type == "u":
            u_id = current_user.get_id()
            upload_folder = get_upload_folder()

            user_gb = (
                UserGenbank.query.join(Te_Entry)
                .filter(Te_Entry.accession == acc, UserGenbank.user_id == u_id)
                .first()
            )

            if user_gb.snap_name != None:
                snap_path = os.path.join(upload_folder, user_gb.snap_name)
                user_gb.snap_name = None
                user_gb.snap_size = None
                user_gb.snap_time = None
                db.session.commit()
                if os.path.exists(snap_path):
                    os.remove(snap_path)
                    # log the change in log table
                    save_change_log(Constants.UPLOAD_SNAPGENE, snap_path,
                                    "Snapgene file deleted from user area.")
                    return_status["status"] = "ok"
                else:
                    return_status["status"] = "error"
                    return_status["error"] = "There is no file to delete."
            else:
                return_status["status"] = "error"
                return_status["error"] = "There is no file to delete."
        elif type == "d":
            snap_dir = os.path.join(current_dir, current_app.config['TNC_SNAP_DIR'])
            filepath = os.path.join(snap_dir, acc+".dna")
            if os.path.exists(filepath):
                copy_file = os.path.join(snap_dir, acc+".dna.last")
                shutil.copyfile(filepath, copy_file)
                os.remove(filepath)
                # log the change in log table
                save_change_log(Constants.UPLOAD_SNAPGENE, filepath,
                                "Snapgene file deleted from db area.")
                return_status["status"] = "ok"
            else:
                return_status["status"] = "error"
                return_status["error"] = "There is no file to delete."
    except Exception as exc:
        print("-----------Exception")
        print(exc)
        return_status["status"] = "error"
        return_status["error"] = "Server error."
    
    return jsonify(return_status)


@bp.route("/upload_image", methods=["POST"])
@login_required
def upload_image():
    accession = utils.get_request_value(request.form, "accession")
    image = request.files["snapgene_image"]
    return_status = {}
    filename = secure_filename(image.filename)
    # TODO: check if name of the image is the same of the genbank

    accepted_images = ".png"
    if not filename.lower().endswith(accepted_images):
        return_status["status"] = "error"
        return_status["error"] = "Extension not allowed. Only .png for image files."
    else:
        try:
            u_id = current_user.get_id()
            upload_folder = get_upload_folder()

            user_gb = (
                UserGenbank.query.join(Te_Entry)
                .filter(Te_Entry.accession == accession, UserGenbank.user_id == u_id)
                .first()
            )
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            extension = filename.split(".")[-1]
            new_filename = user_gb.filename + "." + extension
            full_filename = os.path.join(upload_folder, new_filename)
            image.save(full_filename)
            # log the change in log table
            save_change_log(Constants.UPLOAD_IMAGE, full_filename,
                            "Image file uploaded from user area.")
            filesize = os.path.getsize(full_filename)
            filesize = filesize / 1000  # in kilobytes
            user_gb.image_name = new_filename
            user_gb.image_size = filesize
            user_gb.image_time = datetime.date.today()
            db.session.commit()
            return_status["status"] = "ok"
            return_status["name"] = new_filename
        except:
            return_status["status"] = "error"
            return_status["error"] = (
                "An error has ocurred in the server. Please contact admin."
            )
    return jsonify(return_status)


@bp.route("/upload_snapgene", methods=["POST"])
@login_required
def upload_snapgene():
    accession = utils.get_request_value(request.form, "accession")
    file_obj = request.files["snapgene_file"]
    return_status = {}
    filename = secure_filename(file_obj.filename)

    accepted_extensios = ".dna"
    if not filename.lower().endswith(accepted_extensios):
        return_status["status"] = "error"
        return_status["error"] = "Extension not allowed. Only .dna for snapgene files."
    else:
        try:
            u_id = current_user.get_id()
            upload_folder = get_upload_folder()

            user_gb = (
                UserGenbank.query.join(Te_Entry)
                .filter(Te_Entry.accession == accession, UserGenbank.user_id == u_id)
                .first()
            )
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            name, extension = os.path.splitext(filename)
            new_filename = user_gb.filename + extension
            full_filename = os.path.join(upload_folder, new_filename)
            file_obj.save(full_filename)
            # log the change in log table
            save_change_log(Constants.UPLOAD_SNAPGENE, full_filename,
                            "Snapgene file uploaded from user area.")

            filesize = os.path.getsize(full_filename)
            filesize = filesize / 1000  # in kilobytes
            user_gb.snap_name = new_filename
            user_gb.snap_size = filesize
            user_gb.snap_time = datetime.date.today()
            db.session.commit()
            return_status["status"] = "ok"
            return_status["name"] = new_filename
        except:
            return_status["status"] = "error"
            return_status["error"] = "Server error."

    return jsonify(return_status)

@bp.route("/upload_snapgene_db", methods=["POST"])
@login_required
def upload_snapgene_db():
    accession = utils.get_request_value(request.form, "accession")
    file_obj = request.files["snapgene_file"]
    return_status = {}
    filename = secure_filename(file_obj.filename)

    accepted_extensios = ".dna"
    if not filename.lower().endswith(accepted_extensios):
        return_status["status"] = "error"
        return_status["error"] = "Extension not allowed. Only .dna for snapgene files."
    else:
        try:
            snap_folder = os.path.join(current_dir, current_app.config["TNC_SNAP_DIR"])
            full_filename = os.path.join(snap_folder, accession+".dna")

            if os.path.exists(full_filename):
                copy_filename = os.path.join(snap_folder, accession+".dna.last")
                shutil.copyfile(full_filename, copy_filename)
                os.remove(full_filename)
            file_obj.save(full_filename)
            # log the change in log table
            save_change_log(Constants.UPLOAD_SNAPGENE, full_filename,
                            "Snapgene file uploaded from db area.")
            return_status["status"] = "ok"
            return_status["name"] = accession+".dna"
        except Exception as exc:
            print("-----------Exception")
            print(exc)
            return_status["status"] = "error"
            return_status["error"] = "Server error. Please report us the error."

    return jsonify(return_status)

@bp.route("/upload_image_db", methods=["POST"])
@login_required
def upload_image_db():
    accession = utils.get_request_value(request.form, "accession")
    image = request.files["snapgene_image"]
    return_status = {}
    filename = secure_filename(image.filename)
    # TODO: check if name of the image is the same of the genbank

    accepted_images = ".png"
    if not filename.lower().endswith(accepted_images):
        return_status["status"]="error"
        return_status["error"]="Incorrect image extension. Only '.png' allowed."
    else:
        try:
            img_dir = current_app.config["TNC_IMAGE_DIR"]
            file_folder = os.path.join(current_dir, img_dir)

            extension = filename.split(".")[-1]
            new_filename = f"{accession}.{extension}"
            full_filename = os.path.join(file_folder, new_filename)
            if os.path.exists(full_filename):
                copy_filename = os.path.join(file_folder, accession+".png.last")
                shutil.copyfile(full_filename, copy_filename)
                os.remove(full_filename)
            image.save(full_filename)
            # log the change in log table
            save_change_log(Constants.UPLOAD_IMAGE, full_filename,
                            "Image file uploaded from db area.")
            return_status["status"] = "ok"
            return_status["name"] = new_filename
        except Exception as exc:
            print("-----------Exception")
            print(exc)
            return_status["status"] = "error"
            return_status["error"] = "Server error. Please report us the error."
    
    return jsonify(return_status)


from flask_tn.utils import qc
@bp.route("/upload_qc", methods=["POST"])
@login_required
def upload_qc():
    qc_filename = utils.get_request_value(request.form, "qc_filename")
    obj_file = request.files["fileToUpload"]
    return_status = {}
    # possible files:
    # aro_categories.tsv
    # aro_index.tsv
    # tncentral_accessory_gene_annotation.txt
    # tncentral_TA_gene_annotation.txt
    # tncentral_transposase_annotation.txt
    upload_file = get_upload_folder() # we will save first in the upload folder
    # to be able to validate, later we will copy to the correct folder
    filename = secure_filename(obj_file.filename)
    full_filename = os.path.join(upload_file, qc_filename)
    obj_file.save(full_filename)
    # log the change in log table
    save_change_log(Constants.UPLOAD_QC, full_filename, "QC file uploaded")
    utils.rm_carriage(full_filename, current_app.config["PERL"])
    list_errors = []
    list_errors = qc.validate_file(full_filename)

    if len(list_errors) > 0:
        return_status["status"]="error"
        return_status["error"]=""
        for error in list_errors:
            return_status["error"] +=f"Error in line {error['line']}: {error['error']}<br>"
    else:
        to_path = os.path.join(current_app.config["QC_ACCESSORY"], qc_filename)
        if os.path.exists(to_path):
            os.rename(to_path, to_path+".old")
        shutil.copyfile(full_filename, to_path)
        return_status["status"]="ok"
    return jsonify(return_status)

@bp.route("/genbank/<accession>", methods=["DELETE"])
@login_required
def delete_user_entry(accession):
    return_status = {}
    in_prod = utils.get_request_value(request.form, "in_prod")

    if in_prod == "0":
        uname = current_user.username
        user_gb = (
            UserGenbank.query.join(User)
            .filter(User.username == uname, UserGenbank.accession == accession)
            .first()
        )

        upload_folder = get_upload_folder()
        # genbank
        exts = [".gb", ".ori.gb", ".png", ".fa", ".gb.out", ".dna"]
        for ext in exts:
            filepath = os.path.join(upload_folder, user_gb.filename + ext)
            if os.path.exists(filepath):
                os.remove(filepath)
                # log the change in log table
                if ext == '.gb':
                    save_change_log(Constants.UPLOAD_GENBANK, filepath,
                                    "Genbank file deleted from user area.")
                elif ext == '.png':
                    save_change_log(Constants.UPLOAD_IMAGE, filepath,
                                    "Image file deleted from user area.")
                elif ext == '.dna':
                    save_change_log(Constants.UPLOAD_SNAPGENE, filepath,
                                    "Snapgene file deleted from user area.")
        db.session.delete(user_gb.te_entry)
        db.session.commit()
        return_status["status"] = "ok"
    else:
        entry = Te_Entry.query.filter(
            Te_Entry.accession == accession,
            Te_Entry.entry_id_parent == None,
            Te_Entry.in_production == 1,
        ).first()
        if entry:
            db.session.delete(entry)
            db.session.commit()
            dirs = [
                "TNC_GENBANK_DIR",
                "TNC_GENBANK_DIR",
                "TNC_GENBANK_DIR",
                "TNC_FASTA_DIR",
                "TNC_FASTA_FMT_DIR",
                "TNC_CSV_DIR",
                "TNC_IMAGE_DIR",
            ]
            exts = [".gb", ".ori.gb", ".gb.out", ".fa", ".fmt", ".csv", ".png"]
            for i in range(0, len(dirs)):
                filepath = os.path.join(
                    current_dir, current_app.config[dirs[i]], accession + exts[i]
                )
                if os.path.exists(filepath):
                    os.remove(filepath)
                    # log the change in log table
                    if exts[i] == '.gb':
                        save_change_log(Constants.UPLOAD_GENBANK, filepath,
                                        "Genbank file deleted from db area.")
                    elif exts[i] == '.png':
                        save_change_log(Constants.UPLOAD_IMAGE, filepath,
                                        "Image file deleted from db area.")
                    elif exts[i] == '.dna':
                        save_change_log(Constants.UPLOAD_SNAPGENE, filepath,
                                        "Snapgene file deleted from db area.")
            return_status["status"] = "ok"
        else:
            print("Entry está vazio")
            return_status["error"] = "Genbank not found"

        ## now we will recreate the blast files
        rq_def = current_app.config["RQ_QUEUE_DEFAULT"]
        q = Queue(name=rq_def, connection=conn)
        from flask_tn.utils.job_utils import recreate_blast

        job = q.enqueue(recreate_blast)
        # print(job.get_id)

    return jsonify(return_status)

@bp.route("/download_qc_file/<filename>")
def download_qc_file(filename):
    download_path = os.path.join(current_app.config["QC_ACCESSORY"], filename)
    if os.path.exists(download_path):
        return send_file(download_path, as_attachment=True)


@bp.route("/download_all", methods=["POST"])
@login_required
def download_all():
    in_prod = utils.get_request_value(request.form, "in_prod")
    if in_prod == "0":
        uname = current_user.username
        user_gb = UserGenbank.query.join(User).filter(User.username == uname).all()
        upload_folder = get_upload_folder()

        temp_folder = os.path.join(upload_folder, "temp")

        random_token = token_hex(3).upper()
        download_folder = os.path.join(temp_folder, random_token, uname)
        os.makedirs(download_folder, exist_ok=True)

        for u_gb in user_gb:
            genbank_name = u_gb.filename
            filepath = os.path.join(upload_folder, genbank_name + ".gb")
            shutil.copy(filepath, download_folder)
            if u_gb.image_name != None:
                image_name = u_gb.image_name
                filepath = os.path.join(upload_folder, image_name)
                if os.path.exists(filepath):
                    shutil.copy(filepath, download_folder)
            if u_gb.snap_name != None:
                snap_name = u_gb.snap_name
                filepath = os.path.join(upload_folder, snap_name)
                if os.path.exists(filepath):
                    shutil.copy(filepath, download_folder)
        localfile = os.path.join(temp_folder, random_token, uname)
        shutil.make_archive(localfile, "zip", download_folder)
        localfile = localfile + ".zip"

    return send_file(localfile, as_attachment=True)


@bp.route("/delete_all", methods=["DELETE"])
@login_required
def delete_all_user():
    uname = current_user.username
    user_gb = UserGenbank.query.join(User).filter(User.username == uname).all()
    upload_folder = get_upload_folder()
    # genbank
    exts = [".gb", ".ori.gb", ".png", ".fa", ".gb.out", ".dna"]
    for u_gb in user_gb:
        filename = u_gb.filename
        db.session.delete(u_gb.te_entry)
        for ext in exts:
            filepath = os.path.join(upload_folder, filename + ext)
            if os.path.exists(filepath):
                os.remove(filepath)
                # log the change in log table
                if ext == '.gb':
                    save_change_log(Constants.UPLOAD_GENBANK, filepath, "Genbank file deleted from db area.")
                elif ext == '.png':
                    save_change_log(Constants.UPLOAD_IMAGE, filepath, "Image file deleted from db area.")
                elif ext == '.dna':
                    save_change_log(Constants.UPLOAD_SNAPGENE, filepath, "Snapgene file deleted from db area.")
                
    db.session.commit()

    return_status = {"status": "ok"}

    return jsonify(return_status)


def append_error(dict_status, error_key, key, value):
    if error_key in dict_status:
        dict_status[error_key].append({key: value})
    else:
        dict_status[key] = [{key: value}]


@bp.route("/upload_to_db", methods=["POST"])
@login_required
def upload_to_db():
    uploaded_files = request.files.getlist("genbank_file[]")
    count = 0
    return_status = {"status": "ok"}

    return_status["count_total"] = len(uploaded_files)
    list_images = []
    list_snapgene = []
    for up_file in uploaded_files:
        filename = secure_filename(up_file.filename)
        ext = get_file_ext(filename)
        if check_extension(ext):
            try:
                if ext == "gb":
                    file_uploaded = upload_obj_gb(up_file)
                    return_status[filename] = "ok"
                elif ext == "png":
                    list_images.append(up_file)
                elif ext == "dna":
                    list_snapgene.append(up_file)
                else:
                    status = upload_zip(up_file)
                    if status:
                        return_status[filename] = "ok"
                    else:
                        return_status["status"] = "error"
                        return_status[filename] = "Load error"
            except Exception as e:
                return_status["status"] = "error"
                return_status[filename] = f"Load error. {e}"
            count += 1
        else:
            return_status["status"] = "error"
            return_status[filename] = "Extension Error. Only gb, png and zip allowed."
    for obj_img in list_images:
        status = upload_png_from_user(obj_img)
        filename = secure_filename(obj_img.filename)
        if not status:
            count -= 1
            return_status["status"] = "error"
            return_status[filename] = "No genbank associated."
    for obj_snap in list_snapgene:
        status = upload_snap_from_user(obj_snap)
        filename = secure_filename(obj_snap.filename)
        if not status:
            count -= 1
            return_status["status"] = "error"
            return_status[filename] = "No genbank associated."

    return_status["count"] = count
    q_def = current_app.config["RQ_QUEUE_DEFAULT"]
    q = Queue(name=q_def, connection=conn)
    from flask_tn.utils.job_utils import export_pubmed_files

    q.enqueue(export_pubmed_files)

    return jsonify(return_status)


def get_basename(filename):
    array_names = filename.split(".")
    if len(array_names) > 1:
        basename = ".".join(array_names[0:-1])
    else:
        basename = filename

    return basename


def get_file_ext(filename):
    array_names = filename.split(".")
    ext = array_names[-1]
    if len(array_names) > 1:
        return ext
    else:
        return ""


def check_extension(ext):
    return ext in ["gb", "png", "dna", "zip"]


def upload_zip(obj_file):
    return_status = True
    filename = secure_filename(obj_file.filename)

    upload_folder = get_upload_folder()
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    full_filename = os.path.join(upload_folder, filename)
    obj_file.save(full_filename)
    filesize = os.path.getsize(full_filename)
    filesize = filesize / 1000  # in kilobytes
    with zipfile.ZipFile(full_filename, "r") as zip_ref:
        zip_ref.extractall(path=upload_folder)
        namelist = zip_ref.namelist()
        copy_before = False
        new_dir = os.path.join(upload_folder, namelist[0])
        if os.path.isdir(new_dir):
            copy_before = True
        list_images = []
        list_snap = []
        for f in zip_ref.namelist():
            f_path = os.path.join(upload_folder, f)
            if os.path.isfile(f_path):
                if copy_before:
                    shutil.copy(f_path, upload_folder)
                basename = os.path.basename(f_path)
                up_path = os.path.join(upload_folder, basename)
                ext = get_file_ext(basename)
                if ext == "gb":
                    save_gb_file(upload_folder, basename)
                elif ext == "png":
                    list_images.append(basename)
                elif ext == "dna":
                    list_snap.append(basename)
                else:
                    return_status = False
        for img in list_images:
            save_png_file(upload_folder, img)
        for snap in list_snap:
            save_snap_file(upload_folder, snap)

    try:
        os.remove(full_filename)
        if copy_before:
            shutil.rmtree(new_dir)
    except:
        return_status = False

    return return_status


def upload_obj_gb(obj_file):
    filename = secure_filename(obj_file.filename)
    upload_folder = get_upload_folder()
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    # Create the full path to save the uploaded file
    filename_no_ext = filename.replace(".gb", "")
    full_filename = os.path.join(upload_folder, filename)
    # Save the uploaded FASTA file with the job ID as the filename
    obj_file.save(full_filename)
    accession = save_gb_file(upload_folder, filename)

    return filename


def save_gb_file(upload_folder, filename):
    basename = os.path.basename(filename)
    filename_no_ext = basename.replace(".gb", "")
    full_filename = os.path.join(upload_folder, filename)
    # logging changes to table log
    save_change_log(Constants.UPLOAD_GENBANK, full_filename, "Genbank file uploaded.")

    filesize = os.path.getsize(full_filename)
    filesize = filesize / 1000  # in kilobytes
    perl_command = current_app.config["PERL"]
    utils.rm_carriage(full_filename, perl_command)

    gb_obj = Genbank.get_genbank_object(full_filename)
    # rename file to accession.gb
    gb_obj.accession = gb_obj.accession.replace(' ', '')
    acc = gb_obj.accession
    if acc:
        # before upload, remove possible old files from the same accession
        new_filename = os.path.join(upload_folder, acc+".gb")
        existed_ext = ['.gb.out', '.dna', '.png']
        for ext in existed_ext:
            file_to_remove = os.path.join(upload_folder, acc+ext)
            if os.path.exists(file_to_remove):
                os.remove(file_to_remove)

        if new_filename != full_filename:
            os.rename(full_filename, new_filename)
        # save in the db
        user_gb = UserGenbank()
        user_gb.user_id = current_user.user_id
        user_gb.file_size = filesize
        user_gb.filename = acc
        user_gb.accession = gb_obj.accession

        # delete if exists
        uname = current_user.username
        delete_user_db = (
            UserGenbank.query.join(User)
            .filter(User.username == uname, UserGenbank.accession == gb_obj.accession)
            .first()
        )
        if delete_user_db:
            db.session.delete(delete_user_db.te_entry)
            db.session.delete(delete_user_db)
            db.session.commit()

        main_entry = gb_utils.save_obj_to_db(gb_obj)
        main_entry.user_gb.append(user_gb)
        db.session.add(main_entry)
        db.session.commit()

        full_filename = os.path.join(upload_folder, acc + ".fa")

        # separate genbank from fasta:
        with open(full_filename, "w") as h:
            h.write(f">{gb_obj.accession}\n")
            h.write(gb_obj.sequence_as_text())

    return gb_obj.accession


def upload_png_from_user(obj_img):
    upload_folder = get_upload_folder()
    filename = secure_filename(obj_img.filename)

    acc = get_basename(filename)
    user_gb = (
        UserGenbank.query.join(Te_Entry)
        .filter(Te_Entry.accession == acc, UserGenbank.user_id == current_user.get_id())
        .first()
    )
    return_status = False
    if user_gb:
        full_filename = os.path.join(upload_folder, filename)
        obj_img.save(full_filename)
        return_status = save_png_file(upload_folder, filename)

    return return_status


def save_png_file(upload_folder, image_name):
    acc = get_basename(image_name)

    u_id = current_user.get_id()
    upload_folder = get_upload_folder()

    user_gb = (
        UserGenbank.query.join(Te_Entry)
        .filter(Te_Entry.accession == acc, UserGenbank.user_id == u_id)
        .first()
    )

    return_status = True
    if user_gb:
        full_filename = os.path.join(upload_folder, image_name)
        # logging changes to table log
        save_change_log(Constants.UPLOAD_IMAGE, full_filename, "Image file saved.")

        filesize = os.path.getsize(full_filename)
        filesize = filesize / 1000  # in kilobytes

        user_gb.image_name = image_name
        user_gb.image_size = filesize
        user_gb.image_time = datetime.date.today()
        db.session.commit()
    else:
        return_status = False
    return return_status


def upload_snap_from_user(obj_snap):
    upload_folder = get_upload_folder()
    filename = secure_filename(obj_snap.filename)

    acc = get_basename(filename)
    user_gb = (
        UserGenbank.query.join(Te_Entry)
        .filter(Te_Entry.accession == acc, UserGenbank.user_id == current_user.get_id())
        .first()
    )
    return_status = False
    if user_gb:
        full_filename = os.path.join(upload_folder, filename)
        obj_snap.save(full_filename)
        return_status = save_snap_file(upload_folder, filename)

    return return_status

def save_snap_file(upload_folder, snap_name):
    acc = get_basename(snap_name)

    u_id = current_user.get_id()
    upload_folder = get_upload_folder()

    user_gb = (
        UserGenbank.query.join(Te_Entry)
        .filter(Te_Entry.accession == acc, UserGenbank.user_id == u_id)
        .first()
    )

    return_status = True
    if user_gb:
        full_filename = os.path.join(upload_folder, snap_name)
        # logging changes to table log
        save_change_log(Constants.UPLOAD_SNAPGENE, full_filename, "Snapgene file saved.")

        filesize = os.path.getsize(full_filename)
        filesize = filesize / 1000  # in kilobytes

        user_gb.snap_name = snap_name
        user_gb.snap_size = filesize
        user_gb.snap_time = datetime.date.today()
        db.session.commit()
    else:
        return_status = False
    return return_status


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("webui.index"))


@bp.route("/change_pwd")
@login_required
def change_pwd():
    return render_template("admin/change_password.html")


@bp.route("/change_pwd", methods=["POST"])
@login_required
def submit_change_pwd():
    cur_pwd = utils.get_request_value(request.form, "cur_pwd")
    new_pwd = utils.get_request_value(request.form, "new_pwd")
    con_new_pwd = utils.get_request_value(request.form, "con_new_pwd")
    user = current_user
    if check_password_hash(user.password, cur_pwd):
        if new_pwd != con_new_pwd:
            flash("New password is not equal the confirmation password.", "error")
            return render_template("admin/change_password.html")
        else:
            new_password = generate_password_hash(new_pwd)
            user.password = new_password
            db.session.commit()
            flash("Password has been changed.", "success")
            return render_template("admin/change_password.html")

    else:
        flash("Current password is incorrect. Password has not been changed.", "error")
        return render_template("admin/change_password.html")


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


def get_query_from_drop(query, filter_text, drop_value, db_class, col_name):
    filter_text = build_match_filter(filter_text, drop_value)
    query = query.filter(getattr(db_class, col_name).like(filter_text))
    return query


from sqlalchemy import func


@bp.route("/te/")
@login_required
def admin_dbdata():
    """
    This function is the endpoint of the search by Transposable Elements.
    Given the parameters sent by GET method, this function searches the
    database and return the list of transposable elements as a json like
    format with the keys: data, recordsFiltered, recordsTotal, draw.
    """
    query = Te_Entry.query.filter(
        Te_Entry.entry_id_parent == None, Te_Entry.in_production == 1
    )

    user_filters = ["type", "family", "group", "transposition"]
    for u_filter in user_filters:
        value = utils.get_request_value(request.args, u_filter)
        if value != "":
            query = query.filter(
                func.lower(getattr(Te_Entry, u_filter)) == func.lower(value)
            )

    total_query = query.count()
    # It's not possible to work with the size of the
    # request.args because this variable is manipulated
    # by datatable.js and they send a lot of values for
    # their own control. Since we are sending our values together
    # with the table variables we have to check one by one if the value exists
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
                Te_Entry.date.like(f"%{search}%"),
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
        view_db = {
            "select": "entry_id",
            "accession": "accession",
            "type": "type",
            "family": "family",
            "group": "group",
            "organism": "organism",
            "country": "country",
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
        "draw": request.args.get("draw", type=int),
    }

from flask_tn.utils.qc import read_qc_file
import operator
@bp.route("/qc_file/<filename>")
@login_required
def qc_file(filename):
    # tncentral_accessory_gene_annotation.txt
    # aro_categories.tsv
    # aro_index.tsv
    # tncentral_TA_gene_annotation.txt
    # tncentral_transposase_annotation.txt
    # first column without search
    filepath = os.path.join(current_app.config["QC_ACCESSORY"], filename)
    
    list_obj = read_qc_file(filepath)
    total_query = len(list_obj)
    # It's not possible to work with the size of the
    # request.args because this variable is manipulated
    # by datatable.js and they send a lot of values for
    # their own control. Since we are sending our values together
    # with the table variables we have to check one by one if the value exists
    total_filtered = total_query

    # search filter
    search = request.args.get("search[value]")
    filtered_obj = []
    if search:
        for single_obj in list_obj:
            if single_obj.search(search):
                filtered_obj.append(single_obj)
        list_obj = filtered_obj
        total_filtered = len(filtered_obj)

    # sorting
    i = 0
    while True:
        col_index = request.args.get(f"order[{i}][column]")
        if col_index is None:
            break
        col_name = request.args.get(f"columns[{col_index}][data]")
        view_db = get_qc_view(filename)
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        list_obj.sort(key = operator.attrgetter(view_db[col_name]), reverse=descending)
        i += 1
    

    # # pagination
    start = request.args.get("start", type=int)
    if not start:
        start = 0
    length = request.args.get("length", type=int)
    if not length:
        length = total_query
    list_obj = list_obj[start:start+length]

    return {
        "data": [x.to_datatable() for x in list_obj],
        "recordsFiltered": total_filtered,
        "recordsTotal": total_query,
        "draw": request.args.get("draw", type=int),
    }

def get_qc_view(filename):
    if filename == qc.ACCESSORY_GENE_FILE:
        view_db = {
            "line_number": "lineNumber",
            "gene_class": "geneClass",
            "subclass": "subClass",
            "gene": "gene",
            "product": "product",
            "sequence_family": "sequenceFamily",
            "chemistry": "chemistry"
        }
    elif filename == qc.TA_GENE_FILE:
        view_db = {
            "line_number": "lineNumber",
            "gene_class": "geneClass",
            "subclass": "subClass",
            "gene": "gene",
            "product": "product",
            "sequence_family": "sequenceFamily",
            "target": "target"
        }
    elif filename == qc.TRANSPOSASE_FILE:
        view_db = {
            "line_number": "lineNumber",
            "gene_class": "geneClass",
            "gene": "gene",
            "product": "product",
            "sequence_family": "sequenceFamily"
        }
    elif filename == qc.CARD_CATEGORIES_FILE:
        view_db = {
            "line_number": "lineNumber",
            "category": "category",
            "accession": "accession",
            "name": "name"
        }
    elif filename == qc.CARD_INDEX_FILE:
        view_db = {
            "line_number": "lineNumber",
            "aro_accession": "aroAccession",
            "cv_term_id": "cvTermId",
            "model_seq_id": "modelSeqId",
            "model_id": "modelId",
            "model_name": "modelName",
            "aro_name": "aroName",
            "protein_accession": "proteinAccession",
            "dna_accession": "dnaAccession",
            "amr_family": "amrGeneFamily",
            "drug_class": "drugClass",
            "resistance_mechanism": "resistanceMecanism",
            "card_short_name": "cardShortName"
        }
    elif filename == qc.METAL_TARGETS_FILE:
        view_db = {
            "line_number": "lineNumber",
            "metal_name": "metalName"
        }
    else:
        view_db = {}
    return view_db

@bp.route("/qc_file/<file>", methods=["POST"])
@login_required
def qc_file_post(file):
    # tncentral_accessory_gene_annotation.txt
    # aro_categories.tsv
    # aro_index.tsv
    # tncentral_TA_gene_annotation.txt
    # tncentral_transposase_annotation.txt
    # first column without search
    filepath = os.path.join(current_app.config["QC_ACCESSORY"], file)
    line = utils.get_request_value(request.form, "line")
    line_number = int(utils.get_request_value(request.form, "line_number"))
    has_header = utils.get_request_value(request.form, "has_header")
    if has_header == '0':
        line_number = int(line_number)-1
        
    qc.update_line_in_file(filepath, line, line_number)
    # log the change in log table
    save_change_log(Constants.UPLOAD_QC, filepath, "QC file updated.")

    return_status = {"status": "ok"}
    return jsonify(return_status)

@bp.route("/qc_file/<file>", methods=["PUT"])
@login_required
def qc_file_put(file):
    # tncentral_accessory_gene_annotation.txt
    # aro_categories.tsv
    # aro_index.tsv
    # tncentral_TA_gene_annotation.txt
    # tncentral_transposase_annotation.txt
    # first column without search
    filepath = os.path.join(current_app.config["QC_ACCESSORY"], file)
    line = utils.get_request_value(request.form, "line")
    qc.update_line_in_file(filepath, line)
    # log the change in log table
    save_change_log(Constants.UPLOAD_QC, filepath, "QC file updated.")
    return_status = {"status": "ok"}
    return jsonify(return_status)

@bp.route("/qc_file/<file>", methods=["DELETE"])
@login_required
def qc_file_delete(file):
    # tncentral_accessory_gene_annotation.txt
    # aro_categories.tsv
    # aro_index.tsv
    # tncentral_TA_gene_annotation.txt
    # tncentral_transposase_annotation.txt
    # first column without search
    filepath = os.path.join(current_app.config["QC_ACCESSORY"], file)
    line_number = int(utils.get_request_value(request.form, "line_number"))
    has_header = utils.get_request_value(request.form, "has_header")
    if has_header == '0':
        line_number = int(line_number)-1
    qc.delete_line_in_file(filepath, line_number)
    # log the change in log table
    save_change_log(Constants.UPLOAD_QC, filepath, "QC file deleted.")

    return_status = {"status": "ok"}
    return jsonify(return_status)

@bp.route("/user_gb/")
@login_required
def get_data():
    user_id = current_user.user_id
    query = UserGenbank.query.filter(UserGenbank.user_id == user_id)
    total_query = query.count()
    # It's not possible to work with the size of the
    # request.args because this variable is manipulated
    # by datatable.js and they send a lot of values for
    # their own control. Since we are sending our values together
    # with the table variables we have to check one by one if the value exists
    #

    total_filtered = total_query
    # search filter
    search = request.args.get("search[value]")
    if search:
        query = query.filter(
            db.or_(
                UserGenbank.accession.like(f"%{search}%"),
                UserGenbank.filename.like(f"%{search}%"),
                UserGenbank.upload_time.like(f"%{search}%"),
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
        view_db = {
            "select": "user_id",
            "accession": "accession",
            "upload_time": "upload_time",
            "filesize": "file_size",
        }
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        col = getattr(UserGenbank, view_db[col_name])
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
        "data": [gb.datatable() for gb in query],
        "recordsFiltered": total_filtered,
        "recordsTotal": total_query,
        "draw": request.args.get("draw", type=int),
    }

from flask_tn.utils.jobs import JobWrapper, get_jobs_from_dir, tnjob_from_info
from rq import Queue
import worker # from tncentral
from rq.job import Job
import signal
@bp.route("/jobs_test/")
def jobs_test():
    jobs_dir = os.path.join(current_dir, current_app.config['TNC_JOB_DIR'])
    if not os.path.exists(jobs_dir):
        os.makedirs(jobs_dir)
    all_jobs = get_jobs_from_dir(jobs_dir)
    return {
        "data": [job.datatable() for job in all_jobs]
    }
    # import psutil
    # try:
    #     p = psutil.Process(2037515)
    #     # result = run(f"kill -9 2037515", stdout=PIPE, stderr=PIPE, shell=True)
    #     os.kill(2037515, signal.SIGKILL)
    #     # pp = p.parent()
    #     # pp.terminate()
    #     return {"data": p.username(), "status":p.status()}
    # except Exception as exc:
    #     return {"error": str(exc.with_traceback)}
    # queues = [current_app.config['RQ_QUEUE_LOW'],
    #             current_app.config['RQ_QUEUE_DEFAULT'],
    #             current_app.config['RQ_QUEUE_HIGH']
    #             ]
    # all_jobs = []
    # registries = ['canceled', 'deferred', 'failed', 'finished', 'scheduled','started']
    # for queue in queues:
    #     q = Queue(queue, connection=worker.conn)
    #     for registry in registries:
    #         reg = getattr(q, registry+"_job_registry")
    #         job_ids = reg.get_job_ids()
    #         if job_ids:
    #             for job_id in job_ids:
    #                 if job_id.startswith(current_app.config['RQ_JOB_PREFIX']):
    #                     try:
    #                         job = Job.fetch(job_id, worker.conn)
    #                         all_jobs.append(JobWrapper(job))
    #                     except NoSuchJobError as exc:
    #                         print("Error: ---------------------"+str(exc))
    #                         print("Registry: "+registry)
    #     enqueued_jobs = q.get_jobs()
    #     for enq_job in enqueued_jobs:
    #         all_jobs.append(JobWrapper(enq_job))
    
    # return {
    #     "data": [job.datatable() for job in all_jobs]
    # }

@bp.route("/jobs_data/")
@login_required
def jobs_data():
    # get jobs from queues
    # queues = [current_app.config['RQ_QUEUE_LOW'],
    #             current_app.config['RQ_QUEUE_DEFAULT'],
    #             current_app.config['RQ_QUEUE_HIGH']
    #             ]
    # all_jobs = []
    # registries = ['canceled', 'deferred', 'failed', 'finished', 'scheduled','started']
    # for queue in queues:
    #     q = Queue(queue, connection=worker.conn)
    #     for registry in registries:
    #         reg = getattr(q, registry+"_job_registry")
    #         job_ids = reg.get_job_ids()
    #         if job_ids:
    #             for job_id in job_ids:
    #                 if job_id.startswith(current_app.config['RQ_JOB_PREFIX']):
    #                     job = Job.fetch(job_id, worker.conn)
    #                     job_meta=job.get_meta(refresh=True)
    #                     all_jobs.append(JobWrapper(job, None, job_meta['file_size']))
    #     enqueued_jobs = q.get_jobs()
    #     for enq_job in enqueued_jobs:
    #         job_meta=enq_job.get_meta(refresh=True)
    #         all_jobs.append(JobWrapper(enq_job, None, job_meta['file_size']))
    jobs_dir = os.path.join(current_dir, current_app.config['TNC_JOB_DIR'])
    if not os.path.exists(jobs_dir):
        os.makedirs(jobs_dir)
    all_jobs = get_jobs_from_dir(jobs_dir)
    total_query = len(all_jobs)
    total_filtered = total_query

    # search filter
    search = request.args.get("search[value]")
    filtered_obj = []
    if search:
        for single_job in all_jobs:
            if single_job.search(search):
                filtered_obj.append(single_job)
        all_jobs = filtered_obj
        total_filtered = len(filtered_obj)
    
    # sorting
    i = 0
    while True:
        col_index = request.args.get(f"order[{i}][column]")
        if col_index is None:
            break
        col_name = request.args.get(f"columns[{col_index}][data]")
        view_db = {
            "job_id": "jobId",
            "status": "status",
            "file_size": "fileSize",
            "enqueued_at": "sorted_enqueued_at",
            "started_at": "sorted_started_at",
            "ended_at": "sorted_ended_at",
        }
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        all_jobs.sort(key = operator.attrgetter(view_db[col_name]), reverse=descending)
        i += 1
    
    # # pagination
    start = request.args.get("start", type=int)
    if not start:
        start = 0
    length = request.args.get("length", type=int)
    if not length:
        length = total_query
    all_jobs = all_jobs[start:start+length]

    return {
        "data": [job.datatable() for job in all_jobs],
        "recordsFiltered": total_filtered,
        "recordsTotal": total_query,
        "draw": request.args.get("draw", type=int)
    }

@bp.route("/blast/error/<job_id>")
@login_required
def job_error(job_id):
    info = None
    error_output=""
    try:
        job = Job.fetch(job_id, worker.conn)
        info = job.exc_info
    except NoSuchJobError as exc:
        full_path = os.path.join(current_dir, current_app.config['TNC_JOB_DIR'], job_id, job_id+".error")
        if os.path.exists(full_path):
            with open(full_path) as reader:
                info = reader.readlines()
    if info:
        if not info.startswith("Work-horse terminated unexpectedly"):
            lines = info.split('\n')
            if len(lines)>=3:
                error_output = lines[-2]
            else:
                error_output = info
        else:
            # the error 'Work-horse terminated unexpectedly' is being thrown by
            # rq when trying to finish the OS process. That overrides the actual
            # risen job exception. So to avoid we save an metadata with the error
            # and show it as a result of this function
            if job:
                job_meta=job.get_meta(refresh=True)
                error_output = job_meta['stderr']
            else:
                error_output = "There was a problem trying to finish the job."
    return_json = {
            "text": error_output
        }
    return return_json

from flask_tn.utils import job_utils
from rq.exceptions import NoSuchJobError
from rq.command import send_stop_job_command
@bp.route("/blast/remove/<job_id>", methods=["DELETE"])
@login_required
def blast_remove(job_id):
    return_json = {"status": "ok"}
    try:
        job = Job.fetch(job_id, worker.conn)
        if job.is_started:
            send_stop_job_command(worker.conn, job_id)
        job.delete()
        # now delete the result on redis database:
        for key in worker.conn.scan_iter("rq:results:"+job_id):
            worker.conn.delete(key)
    except NoSuchJobError:
        full_path = os.path.join(current_dir, current_app.config['TNC_JOB_DIR'], job_id, job_id+".info")
        job = tnjob_from_info(job_id, full_path)
    except Exception as exc:
        return_json["status"]="error"
        return_json["error"]=str(exc)
    
    try:
        if return_json["status"]=="ok":
            job_folder = os.path.join(current_dir, current_app.config['TNC_JOB_DIR'], job_id)
            shutil.rmtree(job_folder)
    except Exception as exc:
        return_json["status"]="error"
        return_json["error"]=str(exc.message)
    
    return jsonify(return_json)


@bp.route("/info/repeat/<rep_id>", methods=["POST"])
def repeat_info(rep_id):
    rep_info = Te_Repeat.query.filter_by(repeat_id=rep_id).first()
    return jsonify(rep_info.as_info())


@bp.route("/info/orf/<orf_id>", methods=["POST"])
def orf_info(orf_id):
    orf_info = Te_Orf.query.filter_by(orf_id=orf_id).first()
    return jsonify(orf_info.as_info())


@bp.route("/info/res/<recomb_id>", methods=["POST"])
def res_info(recomb_id):
    res_info = Te_RecombSite.query.filter_by(recomb_id=recomb_id).first()
    return jsonify(res_info.as_info())


@bp.route("/save/repeat/", methods=["POST"])
@login_required
def save_repeat():
    rep_id = utils.get_request_value(request.form, "rep_id")
    rep_obj = Te_Repeat.query.filter_by(repeat_id=rep_id).first()
    accession = rep_obj.te_entry.accession
    te_name = rep_obj.te_entry.name

    library_name = utils.get_request_value(request.form, "library_name")
    rep_comment = utils.get_request_value(request.form, "rep_comment")

    utils.update_column_value(
        rep_obj, ["library_name", "comment"], [library_name, rep_comment]
    )

    # The following lines are working, but, for now, we've decided avoiding
    # giving the user the option to change the fragments position
    # list_start = request.form.getlist("frag_start")
    # list_end = request.form.getlist("frag_end")
    # list_strand = request.form.getlist("frag_strand")
    # fragments = rep_obj.fragments
    # fragments.delete()
    # for i in range(0,len(list_start)):
    #     f = Te_Repeat_Fragment()
    #     f.start=int(list_start[i])
    #     f.end=int(list_end[i])
    #     f.strand=list_strand[i]
    #     rep_obj.fragments.append(f)
    db.session.commit()

    # saving in the file
    upload_folder = get_upload_folder()
    gb_file = os.path.join(upload_folder, accession + ".gb")
    gb_obj = Genbank.get_genbank_object(gb_file)
    repeats = gb_obj.children_feature(Constants.FT_REPEAT_REGION)
    # TODO: feature_by_name and update_note should be functions from gb_obj object
    repeat = Genbank.feature_by_name(repeats, Constants.FT_REPEAT_REGION, rep_obj.name)
    Genbank.update_note(
        repeat,
        [Constants.NT_OTHER_INFORMATION, Constants.NT_LIBRARY_NAME],
        [rep_comment, library_name],
    )

    with open(gb_file, "w") as writer:
        writer.write(str(gb_obj))
    # log the change in log table
    save_change_log(Constants.UPLOAD_GENBANK, gb_file, "Repeat in genbank file updated.")

    return redirect(
        url_for("admin.edit_gb", type="u", accession=accession) + "#table_repeat"
    )


@bp.route("/save/orf/", methods=["POST"])
@login_required
def save_orf():
    orf_id = utils.get_request_value(request.form, "orf_id")
    orf_obj = Te_Orf.query.filter_by(orf_id=orf_id).first()
    accession = orf_obj.te_entry.accession

    columns = [
        "library_name",
        "orf_class",
        "subclass",
        "function",
        "sequence_family",
        "target",
        "chemistry",
        "comment",
    ]
    values = []
    for column in columns:
        values.append(utils.get_request_value(request.form, column))

    utils.update_column_value(orf_obj, columns, values)
    db.session.commit()

    # saving in the file
    upload_folder = get_upload_folder()
    gb_file = os.path.join(upload_folder, accession + ".gb")
    gb_obj = Genbank.get_genbank_object(gb_file)
    orfs = gb_obj.children_feature(Constants.FT_CDS)
    orf = Genbank.feature_by_name(orfs, Constants.FT_CDS, orf_obj.name)

    columns = [
        Constants.NT_LIBRARY_NAME,
        Constants.NT_CLASS,
        Constants.NT_SUBCLASS,
        Constants.NT_SEQUENCE_FAMILY,
        Constants.NT_TARGET,
        Constants.NT_CHEMISTRY,
        Constants.NT_OTHER_INFORMATION,
    ]
    function = values.pop(3)  # remove function because it's note inside the
    # qualifier note
    Genbank.update_note(orf, columns, values)
    # function is a qualifier
    function_qualifier = orf.get_qualifier(Constants.QL_FUNCTION)
    function = f'"{function}"'
    if function_qualifier == None:
        orf.create_qualifier(Constants.QL_PRODUCT, Constants.QL_FUNCTION, function)
    else:
        function_qualifier.value = function

    with open(gb_file, "w") as writer:
        writer.write(str(gb_obj))
    # log the change in log table
    save_change_log(Constants.UPLOAD_GENBANK, gb_file, "Orf in genbank file updated.")
    return redirect(
        url_for("admin.edit_gb", type="u", accession=accession) + "#table_orf"
    )


@bp.route("/save/res/", methods=["POST"])
@login_required
def save_res():
    recomb_id = utils.get_request_value(request.form, "recomb_id")
    res_obj = Te_RecombSite.query.filter_by(recomb_id=recomb_id).first()
    accession = res_obj.te_entry.accession
    te_name = res_obj.te_entry.name

    library_name = utils.get_request_value(request.form, "library_name")
    comment = utils.get_request_value(request.form, "comment")

    utils.update_column_value(
        res_obj, ["library_name", "comment"], [library_name, comment]
    )

    db.session.commit()

    # saving in the file
    upload_folder = get_upload_folder()
    gb_file = os.path.join(upload_folder, accession + ".gb")
    gb_obj = Genbank.get_genbank_object(gb_file)
    recombs = gb_obj.children_feature(Constants.FT_MISC_FEATURE)
    recomb = Genbank.feature_by_name(recombs, Constants.FT_MISC_FEATURE, res_obj.name)
    Genbank.update_note(
        recomb,
        [Constants.NT_LIBRARY_NAME, Constants.NT_OTHER_INFORMATION],
        [library_name, comment],
    )

    with open(gb_file, "w") as writer:
        writer.write(str(gb_obj))

    # log the change in log table
    save_change_log(Constants.UPLOAD_GENBANK, gb_file, "Recombination site in genbank file updated.")
    return redirect(
        url_for("admin.edit_gb", type="u", accession=accession) + "#table_recomb"
    )


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table,
    # use it in the query for the user
    return User.query.filter_by(user_id=user_id).first()

@bp.route("/check_qc/<accession>")
def check_qc(accession):
    location_folder = get_upload_folder()
    file = os.path.join(location_folder, accession + ".gb.out")
    return_status = {}
    if os.path.exists(file):
        return_status["status"]="ok"
    else:
        return_status["status"]="error"
        return_status["error"]="There is no report to download."
    
    return jsonify(return_status)

@bp.route("/qc_result/<db>/<accession>")
def download_qc(db, accession):
    if db == "u":
        location_folder = get_upload_folder()
    else: 
        location_folder = os.path.join(current_app.config['TNC_CURRENT_DIR'], current_app.config['TNC_GENBANK_DIR'])
    file = os.path.join(location_folder, accession + ".gb.out")

    return send_file(file, as_attachment=True)


@bp.route("/download/<db>/<accession>")
def direct_download(db, accession):
    ext = request.args.get("ext")
    location_folder = ""
    if db == "u":
        location_folder = get_upload_folder()
        file = os.path.join(location_folder, accession + "." + ext)
    elif db == "d":
        if ext == "fa":
            location_folder = os.path.join(
                current_dir, current_app.config["TNC_FASTA_DIR"]
            )
        elif ext == "gb":
            location_folder = os.path.join(
                current_dir, current_app.config["TNC_GENBANK_DIR"]
            )
        elif ext == "dna":
            location_folder = os.path.join(
                current_dir, current_app.config["TNC_SNAP_DIR"]
            )
        file = os.path.join(location_folder, accession + "." + ext)
    else:
        print("throw an exception")

    return send_file(file, as_attachment=True)


@bp.route("/check_download/<db>", methods=["POST"])
@login_required
def check_download(db):
    ext = request.args.get("ext")
    list_acc = request.args.getlist("accession")
    len_list = len(list_acc)
    return_status = {}
    if len_list == 0:
        return_status["status"] = "error"
        return_status["error"] = "Empty accession"
        return jsonify(return_status)
    
    location_folder = ""
    if db == "u":
        location_folder = get_upload_folder()
    elif db == "d":
        location_folder = os.path.join(
            current_dir, current_app.config["TNC_GENBANK_DIR"]
        )
        if ext == "fa":
            location_folder = os.path.join(
                current_dir, current_app.config["TNC_FASTA_DIR"]
            )
        elif ext == "dna":
            location_folder = os.path.join(
                current_dir, current_app.config["TNC_SNAP_DIR"]
            )
    else:
        return_status["status"] = "error"
        return_status["error"] = "DB type not found."
        return jsonify(return_status)

    valid_file = 0
    for accession in list_acc:
        filepath = os.path.join(location_folder, accession + "." + ext)
        if os.path.exists(filepath):
            valid_file += 1
    if valid_file > 0:
        return_status["status"] = "ok"
    else:
        return_status["status"] = "error"
        return_status["error"] = "There is no file to download."
    
    return jsonify(return_status)


@bp.route("/bulk/<db>")
def bulk_download(db):
    ext = request.args.get("ext")
    list_acc = request.args.getlist("accession")
    len_list = len(list_acc)

    if ext == "fa" or ext == "fasta":
        ext = "fa"

    if len_list == 0:
        return None

    location_folder = ""
    if db == "u":
        location_folder = get_upload_folder()
    elif db == "d":
        location_folder = os.path.join(
            current_dir, current_app.config["TNC_GENBANK_DIR"]
        )
        if ext == "fa":
            location_folder = os.path.join(
                current_dir, current_app.config["TNC_FASTA_DIR"]
            )
        elif ext == "dna":
            location_folder = os.path.join(
                current_dir, current_app.config["TNC_SNAP_DIR"]
            )
    else:
        print("throw an exception")

    filename = "bulk"
    if len_list < 4:
        filename = "_".join(list_acc)

    random_token = token_hex(3).upper()
    download_location = os.path.join(location_folder, "temp", random_token)
    os.makedirs(download_location)

    file = os.path.join(download_location, filename + "_" + ext + ".zip")

    with zipfile.ZipFile(file, mode="a") as archive:
        for accession in list_acc:
            file_ac = os.path.join(location_folder, accession + "." + ext)
            if os.path.exists(file_ac):
                archive.write(file_ac, accession + "." + ext)
    return send_file(file, as_attachment=True)

@bp.route("/save_reference", methods=["POST"])
@login_required
def save_reference():
    pmid = utils.get_request_value(request.form, "pmid")
    entry_id = utils.get_request_value(request.form, "entry_id")
    
    if pmid == "":
        return_obj = {'status': 'error',
                'error':'Empty pubmed id.'}
        return jsonify(return_obj)
    # first we save the file
    pubmed_folder = utils.join_and_create_folder(
        current_app.config["TNC_BASE_DIR"], current_app.config["TNC_PUBMED_DIR"]
    )
    pm_file = os.path.join(pubmed_folder, pmid)
    file_exists = True
    try:
    # get the size of file
        file_size = os.path.getsize(pm_file)
        # if file size is 0, it is empty
        if (file_size == 0):
            response = utils.download_pubmed_file(pmid)
            file_exists = utils.save_pubmed_file(response, pm_file)
    # if file does not exist, then exception occurs
    except FileNotFoundError as e:
        response = utils.download_pubmed_file(pmid)
        file_exists = utils.save_pubmed_file(response, pm_file)

    if file_exists:
        gb_obj = Te_Entry.query.filter_by(entry_id=entry_id).first()
        pub_obj = Te_Pubmed.query.filter_by(pubmed_id=int(pmid)).first()
        gb_obj.pubmeds.append(pub_obj)
        db.session.commit()
        # export new genbank
        upload_folder = get_upload_folder()
        gb_file = os.path.join(upload_folder, gb_obj.accession+".gb")
        gb_file_obj = Genbank.get_genbank_object(gb_file)
        gb_file_obj.sequence_as_text
        n_references = len(gb_file_obj.references)
        tnRef = gb_utils.pub_db_to_tn(pub_obj)
        tnRef.refNumber=n_references+1
        tnRef.seqStart=1
        tnRef.seqEnd=gb_file_obj.len_sequence()
        gb_file_obj.references.append(tnRef)

        with open(gb_file, "w") as writer:
            writer.write(str(gb_file_obj))

        # log the change in log table
        save_change_log(Constants.UPLOAD_GENBANK, gb_file, "Reference in genbank file updated.")

        return_obj = {'status': 'ok'}
    else:
        return_obj = {'status': 'error',
                'error':'Problem during downloading from NCBI.'}
    return jsonify(return_obj)

@bp.route("/delete_reference", methods=["DELETE"])
@login_required
def delete_reference():
    pmid = utils.get_request_value(request.form, "pmid")
    entry_id = utils.get_request_value(request.form, "entry_id")
    
    gb_obj = Te_Entry.query.filter_by(entry_id=entry_id).first()
    pub_obj = Te_Pubmed.query.filter_by(pubmed_id=int(pmid)).first()
    gb_obj.pubmeds.remove(pub_obj)
    db.session.commit()
    # deleting from file
    upload_folder = get_upload_folder()
    gb_file = os.path.join(upload_folder, gb_obj.accession+".gb")
    gb_file_obj = Genbank.get_genbank_object(gb_file)
    list_to_remove = []
    for idx,ref in enumerate(gb_file_obj.references):
        if pmid in ref.pubmed:
            list_to_remove.append(idx)
    
    n = 0
    for i in range(0,len(gb_file_obj.references)):
        if i in list_to_remove:
            del gb_file_obj.references[i-n]
            n = n+1
        else:
            gb_file_obj.references[i-n].refNumber = i-n+1
    
    with open(gb_file, "w") as writer:
        writer.write(str(gb_file_obj))

        # log the change in log table
        save_change_log(Constants.UPLOAD_GENBANK, gb_file, "Reference in genbank file deleted.")

    return_obj = {'status': 'ok'}
    return jsonify(return_obj)

@bp.route("/fetch_pubmed/", methods=["GET"])
@login_required
def fetch_pubmed_empty():
    return_obj = {'status': 'error',
                'error':'Empty pubmed id.'}
    return jsonify(return_obj)

@bp.route("/fetch_pubmed/<pmid>/", methods=["GET"])
@login_required
def fetch_pubmed(pmid):
    if pmid is None or pmid == "":
        return_obj['status']='error'
        return_obj['error']='Empty pubmed id.'
        return jsonify(return_obj)
    
    # first we save the file
    pubmed_folder = utils.join_and_create_folder(
        current_app.config["TNC_BASE_DIR"], current_app.config["TNC_PUBMED_DIR"]
    )
    pm_file = os.path.join(pubmed_folder, pmid)
    pubmed_obj = None
    file_exists = True
    try:
    # get the size of file
        file_size = os.path.getsize(pm_file)
        # if file size is 0, it is empty
        if (file_size == 0):
            response = utils.download_pubmed_file(pmid)
            file_exists = utils.save_pubmed_file(response, pm_file)
    # if file does not exist, then exception occurs
    except FileNotFoundError as e:
        response = utils.download_pubmed_file(pmid)
        file_exists = utils.save_pubmed_file(response, pm_file)

    return_obj = {'status':'ok'}
    if file_exists:
        pubmed_obj = Te_Pubmed.query.filter_by(pubmed_id=pmid).first()
        if not pubmed_obj:
            pubmed_dict = gb_utils.get_pubmed_from_file(pm_file)
            pubmed_obj = Te_Pubmed()
            pubmed_obj.pubmed_id=pmid
            pubmed_obj.title = pubmed_dict["title"]
            pubmed_obj.authors = pubmed_dict["authors"]
            pubmed_obj.summary = pubmed_dict["summary"]
            db.session.add(pubmed_obj)
            db.session.commit()
        return_obj['pub_title']=pubmed_obj.title
        return_obj['pub_authors']=pubmed_obj.authors
        return_obj['pub_summary']=pubmed_obj.summary
    else:
        return_obj['status']='error'
        return_obj['error']='Invalid pubmed id.'

    return jsonify(return_obj)

def save_change_log(category, filename, action):
    change_log = ChangeLog()
    change_log.user_id = current_user.get_id()
    category_obj = UploadCategory.query.filter_by(category_name=category).first()
    change_log.time_changed = datetime.datetime.now(tz=datetime.timezone.utc)
    change_log.category_id = category_obj.category_id
    change_log.filename=filename
    change_log.action = action
    db.session.add(change_log)
    db.session.commit()

@bp.route("/upload_custom", methods=["POST"])
@login_required
def upload_custom():
    custom_file = request.files["custom_file"]
    return_status = {}
    filename = secure_filename(custom_file.filename)
    # TODO: check if name of the image is the same of the genbank

    accepted_extension = (".zip",".ftrs")
    if not filename.lower().endswith(accepted_extension):
        return_status["status"]="error"
        return_status["error"]="Incorrect extension. Only '.zip' and '.ftrs' allowed."
    else:
        try:
            custom_folder = os.path.join(current_app.config["TNC_BASE_DIR"],
                        current_app.config['TNC_SNAPGENE_BASE_LIBRARY'],'upload')
            extension = filename.split(".")[-1]

            config_custom = current_app.config["TNC_SNAPGENE_CUSTOM"]
            config_dna = current_app.config["TNC_SNAPGENE_COMMON_DNA"]

            date_today = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%m_%d_%Y")
            
            new_unpacked = f"{config_custom}_{date_today}.ftrs"
            new_dna_unpacked = f"{config_dna}_{date_today}.dna"

            full_unpacked = os.path.join(custom_folder, new_unpacked)
            full_dna_unpacked = os.path.join(custom_folder, new_dna_unpacked)

            if extension == "zip":
                full_zipped = os.path.join(custom_folder, new_unpacked+".zip")
                custom_file.save(full_zipped)
                zip = zipfile.ZipFile(full_zipped)
                infolist = zip.infolist()
                n_files = 0
                file_inside = ""
                for info in infolist:
                    if not info.is_dir():
                        zip.extract(info.filename, custom_folder)
                        n_files += 1
                        file_inside = os.path.join(custom_folder, 
                                                   info.filename.split('/')[-1])
                if n_files == 1:
                    os.rename(file_inside, full_unpacked)
                    os.remove(full_zipped)
                else:
                    pass
            else:
                custom_file.save(full_unpacked)
            shutil.copy2(full_unpacked, full_dna_unpacked)
            
            # log the change in log table
            save_change_log(Constants.UPLOAD_CUSTOM, full_unpacked,
                            "Custom Commom Features file uploaded.")
            return_status["status"] = "ok"
            return_status["name"] = custom_file.filename
        except Exception as exc:
            print("-----------Exception")
            print(exc)
            return_status["status"] = "error"
            return_status["error"] = "Server error. Please report us the error."
    
    return jsonify(return_status)

@bp.route("/upload_favorites", methods=["POST"])
@login_required
def upload_favorites():
    favorites_file = request.files["favorites_file"]
    return_status = {}
    filename = secure_filename(favorites_file.filename)
    # TODO: check if name of the image is the same of the genbank

    accepted_extension = ".zip"
    if not filename.lower().endswith(accepted_extension):
        return_status["status"]="error"
        return_status["error"]="Incorrect extension. Only '.zip' and '.ftrs' allowed."
    else:
        try:
            custom_folder = os.path.join(current_app.config["TNC_BASE_DIR"],
                        current_app.config['TNC_SNAPGENE_BASE_LIBRARY'],'upload')
            config_favorites = current_app.config["TNC_SNAPGENE_FAVORITES"]

            date_today = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%m_%d_%Y")
            new_filename = f"{config_favorites}_{date_today}.zip"
            
            full_filename = os.path.join(custom_folder, new_filename)
            favorites_file.save(full_filename)
            
            # log the change in log table
            save_change_log(Constants.UPLOAD_FAVORITE, full_filename,
                            "Exported Favorites file uploaded.")
            return_status["status"] = "ok"
            return_status["name"] = new_filename
        except Exception as exc:
            print("-----------Exception")
            print(exc)
            return_status["status"] = "error"
            return_status["error"] = "Server error. Please report us the error."
    
    return jsonify(return_status)

@bp.route("/log_data/")
@login_required
def change_log_data():
    """
    
    """
    query = ChangeLog.query

    total_query = query.count()
    # It's not possible to work with the size of the
    # request.args because this variable is manipulated
    # by datatable.js and they send a lot of values for
    # their own control. Since we are sending our values together
    # with the table variables we have to check one by one if the value exists
    total_filtered = total_query

    # search filter
    search = request.args.get("search[value]")
    if search:
        query = query.join(User).join(UploadCategory).filter(
            db.or_(
                ChangeLog.time_changed.like(f"%{search}%"),
                ChangeLog.filename.like(f"%{search}%"),
                ChangeLog.action.like(f"%{search}%"),
                User.username.like(f"%{search}%"),
                UploadCategory.category_name.like(f"%{search}%")
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
        view_db = {
            "select": "log_id",
            "filename": "filename",
            "time_changed": "time_changed",
            "action": "action",
            "username": "user",
            "category": "category"
        }
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        if col_name == "user":
            col = getattr(User, "username")
        elif col_name == "category":
            col = getattr(UploadCategory, "category_name")
        else:
            col = getattr(ChangeLog, view_db[col_name])
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        query = query.join(UploadCategory).join(User).order_by(*order)

    # # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    query = query.offset(start).limit(length)

    return {
        "data": [log.datatable() for log in query],
        "recordsFiltered": total_filtered,
        "recordsTotal": total_query,
        "draw": request.args.get("draw", type=int),
    }