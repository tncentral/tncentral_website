#!venv/bin/python

"""
    Before running this script you need to load the virtual environment by
    using the command below inside the tncentral folder:
    $ cd /path/to/tncentral
    $ source venv/bin/activate
    This script can perform command line manipulation on TnCentral database.
    To see all commands available, just type on the terminal:
    $ python app.py

"""


import zipfile
from flask_tn import create_app
from flask_tn import db_models
from flask_tn.db_models import UploadCategory, User, UserGenbank
from flask_tn.ext.database import db
from flask_tn import utils
import shutil
import getpass
import sys
import os

from flask_tn.utils import Constants

app = create_app()

# current_directory must be empty
# python app.py create
# python app.py load
# python app.py pubmed
if __name__ == "__main__":
    user_args = sys.argv[1:]
    app.app_context().push()
    data_dir = app.config["TNC_DATA_DIR"]
    current_dir = os.path.join(data_dir, app.config["TNC_CURRENT_DIR"])
    
    if "drop_all" in user_args:
        keep_pubmed = "keep_pubmed" in user_args
        keep_user = "keep_user" in user_args
        upload_dir = os.path.join(data_dir, app.config["TNC_UPLOAD_FOLDER"])

        if keep_pubmed or keep_user:
            db_models.drop_all(keep_pubmed, keep_user)
        else:
            db_models.drop_all()
        if not keep_user:
            shutil.rmtree(upload_dir)
            os.makedirs(upload_dir)
            shutil.rmtree(current_dir)
            os.makedirs(current_dir)
        else:
            db_file = os.path.join(current_dir, app.config["TNC_DATABASE_NAME"])
            shutil.copy2(db_file, data_dir)
            shutil.rmtree(current_dir)
            os.makedirs(current_dir)
            db_file = os.path.join(data_dir, app.config["TNC_DATABASE_NAME"])
            shutil.move(db_file, current_dir)
    if "delete_files" in user_args:
        pass
    if "clear_user_data" in user_args:
        try:
            username = input("username [None=delete all]: ")
        except Exception as error:
            print("ERROR", error)
        else:
            upload_dir = os.path.join(data_dir, app.config["TNC_UPLOAD_FOLDER"])

            if username == "":
                user_gb = UserGenbank.query.all()
                subfolders = [f.path for f in os.scandir(upload_dir) if f.is_dir()]
            else:
                user_gb = (
                    UserGenbank.query.join(User).filter_by(username=username).all()
                )
                if user_gb != None:
                    upload_dir = os.path.join(upload_dir, username)
                    subfolders = [upload_dir]
                else:
                    subfolders = []  # TODO raise an exception
            for gb in user_gb:
                db.session.delete(gb)
            db.session.commit()

            for subfolder in subfolders:
                shutil.rmtree(subfolder)
                os.makedirs(subfolder)
    if "create_db" in user_args:
        if not os.path.exists(current_dir):
            os.makedirs(current_dir)
        db.create_all()
        for category in Constants.UPLOAD_CATEGORIES:
            upload_category = UploadCategory(category)
            db.session.add(upload_category)
        db.session.commit()
    if "unpack_files" in user_args:
        base_dir = os.path.join(data_dir, app.config["TNC_BASE_DIR"])
        
        # 1. Unpacking zip images from base dir to current dir
        images_zip = os.path.join(base_dir, app.config["TNC_IMG_ARCHIVE"])
        shutil.unpack_archive(images_zip, current_dir, "zip")

        # 2. Unpacking genbank files from base dir to current dir
        gb_zip = os.path.join(base_dir, app.config["TNC_GB_ARCHIVE"])
        shutil.unpack_archive(gb_zip, current_dir, "zip")

        # 3. Unpacking the snapgene files
        snap_zip = os.path.join(base_dir, app.config["TNC_SNAP_ARCHIVE"])
        shutil.unpack_archive(snap_zip, current_dir, "zip")

        # 4. Unpacking the external files
        external_zip = os.path.join(base_dir, app.config["TNC_EXTERNAL_ARCHIVE"])
        shutil.unpack_archive(external_zip, current_dir, "zip")
        
        # 4. Create the folder to hold fasta files. The fasta sequences
        # will be extracted from the genbank files
        fasta_dir = os.path.join(current_dir, app.config["TNC_FASTA_DIR"])
        utils.create_directory(fasta_dir)   

        # 5. Creating the formatted sequences folder. We extract the sequences
        # and format them as they are showed in the report page. We prefer to do
        # this beforehand just for a matter of performance
        fmt_fasta_dir = os.path.join(current_dir, app.config["TNC_FASTA_FMT_DIR"])
        utils.create_directory(fmt_fasta_dir)

        # fasta_name = app.config["TNC_FASTA_FILE"]
        # 6. Export both fasta and format file format files:
        gb_dir = os.path.join(current_dir, app.config["TNC_GENBANK_DIR"])
        utils.gb_utils.export_fasta(gb_dir, fasta_dir, fmt_fasta_dir, current_dir)
        
        # create a zip file containing all fasta files exported from the genbanks
        utils.gb_utils.create_zip(current_dir, fasta_dir, "tncentral.fa.zip")

        # copy the base gb.zip to a file called tncentral.gb.zip
        shutil.copyfile(gb_zip, os.path.join(current_dir, "tncentral.gb.zip"))
        # utils.gb_utils.create_zip(current_dir, gb_dir, "tncentral.gb.zip")

        snap_dir = os.path.join(current_dir, app.config["TNC_SNAP_DIR"])
        shutil.copyfile(snap_zip, os.path.join(current_dir, "tncentral.dna.zip"))

        temp_dir = os.path.join(current_dir, app.config["TNC_TEMP_DIR"])
        utils.create_directory(temp_dir)

        base_pubmed = os.path.join(base_dir, app.config["TNC_PUBMED_DIR"])
        src_pubmed = os.path.join(current_dir, app.config["TNC_PUBMED_DIR"])
        utils.gb_utils.create_symlink(base_pubmed, src_pubmed, is_dir=True)

        # creating external files to download
        # copy snapgene custonFeatures:
        base_snap_lib = os.path.join(base_dir, app.config["TNC_SNAPGENE_BASE_LIBRARY"])
        custom_features = os.path.join(base_snap_lib, app.config["TNC_SNAPGENE_CUSTOM"])
        snapgene_favorites = os.path.join(base_snap_lib, app.config["TNC_SNAPGENE_FAVORITES"])
        # shutil.copyfile(custom_features, os.path.join(current_dir, app.config["TNC_SNAPGENE_CUSTOM"]))
        os.symlink(custom_features, os.path.join(current_dir, app.config["TNC_SNAPGENE_CUSTOM"]))
        os.symlink(snapgene_favorites, os.path.join(current_dir, app.config["TNC_SNAPGENE_FAVORITES"]))
        # shutil.copyfile(snapgene_favorites, os.path.join(current_dir, app.config["TNC_SNAPGENE_FAVORITES"]))

        # create zip to integrall
        integrall_dir = os.path.join(
            current_dir, app.config["TNC_RESOURCES_DIR"], app.config["INTEGRALL_FOLDER"]
        )
        integrall_zip = os.path.join(integrall_dir, app.config["INTEGRALL_ZIP"])
        list_files = app.config["INTEGRALL_FILES"]
        with zipfile.ZipFile(integrall_zip, 'w') as f_out:
            for file in list_files:
                full_file = os.path.join(integrall_dir, file)
                f_out.write(
                    full_file, 
                    os.path.join(app.config['INTEGRALL_FOLDER'],file)
                )
                if os.path.isdir(full_file):
                    for f in os.listdir(full_file):
                        new_file = os.path.join(full_file, f)
                        f_out.write(
                            new_file, 
                            os.path.join(app.config['INTEGRALL_FOLDER'],file, f)
                        )

    if "load_db" in user_args:
        gb_dir = os.path.join(current_dir, app.config["TNC_GENBANK_DIR"])
        utils.gb_utils.load_db_new(gb_dir)

        csv_dir = app.config["TNC_CSV_DIR"]
        csv_name = app.config["TNC_CSV_FILE"]        
        utils.gb_utils.create_csv_file(current_dir, csv_dir, csv_name)
    if "load_external" in user_args:
        external_resources = app.config["LOAD_EXTERNAL"]
        for idx,resource in enumerate(external_resources):
            resources_dir = os.path.join(current_dir, app.config["TNC_RESOURCES_DIR"])
            resources_dir = os.path.join(resources_dir, resource)
            id_file = os.path.join(resources_dir, app.config["EXTERNAL_IDS"][idx])
            utils.gb_utils.load_external(resource, id_file)
    if "load_categories" in user_args:
        for category in Constants.UPLOAD_CATEGORIES:
            upload_category = UploadCategory(category)
            db.session.add(upload_category)
        db.session.commit()
    if "create_blast" in user_args:
        from flask_tn.utils import job_utils
        job_utils.recreate_blast()
    if "create_admin" in user_args:
        try:
            username = input("Username: ")
            p = getpass.getpass(prompt="Password: ")
            p1 = getpass.getpass(prompt="Type the password again: ")
        except Exception as error:
            print("ERROR", error)
        else:
            user_query = User.query.filter_by(username=username).first()
            if user_query:
                print(user_query.get_id())
                print(f"[ERROR] User '{username}' already exists.")
            else:
                if p == p1:
                    user = User(username, p)
                    db.session.add(user)
                    db.session.commit()
                    upload_dir = app.config["TNC_UPLOAD_FOLDER"]
                    user_dir = os.path.join(data_dir, upload_dir, username)
                    if os.path.exists(user_dir):
                        shutil.rmtree(user_dir)
                        os.makedirs(user_dir)
                    else:
                        os.makedirs(user_dir)
                    print(f"User '{username}' successfully created.")
                else:
                    print("[ERROR] Password doesn't match.")
    if "update_admin" in user_args:
        try:
            username = input("Username: ")
            p = getpass.getpass(prompt="Password: ")
            p1 = getpass.getpass(prompt="Type the password again: ")
        except Exception as error:
            print("ERROR", error)
        else:
            user_query = User.query.filter_by(username=username).first()
            if user_query:
                if p == p1:
                    user_query.set_password(p)
                    db.session.commit()
                else:
                    print("[ERROR] Password doesn't match.")
                
            else:
                print(f"[ERROR] User '{username}' doesn't exist.")
    if "pubmed" in user_args:
        from flask_tn.utils import job_utils
        job_utils.export_pubmed_files()
    if "clean_jobs" in user_args:
        from flask_tn.utils import job_utils
        cron_days = app.config['RQ_CRON_DAYS']
        dir_jobs = os.path.join(current_dir, app.config['TNC_JOB_DIR'])
        job_utils.clean_jobs(dir_jobs, cron_days)
    if "clean_temp" in user_args:
        dir_temp = os.path.join(current_dir, app.config['TNC_TEMP_DIR'])
        shutil.rmtree(dir_temp)
        os.makedirs(dir_temp)
    if "snapshot" in user_args:
        snapshot_dir = os.path.join(data_dir, app.config["TNC_SNAPSHOT_DIR"])
        if not os.path.exists(snapshot_dir):
            os.makedirs(snapshot_dir)

        gb_dir = os.path.join(current_dir, app.config['TNC_GENBANK_DIR'])
        gb_zip = os.path.join(snapshot_dir, app.config['TNC_GB_ARCHIVE'])
        with zipfile.ZipFile(gb_zip, 'w') as f_out:
            for gb in os.listdir(gb_dir):
                if gb.endswith(".gb"):
                    gb_file = os.path.join(gb_dir, gb)
                    f_out.write(
                        gb_file, 
                        os.path.join(app.config['TNC_GENBANK_DIR'],gb)
                    )

        dna_dir = os.path.join(current_dir, app.config['TNC_SNAP_DIR'])
        dna_zip = os.path.join(snapshot_dir, app.config['TNC_SNAP_ARCHIVE'])
        with zipfile.ZipFile(dna_zip, 'w') as f_out:
            for dna in os.listdir(dna_dir):
                if dna.endswith(".dna"):
                    dna_file = os.path.join(dna_dir, dna)
                    f_out.write(
                        dna_file,
                        os.path.join(app.config['TNC_SNAP_DIR'],dna)
                    )

        img_dir = os.path.join(current_dir, app.config['TNC_IMAGE_DIR'])
        img_zip = os.path.join(snapshot_dir, app.config['TNC_IMG_ARCHIVE'])
        with zipfile.ZipFile(img_zip, 'w') as f_out:
            for img in os.listdir(img_dir):
                if img.endswith(".png"):
                    img_file = os.path.join(img_dir, img)
                    f_out.write(
                        img_file,
                        os.path.join(app.config['TNC_IMAGE_DIR'],img)
                    )
    if "archive_fa" in user_args:
        archive_file = os.path.join(current_dir, "tncentral.fa.zip")
        if os.path.exists(archive_file):
            os.remove(archive_file)
        fasta_dir = os.path.join(current_dir, app.config["TNC_FASTA_DIR"])
        # create a zip file containing all fasta files exported from the genbanks
        utils.gb_utils.create_zip(current_dir, fasta_dir, "tncentral.fa.zip")
    if "archive_gb" in user_args:
        archive_file = os.path.join(current_dir, "tncentral.gb.zip")
        if os.path.exists(archive_file):
            os.remove(archive_file)

        gb_dir = os.path.join(current_dir, app.config["TNC_GENBANK_DIR"])
        # create a zip file containing all unpacked genbanks
        utils.gb_utils.create_zip(current_dir, gb_dir, "tncentral.gb.zip", "gb", "gb")
    if "archive_dna" in user_args:
        archive_file = os.path.join(current_dir, "tncentral.dna.zip")
        if os.path.exists(archive_file):
            os.remove(archive_file)
        snap_dir = os.path.join(current_dir, app.config["TNC_SNAP_DIR"])
        # create a zip file containing all unpacked genbanks
        utils.gb_utils.create_zip(current_dir, snap_dir, "tncentral.dna.zip", "snapgene", "dna")

    port = app.config["TNC_APP_PORT"]
    host = app.config["TNC_APP_HOST"]
    if len(user_args) == 1 and "run" in user_args:
        if host != "127.0.0.1":
            app.run(port=port, host=host, debug=True)
        else:
            app.run(port=port, debug=True)
    elif len(user_args) == 1 and "run_https" in user_args:
        certificate_file = app.config["CERT_FILE"]
        key_file = app.config["PRIV_KEY"]
        app.run(port=port, debug=True, ssl_context=(certificate_file, key_file))
    elif len(user_args) == 0:
        print("Usage: python3 app.py [command]")
        print("  [command] can be one of the following:")
        print("    run: run the current flask app using http protocol.")
        print("    run_https: run the current flask app using https protocol.")
        print("    drop_all: erase the current database.")
        print("    create_db: create the entire current database structure.")
        print("    unpack_files: before loading the database this command will unpack.")
        print("                  the files to load them into the database.")
        print("    load_db: load the entire database from the unpacked files.")
        print("    load_external: load the external resources into external table.")
        print("    create_blast: create the files for blast. This can only be done")
        print("                  after loading the database.")
        print("    clear_user_data: Delete all genbanks uploaded by the users.")
        print("    pubmed: Due perfomance issues, we download and load the pubmed ")
        print("            information using this command.")
        print("    create_admin: create admin user.")
        print("    update_admin: update admin user password.")
        print("    clean_jobs: Remove jobs older than RQ_CRON_DAYS (defined in settings.toml).")
        print("    pack_files: generate the necessary files to load the database.")