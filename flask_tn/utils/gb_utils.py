import os
import re
from subprocess import PIPE, run
import requests
import time
import math
import zipfile
import os

from flask_tn.db_models import (
    db, Te_Entry, Te_Fragment, Te_Repeat, Te_Repeat_Fragment,
    Te_Orf, Te_Orf_Fragment, Te_RecombSite, Te_Recomb_Fragment,
    Entry_Orf_Summary, Orf_Summary, Te_Pubmed, External_Resource
)
from flask_tn import utils
from flask_tn.utils.Genbank import TnReference, get_genbank_object, Constants


def sort_internals(main_entry, internals, field_name):
    """
    Given an entry (transposon, integron or insertion sequence) and a list
    of internals elements (repeats, orfs and recombination sites), we sort
    the list based on the start coordinate of the sequence.
    """
    local_internals = []
    if main_entry:
        results = main_entry.get_value(field_name).all()
        if results != []:
            local_internals = main_entry.get_value(field_name).all()

    for te_int in internals:
        results = te_int.get_value(field_name).all()
        if results != []:
            local_internals.extend(results)
    if len(local_internals) > 0:
        local_internals.sort(key=lambda x: x.fragments[0].start)

    return local_internals


def iterate_fragments(value):
    list_fragments = []
    match = re.search("^join\((\d+\.\.\d+(,\d+\.\.\d+)*)\)$", value)
    if match != None:
        values = match.group(1)
        parts = values.split(",")
        for part in parts:
            match = re.search("^(\d+)\.\.(\d+)$", part)
            if match != None:
                fragment = {
                    "start": int(match.group(1)),
                    "end": int(match.group(2)),
                    "strand": "+",
                }
                list_fragments.append(fragment)
            else:
                print("ERROOOOEROEOEROROEOREOR")
    else:
        match = re.search("^complement\(join\((\d+\.\.\d+(,\d+\.\.\d+)*)\)\)$", value)
        if match != None:
            values = match.group(1)
            parts = values.split(",")
            for part in parts:
                match = re.search("^(\d+)\.\.(\d+)$", part)
                if match != None:
                    fragment = {
                        "start": int(match.group(1)),
                        "end": int(match.group(2)),
                        "strand": "-",
                    }
                    list_fragments.append(fragment)
                else:
                    print("COMPLEMENT ERROROEOROEOR")
    return list_fragments


def get_start_end(value):
    value = value.replace(" ", "")
    list_fragments = []
    # complement(8781..8818)
    match = re.search("^complement\((\d+)\.\.(\d+)\)$", value)
    if match != None:
        fragment = {
            "start": int(match.group(1)),
            "end": int(match.group(2)),
            "strand": "-",
        }
        list_fragments.append(fragment)
    else:
        match = re.search("^(\d+)\.\.(\d+)$", value)
        if match != None:
            fragment = {
                "start": int(match.group(1)),
                "end": int(match.group(2)),
                "strand": "+",
            }
            list_fragments.append(fragment)
        else:
            list_fragments = iterate_fragments(value)

    return list_fragments


def create_symlink(src, dest, is_dir=False):
    if is_dir:
        if dest.endswith("/"):
            dest = dest.rstrip("/")
    if not os.path.exists(dest):
        os.symlink(src, dest)


def get_dict_from_genbank(gb_block):
    gb_block = gb_block.copy()
    line = gb_block.pop(0)
    before_feature = ""
    list_dict_gb = []
    pubmed_list = []
    internal_dict = {}
    last_key = ""

    while not line.startswith("FEATURES"):
        match = re.search("^\s*PUBMED\s+(\d+)\s*$", line)
        if match != None:
            pubmed_id = match.group(1)
            if not pubmed_id in pubmed_list:
                pubmed_list.append(pubmed_id)
            # pubmed_dict = export_pubmed_file(pubmed_id, pubmed_dir)
        before_feature = before_feature + line
        line = gb_block.pop(0)

    # reading all features
    feature = ""  # variable to store the type of feature
    first_mobile = False
    line = gb_block.pop(0)
    accession = ""
    while not line.startswith("ORIGIN"):
        match = re.search("^\s{5}(\S+)\s+(.+)$", line)
        if match != None:
            # if internal dict is not empty, we have data from the last feature
            # as a dictionary
            if internal_dict:
                if "note" in internal_dict[feature]:
                    internal_dict[feature]["note"] = utils.get_dict_from_note(
                        internal_dict[feature]["note"]
                    )
                    if feature == "mobile_element":
                        internal_dict[feature][
                            "mobile_element_type"
                        ] = utils.get_dict_from_type(
                            internal_dict[feature]["mobile_element_type"]
                        )
                        if not first_mobile:
                            first_mobile = True
                            if "Accession" in internal_dict[feature]["note"]:
                                accession = internal_dict[feature]["note"]["Accession"]
                            else:
                                accession = internal_dict[feature][
                                    "mobile_element_type"
                                ]["name"]
                                internal_dict[feature]["note"]["Accession"] = accession
                    list_dict_gb.append(internal_dict)
                    internal_dict = {}
                else:
                    internal_dict = {}
            feature = match.group(1)
            value = match.group(2)
            list_fragments = get_start_end(value)
            internal_dict[feature] = {"fragments": list_fragments}
        else:
            line = line.strip()
            match = re.search("^\/(\w+)=(.+)$", line)
            if match != None:
                last_key = match.group(1)
                value = match.group(2)
                internal_dict[feature][last_key] = value.strip('"')
            else:
                match = re.search("^\/(\w+)$", line)
                match2 = re.search("^[xX]+$", line)
                if match != None or match2 != None:  # tag without value
                    pass
                else:
                    value = internal_dict[feature][last_key] + " " + line.strip('"')
                    internal_dict[feature][last_key] = value
        line = gb_block.pop(0)

    if "note" in internal_dict[feature]:
        internal_dict[feature]["note"] = utils.get_dict_from_note(
            internal_dict[feature]["note"]
        )
        if feature == "mobile_element":
            internal_dict[feature]["mobile_element_type"] = utils.get_dict_from_type(
                internal_dict[feature]["mobile_element_type"]
            )
            if "Accession" in internal_dict[feature]["note"]:
                accession = internal_dict[feature]["note"]["Accession"]
            else:
                accession = internal_dict[feature]["mobile_element_type"]["name"]
                internal_dict[feature]["note"]["Accession"] = accession

    list_dict_gb.append(internal_dict)
    # reading sequence
    fasta_sequence = ""
    line = gb_block.pop(0).lstrip()
    while not line.startswith("//"):
        line = re.sub("[0-9\s]+", "", line).strip()
        fasta_sequence += line.upper()
        line = gb_block.pop(0)

    list_dict_gb.append(
        {"accession": accession, "pubmed": pubmed_list, "sequence": fasta_sequence}
    )

    return list_dict_gb


def get_lines(path):
    lines = ""
    with open(path) as handle:
        lines = handle.readlines()
    return lines


def export_genbank_file(list_lines, accession, gb_dir):
    gb_file = os.path.join(gb_dir, accession + ".gb")
    with open(gb_file, "w") as writer:
        writer.writelines(list_lines)


def export_csv_file(line, csv_dir, accession):
    csv_file = os.path.join(csv_dir, accession + ".csv")
    with open(csv_file, "w") as writer:
        writer.write(line + "\n")


def export_fasta_file(sequence_lines, accession, fasta_dir):
    fasta_file = os.path.join(fasta_dir, accession + ".fa")
    with open(fasta_file, "w") as writer:
        writer.write(f">{accession}\n")
        writer.write(f"{sequence_lines}\n")


def get_sequence_from_file(fasta_file):
    sequence = ""
    with open(fasta_file, "r") as reader:
        line = reader.readline()
        if not line.startswith(">"):
            return None
        else:
            line = reader.readline()
            while line:
                line = line.strip()
                sequence += line
                line = reader.readline()
            return sequence


def export_fmt_fasta(sequence, accession, fasta_dir):
    length_seq = len(sequence)

    fasta_file = os.path.join(fasta_dir, accession + ".fmt")
    with open(fasta_file, "w") as writer:
        header_1 = "DNA Sequence"
        header_2 = "Length: " + str(length_seq)
        spaces = " " * (109 - len(header_1) - len(header_2))
        writer.write(f"{header_1}{spaces}{header_2}\n")
        writer.write("--------10 --------20 --------30 --------40 --------50 ")
        writer.write("--------60 --------70 --------80 --------90 -------100\n")

        col_len = 10
        # Now we split the sequence by col_len (defined above) chunks
        my_list = [sequence[i : i + col_len] for i in range(0, len(sequence), col_len)]

        # with the list of chunks we print 10 chunks per line
        lines = math.floor(length_seq / 100)  # here we know the number of lines with
        # 100 nucleotides full. The last line will
        # be printed after the loop.
        for i in range(0, lines):
            this_line = " ".join(my_list[i * 10 : i * 10 + 10])
            writer.write(f"{this_line} {(i+1)*100}\n")

        len_list = len(my_list)
        rest = len_list % 10
        if rest > 0:
            start = len_list - rest
            last_list = my_list[start:len_list]
            rest_seq = length_seq % 100
            this_line = " ".join(last_list)
            spaces = " " * (110 - (rest_seq + len(last_list) - 1))
            writer.write(f"{this_line}{spaces}{length_seq}\n")


# def export_pubmed_ids(accession, pubmed_list, global_dir):
#     file = os.path.join(global_dir, "pubmed.ids")
#     with open(file, "a") as writer:
#         writer.write(f"{accession}\t{','.join(pubmed_list)}\n")


def extract_met(text: str) -> (str, str):
    text = text.strip('"')
    (type, name) = text.split(":")
    return (type, name)


from flask_tn.utils.Genbank import TnGenbank, TnFeature, gb_int


def save_obj_to_db(genbank_obj: TnGenbank, in_production=0):
    main_entry = Te_Entry()
    main_entry.in_production = in_production
    main_feature: TnFeature = genbank_obj.get_main_feature()
    main_entry.accession = genbank_obj.accession
    main_entry.type = genbank_obj.tn_type
    main_entry.name = genbank_obj.name

    update_te_entry(main_entry, main_feature)
    repeats: TnFeature = genbank_obj.children_feature(Constants.FT_REPEAT_REGION)
    update_repeats(main_entry, repeats, genbank_obj)
    orfs: TnFeature = genbank_obj.children_feature(Constants.FT_CDS)
    update_orfs(main_entry, orfs)
    # recombination sites are in misc_feature
    res: TnFeature = genbank_obj.children_feature(Constants.FT_MISC_FEATURE)
    update_recombs(main_entry, res, genbank_obj)
    update_internals(main_entry, genbank_obj)
    update_pubmed(main_entry, genbank_obj)
    return main_entry

def update_pubmed(main_entry, genbank_obj):
    pubmed_ids = []
    for p in genbank_obj.references:
        if len(p.pubmed)>0:
            for pubmed in p.pubmed:
                if pubmed not in pubmed_ids:
                    pubmed_ids.append(pubmed)

    for pubmed_id in pubmed_ids:
        pub_obj = Te_Pubmed.query.filter_by(pubmed_id=int(pubmed_id)).first()
        if not pub_obj:
            pub_obj = Te_Pubmed()
            pub_obj.pubmed_id = int(pubmed_id)
            db.session.add(pub_obj)
        main_entry.pubmeds.append(pub_obj)

def update_internals(main_entry, genbank_obj):
    internal_mobiles: TnFeature = genbank_obj.children_feature(
        Constants.FT_MOBILE_ELEMENT
    )
    for internal_mobile in internal_mobiles:
        internal_entry = Te_Entry()
        internal_entry.in_production = main_entry.in_production
        internal_entry.accession = internal_mobile.dict_note[Constants.NT_ACCESSION]
        internal_entry.type = internal_mobile.tn_type
        internal_entry.name = internal_mobile.tn_name
        update_te_entry(internal_entry, internal_mobile)
        internal_entry.parents = main_entry
        # Begin New lines: Trying to save inner features with the internal entries
        repeats: TnFeature = genbank_obj.children_feature(Constants.FT_REPEAT_REGION,internal_mobile)
        update_repeats(internal_entry, repeats, genbank_obj)
        orfs: TnFeature = genbank_obj.children_feature(Constants.FT_CDS,internal_mobile)
        update_orfs(internal_entry, orfs)
        
        res: TnFeature = genbank_obj.children_feature(Constants.FT_MISC_FEATURE,internal_mobile)
        update_recombs(internal_entry, res, genbank_obj)
        # End New lines:

        db.session.add(internal_entry)


def update_recombs(entry: Te_Entry, recombs, genbank_obj):
    for recomb_site in recombs:
        te_res = Te_RecombSite()
        sequence = ""
        for f in recomb_site.fragments:
            fragment = Te_Recomb_Fragment()
            fragment.start = f.start
            fragment.end = f.end
            fragment.strand = f.strand
            new_sequence = genbank_obj.sequence_as_text()[
                fragment.start - 1 : fragment.end
            ]
            if fragment.strand == "-":
                new_sequence = utils.reverse_complement(new_sequence)
            sequence += new_sequence
            te_res.fragments.append(fragment)

        te_res.display_name = recomb_site.display_name
        te_res.name = recomb_site.dict_note[Constants.NT_NAME]
        te_res.associated_te = recomb_site.dict_note[Constants.NT_ASSOCIATED_ELEMENT]
        te_res.library_name = recomb_site.dict_note[Constants.NT_LIBRARY_NAME]
        te_res.comment = recomb_site.dict_note[Constants.NT_OTHER_INFORMATION]
        te_res.sequence = sequence
        entry.recombs.append(te_res)


def update_orfs(entry: Te_Entry, orfs):
    for orf in orfs:
        te_orf = Te_Orf()
        for f in orf.fragments:
            fragment = Te_Orf_Fragment()
            fragment.start = f.start
            fragment.end = f.end
            fragment.strand = f.strand
            te_orf.fragments.append(fragment)

        te_orf.display_name = orf.display_name
        te_orf.name = orf.get_qualifier(Constants.QL_GENE).value_to_str(strip=True)
        product = orf.get_qualifier(Constants.QL_PRODUCT)
        if product != None:
            te_orf.protein_name = orf.get_qualifier(Constants.QL_PRODUCT).value_to_str(
                strip=True
            )

        function = orf.get_qualifier(Constants.QL_FUNCTION)
        if function != None:
            te_orf.function = orf.get_qualifier(Constants.QL_FUNCTION).value_to_str(
                strip=True
            )

        te_orf.orf_class = orf.dict_note[Constants.NT_CLASS]
        te_orf.subclass = orf.dict_note[Constants.NT_SUBCLASS]

        te_orf.sequence_family = orf.dict_note[Constants.NT_SEQUENCE_FAMILY]
        te_orf.target = orf.dict_note[Constants.NT_TARGET]
        te_orf.chemistry = orf.dict_note[Constants.NT_CHEMISTRY]

        te_orf.genbank_id = entry.accession
        te_orf.associated_te = orf.dict_note[Constants.NT_ASSOCIATED_ELEMENT]
        te_orf.library_name = orf.dict_note[Constants.NT_LIBRARY_NAME]
        te_orf.comment = orf.dict_note[Constants.NT_OTHER_INFORMATION]
        te_orf.sequence = orf.get_qualifier(Constants.QL_TRANSLATION).value_to_str(
            strip=True
        )

        entry.orfs.append(te_orf)


def update_repeats(entry: Te_Entry, repeats, genbank_obj):
    for repeat in repeats:
        te_repeat = Te_Repeat()
        # note_qualifier:Qualifier = repeat.get_qualifier(Constants.QL_NOTE)
        # (note_dict,error) = dict_from_note(repeat.name, note_qualifier.fmt_to_value())
        # print("depois do dict_note e antes do repeat.fragments")
        sequence = ""
        for f in repeat.fragments:
            fragment = Te_Repeat_Fragment()
            fragment.start = f.start
            fragment.end = f.end
            fragment.strand = f.strand
            new_sequence = genbank_obj.sequence_as_text()[
                fragment.start - 1 : fragment.end
            ]
            if fragment.strand == "-":
                new_sequence = utils.reverse_complement(new_sequence)
            sequence += new_sequence
            te_repeat.fragments.append(fragment)

        te_repeat.display_name = repeat.display_name
        te_repeat.name = repeat.dict_note[Constants.NT_NAME]
        te_repeat.associated_te = repeat.dict_note[Constants.NT_ASSOCIATED_ELEMENT]
        te_repeat.library_name = repeat.dict_note[Constants.NT_LIBRARY_NAME]
        te_repeat.comment = repeat.dict_note[Constants.NT_OTHER_INFORMATION]
        te_repeat.sequence = sequence
        entry.repeats.append(te_repeat)


def update_te_entry(entry: Te_Entry, main_feature: TnFeature):
    for f in main_feature.fragments:
        te_fragment = Te_Fragment()
        te_fragment.start = f.start
        te_fragment.end = f.end
        te_fragment.strand = f.strand
        entry.fragments.append(te_fragment)

    entry.partial = valid_dict_value(main_feature.dict_note, Constants.NT_PARTIAL, True)
    entry.transposition = valid_dict_value(
        main_feature.dict_note, Constants.NT_TRANSPOSITION, True
    )
    entry.first_isolate = valid_dict_value(
        main_feature.dict_note, Constants.HT_FIRST, True
    )

    entry.capture = valid_dict_value(main_feature.dict_note, Constants.HT_FIRST, True)

    entry.family = valid_dict_value(main_feature.dict_note, Constants.NT_FAMILY)
    entry.group = valid_dict_value(main_feature.dict_note, Constants.NT_GROUP)
    entry.synonyms = valid_dict_value(main_feature.dict_note, Constants.NT_SYNONYMS)
    entry.comment = valid_dict_value(
        main_feature.dict_note, Constants.NT_OTHER_INFORMATION
    )
    entry.organism = valid_dict_value(
        main_feature.dict_note, Constants.NT_HOST_ORGANISM
    )
    entry.taxonomy = valid_dict_value(main_feature.dict_note, Constants.HT_TAXONOMY)
    entry.bacteria_group = valid_dict_value(
        main_feature.dict_note, Constants.HT_BAC_GROUP
    )
    entry.molecular_source = valid_dict_value(
        main_feature.dict_note, Constants.HT_MOLECULAR_SOURCE
    )
    entry.region = valid_dict_value(main_feature.dict_note, Constants.HT_REGION)
    entry.country = valid_dict_value(main_feature.dict_note, Constants.HT_COUNTRY)
    entry.other_loc = valid_dict_value(
        main_feature.dict_note, Constants.HT_OTHER_LOC_INFO
    )
    entry.date = valid_dict_value(main_feature.dict_note, Constants.HT_DATE_IDENTIFIED)


def valid_dict_value(dict_note, dict_key, is_int=False):
    value_return = None
    if dict_key in dict_note:
        if is_int:
            value_return = gb_int(dict_note[dict_key])
        else:
            value_return = dict_note[dict_key]
            if value_return == "None":
                value_return = None
    return value_return


def create_orf_summary():
    query = db.session.query(
        Te_Orf.name, Te_Orf.orf_class, Te_Orf.subclass, Te_Orf.target
    ).distinct()
    query = query.order_by(Te_Orf.name)

    for i in query:
        orf = Orf_Summary()
        orf.orf_name = i[0]
        orf.orf_class = i[1]
        orf.subclass = i[2]
        orf.target = i[3]
        subquery = Te_Entry.query.filter_by(entry_id_parent=None, in_production=1)
        subquery = subquery.join(
            Te_Orf, Te_Entry.entry_id == Te_Orf.entry_id
        ).add_columns(
            Te_Entry.entry_id,
            Te_Entry.accession,
            Te_Entry.name,
            Te_Entry.organism,
            Te_Entry.country,
        )
        subquery = subquery.filter(Te_Orf.name == i[0])
        dict_entries = {}
        for te in subquery:
            if not te.entry_id in dict_entries:
                dict_entries[te.entry_id] = 1
                entry_orf_summary = Entry_Orf_Summary()
                entry_orf_summary.entry_id = te.entry_id
                entry_orf_summary.accession = te.accession
                entry_orf_summary.name = te.name
                entry_orf_summary.organism = te.organism
                entry_orf_summary.country = te.country
                orf.entries.append(entry_orf_summary)
        db.session.add(orf)

    db.session.commit()

from subprocess import PIPE, run
def create_single_tncentral(fasta_dir, filename):
    command = f"cat {fasta_dir}/* > {filename}"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
    return result



def external_addon_fasta(filename, external_list):
    for external_fasta in external_list:
        command = f"cat {external_fasta} > {filename}"
        result = run(command, stdout=PIPE, stderr=PIPE, shell=True)


def create_blast_database(current_dir, filename):
    command = f"cd {current_dir}; makeblastdb -in {filename} -dbtype nucl -parse_seqids"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)
    
    # exporting protein database
    a_filename = filename.split(".")
    protein_file = ".".join(a_filename[0:-1])
    protein_file = protein_file + ".prot." + a_filename[-1]
    protein_file = os.path.join(current_dir, protein_file)

    all_orf = Te_Orf.query.all()
    with open(protein_file, "w") as writer:
        dict_rank = {}
        for orf in all_orf:
            sequence = orf.sequence
            sequence = sequence.replace(" ", "")
            accession = orf.te_entry.accession
            if accession in dict_rank:
                dict_rank[accession] = dict_rank[accession] + 1
            else:
                dict_rank[accession] = 1
            name = orf.name
            name = name.replace(" ", "_")
            header_fasta = f"{accession}|{dict_rank[accession]}"
            # header_fasta = header_fasta[:50]
            writer.write(f">{header_fasta}\n")
            # fragments = orf.fragments
            # for fragment in fragments:
            #     writer.write(f"__{fragment.start}_{fragment.end}")
            # writer.write(f"\n")
            writer.write(f"{sequence}\n")
    # create blast protein database
    command = f"makeblastdb -in {protein_file} -dbtype prot"
    result = run(command, stdout=PIPE, stderr=PIPE, shell=True)

def export_fasta(gb_dir, fasta_dir, fmt_fasta_dir, current_dir):
    gb_files = os.listdir(gb_dir)
    for gb_file in gb_files:
        gb_path = os.path.join(gb_dir, gb_file)
        gb_obj = get_genbank_object(gb_path)
        # pubmed_ids = [p.pubmed for p in gb_obj.references if p.pubmed]
        if gb_obj.accession is not None:
            export_fasta_file(gb_obj.sequence_as_text(), gb_obj.accession, fasta_dir)
            export_fmt_fasta(gb_obj.sequence_as_text(), gb_obj.accession, fmt_fasta_dir)
            # export_pubmed_ids(gb_obj.accession, pubmed_ids, current_dir)

def load_external(database_name, ids_file):
    with open(ids_file) as reader:
        line = reader.readline()
        while line:
            line = line.strip()
            ext_re = External_Resource()
            ext_re.database_name=database_name
            ext_re.resource_id=line
            db.session.add(ext_re)
            line = reader.readline()
        db.session.commit()
            

def load_db_new(gb_dir):
    gb_files = os.listdir(gb_dir)
    for gb_file in gb_files:
        if gb_file.endswith(".gb"):
            print(f"Reading {gb_file}...")
            gb_path = os.path.join(gb_dir, gb_file)
            gb_obj = get_genbank_object(gb_path)
            if gb_obj.accession is not None:
                main_entry = save_obj_to_db(gb_obj, in_production=1)
                db.session.add(main_entry)
                db.session.commit()
    # create_single_tncentral(current_dir, fasta_dir, fasta_name)
    # create_blast_database(current_dir, fasta_name)
    create_orf_summary()

from flask_tn.ext.database import db
from flask_tn.db_models import Te_Pubmed
from flask_tn.utils import gb_utils
def load_pubmed(dir_pubmed):
    list_pubmed = Te_Pubmed.query.filter_by(title=None)
    for pubmed_obj in list_pubmed:
        pubmed_id = str(pubmed_obj.pubmed_id)
        pub_path = os.path.join(dir_pubmed, pubmed_id)
        
        list_lines = gb_utils.get_lines(pub_path)
        pubmed_dict = gb_utils.get_pubmed_from_lines(list_lines)

        pubmed_obj.title = pubmed_dict["title"]
        pubmed_obj.authors = pubmed_dict["authors"]
        pubmed_obj.summary = pubmed_dict["summary"]
        db.session.commit()

def create_zip(base_dir, file_to_zip, zip_name, internal_folder='fa', ext="fa"):
    zip_name = os.path.join(base_dir, zip_name)
    with zipfile.ZipFile(zip_name, 'w') as myzip:
        if os.path.isdir(file_to_zip):
            for file in os.listdir(file_to_zip):
                if not file.startswith(".") and file.endswith(f".{ext}"):
                    myzip.write(os.path.join(file_to_zip, file), os.path.join(internal_folder,file))
        else:
            basename = os.path.basename(file_to_zip)
            myzip.write(os.path.join(base_dir, file_to_zip), basename)

def create_nuc_gb(base_dir, current_dir, dir_fasta, fasta_name, list_external):
    fasta_dir = os.path.join(current_dir, dir_fasta)
    
    fasta_final = os.path.join(current_dir, fasta_name)
    if os.path.exists(fasta_final):
        os.remove(fasta_final)
    ext_to_remove = ["nhr", "nin", "nog", "nsd", "nsi", "nsq"]
    for ext in ext_to_remove:
        file_to_remove = os.path.join(current_dir, fasta_name + "." + ext)
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)

    run(f"cat {fasta_dir}/* > {fasta_final}", stdout=PIPE, stderr=PIPE, shell=True)
    run(f"/usr/bin/perl -pi -e 's/\r//g' {fasta_final}", stdout=PIPE, stderr=PIPE, shell=True)

    for external_fasta in list_external:
        ext_path = os.path.join(base_dir, external_fasta)
        run(f"/usr/bin/perl -pi -e 's/\r//g' {ext_path}", stdout=PIPE, stderr=PIPE, shell=True)
        run(f"cat {ext_path} >> {fasta_final}", stdout=PIPE, stderr=PIPE, shell=True)
    
    run(
        f"cd {current_dir}; makeblastdb -in {fasta_final} -dbtype nucl -parse_seqids",
        stdout=PIPE, stderr=PIPE, shell=True
    )

def create_prot_gb(current_dir, prot_filename):
    fasta_final = os.path.join(current_dir, prot_filename)
    if os.path.exists(fasta_final):
        os.remove(fasta_final)
    ext_to_remove = ["phr", "pin", "psq"]
    for ext in ext_to_remove:
        file_to_remove = os.path.join(current_dir, prot_filename + "." + ext)
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)

    all_orf = Te_Orf.query.filter(Te_Orf.te_entry.has(in_production=1)).all()
    with open(fasta_final, "w") as writer:
        dict_rank = {}
        for orf in all_orf:
            sequence = orf.sequence
            sequence = sequence.replace(" ", "")
            accession = orf.te_entry.accession
            if accession in dict_rank:
                dict_rank[accession] = dict_rank[accession] + 1
            else:
                dict_rank[accession] = 1
            name = orf.name
            name = name.replace(" ", "_")
            header_fasta = f"{accession}|{dict_rank[accession]}"
            writer.write(f">{header_fasta}\n")
            writer.write(f"{sequence}\n")
    # create blast protein database
    result = run(f"cd {current_dir}; makeblastdb -in {fasta_final} -dbtype prot", stdout=PIPE, stderr=PIPE, shell=True)

def recreate_blast(cmd_makeblastdb, base_dir, current_dir, fasta_dir, fasta_nc,
                   external_nc, fasta_prot, gb_dir, csv_dir, list_orf):
    
    # recreate tncentral.fa
    fasta_final = os.path.join(current_dir, fasta_nc)
    if os.path.exists(fasta_final):
        os.remove(fasta_final)
    ext_to_remove = ["nhr", "nin", "nog", "nsd", "nsi", "nsq"]
    for ext in ext_to_remove:
        file_to_remove = os.path.join(current_dir, fasta_nc + "." + ext)
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)

    result = run(f"cat {fasta_dir}/* > {fasta_final}", stdout=PIPE, stderr=PIPE, shell=True)
    for external_fasta in external_nc:
        ext_path = os.path.join(base_dir, external_fasta)
        result = run(f"/usr/bin/perl -pi -e 's/\r//g' {ext_path}", stdout=PIPE, stderr=PIPE, shell=True)
        result = run(f"cat {ext_path} >> {fasta_final}", stdout=PIPE, stderr=PIPE, shell=True)

    result = run(
        f"{cmd_makeblastdb} -in {fasta_final} -dbtype nucl -parse_seqids",
        stdout=PIPE, stderr=PIPE, shell=True
    )
    # create_zip(current_dir, fasta_dir, fasta_nc+".zip")

    fasta_prot_final = os.path.join(current_dir, fasta_prot)
    if os.path.exists(fasta_prot_final):
        os.remove(fasta_prot_final)

    ext_to_remove = ["phr", "pin", "psq"]
    for ext in ext_to_remove:
        file_to_remove = os.path.join(current_dir, fasta_prot + "." + ext)
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)

    with open(fasta_prot_final, "w") as writer:
        for orf in list_orf:
            writer.write(f">{orf['header']}\n")
            writer.write(f"{orf['sequence']}\n")
    # create blast protein database
    result = run(f"{cmd_makeblastdb} -in {fasta_prot_final} -dbtype prot", stdout=PIPE, stderr=PIPE, shell=True)
    

def update_entry_from_dict(entry_obj, current_dict):
    if "note" in current_dict:
        fragments = current_dict["fragments"]
        for fragment in fragments:
            te_fragment = Te_Fragment()
            te_fragment.start = fragment["start"]
            te_fragment.end = fragment["end"]
            te_fragment.strand = fragment["strand"]
            entry_obj.fragments.append(te_fragment)

        if "mobile_element_type" in current_dict:
            type_ = current_dict["mobile_element_type"]
            entry_obj.type = type_["type"]
            entry_obj.name = type_["name"]
        else:
            # maybe throw an error here
            pass

        dict_note = current_dict["note"]

        entry_obj.accession = dict_note["Accession"]

        if "First" in dict_note and dict_note["First"] == "yes":
            entry_obj.first_isolate = 1
        elif "First" in dict_note and dict_note["First"] == "no":
            entry_obj.first_isolate = 0

        if "Capture" in dict_note and dict_note["Capture"] == "yes":
            entry_obj.capture = 1
        elif "Capture" in dict_note and dict_note["Capture"] == "no":
            entry_obj.capture = 0

        if "Partial" in dict_note and dict_note["Partial"] == "yes":
            entry_obj.partial = 1
        elif "Partial" in dict_note and dict_note["Partial"] == "no":
            entry_obj.partial = 0

        if "Transposition" in current_dict and current_dict["Transposition"] == "yes":
            entry_obj.transposition = 1
        elif "Transposition" in current_dict and current_dict["Transposition"] == "no":
            entry_obj.transposition = 0

        if "Family" in dict_note:
            entry_obj.family = dict_note["Family"].strip()

        if "Group" in dict_note:
            entry_obj.group = dict_note["Group"].strip()

        if "Synonyms" in dict_note:
            entry_obj.synonyms = dict_note["Synonyms"].strip()

        if "Hosts: Organism" in dict_note:
            entry_obj.organism = dict_note["Hosts: Organism"].strip()
        elif "Hosts: Hosts: Organism" in dict_note:
            entry_obj.organism = dict_note["Hosts: Hosts: Organism"].strip()
        elif "Hosts:Organism" in dict_note:
            entry_obj.organism = dict_note["Hosts:Organism"].strip()
        elif "Organism" in dict_note:
            entry_obj.organism = dict_note["Organism"].strip()

        if "Country" in dict_note:
            entry_obj.country = dict_note["Country"].strip()
        else:  # maybe throw an error?
            pass

        if "DateIdentified" in dict_note:
            entry_obj.date = dict_note["DateIdentified"].strip()
        else:  # maybe throw an error?
            pass

        if "OtherInformation" in dict_note:
            entry_obj.comment = dict_note["OtherInformation"].strip()

        if "BacGroup" in dict_note:
            entry_obj.bacteria_group = dict_note["BacGroup"].strip()

        if "MolecularSource" in dict_note:
            entry_obj.molecular_source = dict_note["MolecularSource"].strip()

        if "Region" in dict_note:
            entry_obj.region = dict_note["Region"].strip()

        if "OtherLocInfo" in dict_note:
            entry_obj.other_loc = dict_note["OtherLocInfo"].strip()


def create_csv_file(current_dir, csv_dir, csv_name):
    csv_dir = os.path.join(current_dir, csv_dir)
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)

    csv_file = os.path.join(current_dir, csv_name)

    res = Te_Entry.query.filter_by(entry_id_parent=None, in_production=1).all()
    with open(csv_file, "w") as h:
        for re in res:
            h.write(re.as_csv())
            h.write("\n")
            new_file = os.path.join(csv_dir, re.accession + ".csv")
            with open(new_file, "w") as new_writer:
                new_writer.write(re.as_csv())
                new_writer.write("\n")

    create_zip(current_dir, csv_dir, csv_name+".zip", "csv/")


def download_pubmed(id_file, pubmed_folder):
    check_dict = {}
    check_pubmed = []
    with open(id_file, "r") as handle:
        for line in handle:
            line = line.strip()
            columns = line.split("\t")
            entry_id = columns[0]
            entry = Te_Entry.query.filter_by(
                entry_id_parent=None, accession=entry_id, in_production=1
            ).first()
            if len(columns) > 1 and not entry_id in check_dict:
                check_dict[entry_id] = {}
                ids = columns[1].split(",")
                for pubmed_id in ids:
                    print(f"Inserting {entry_id} - PubmedId: {id}")
                    if not pubmed_id in check_dict[entry_id]:
                        pub_dict = export_pubmed_file(pubmed_id, pubmed_folder)
                        if not pubmed_id in check_pubmed:
                            check_pubmed.append(pubmed_id)
                            pub_obj = Te_Pubmed()
                            pub_obj.pubmed_id = pub_dict["pubmed"]["pubmed_id"]
                            pub_obj.title = pub_dict["pubmed"]["title"]
                            pub_obj.authors = pub_dict["pubmed"]["authors"]
                            pub_obj.summary = pub_dict["pubmed"]["summary"]
                            db.session.add(pub_obj)
                        else:
                            pub_obj = Te_Pubmed.query.filter_by(
                                pubmed_id=pubmed_id
                            ).first()
                        entry.pubmeds.append(pub_obj)
                        check_dict[entry_id][id] = 1
    db.session.commit()

def get_pubmed_from_file(filepath):
    list_lines = []
    with open(filepath) as reader:
        list_lines = reader.readlines()
    return get_pubmed_from_lines(list_lines)

def get_pubmed_from_lines(list_lines):
    hash_line = {}
    last = ""
    for line in list_lines:
        line = line.strip()
        if line != "":
            match = re.search("([A-Z]+)\s*\-\s+(.+)$", line)
            if match != None:
                last = match.group(1)
                if last in hash_line:
                    hash_line[last].append(match.group(2))
                else:
                    hash_line[last] = [match.group(2)]
            else:
                content = hash_line[last][-1] + " " + line
                hash_line[last][-1] = content
    pubmed_hash = {
        "pubmed_id": int(hash_line["PMID"][0]),
        "title": hash_line["TI"][0],
        "summary": hash_line["SO"][0],
        "authors": ", ".join(hash_line["AU"]),
    }
    return pubmed_hash


def export_pubmed_file(pubmed_id, dir_pubmed):
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
        list_lines = get_lines(pub_path)

    pubmed_dict = get_pubmed_from_lines(list_lines)
    return pubmed_dict


def pub_db_to_tn(db_obj:Te_Pubmed) -> TnReference:
    tnRef = TnReference()

    authors = f"{ref_first_col('AUTHORS')}{db_obj.authors}"
    l_authors = break_by_column(authors)
    l_authors[0] = l_authors[0].replace(ref_first_col("AUTHORS"), "")
    if len(l_authors) > 1:
        l_authors[1:] = [x.replace(f"{' '*12}", "") for x in l_authors[1:]]
    tnRef.authors = l_authors

    title = f"{ref_first_col('TITLE')}{db_obj.title}"
    l_title = break_by_column(title)
    l_title[0] = l_title[0].replace(ref_first_col('TITLE'), "")
    if len(l_title) > 1:
        l_title[1:] = [x.replace(f"{' '*12}", "") for x in l_title[1:]]
    tnRef.title = l_title

    journal = f"{ref_first_col('JOURNAL')}{db_obj.summary}"
    l_journal = break_by_column(journal)
    l_journal[0] = l_journal[0].replace(ref_first_col('JOURNAL'), "")
    if len(l_journal) > 1:
        l_journal[1:] = [x.replace(f"{' '*12}", "") for x in l_journal[1:]]
    tnRef.journal = l_journal

    tnRef.pubmed.append(db_obj.pubmed_id)
    
    return tnRef


def format_reference(db_obj:Te_Pubmed):
    text = ""
    authors = f"{ref_first_col('AUTHORS')}{db_obj.authors}"
    l_authors = break_by_column(authors)
    text = "\n".join(l_authors)

    title = f"{ref_first_col('TITLE')}{db_obj.title}"
    l_title = break_by_column(title)
    text += "\n".join(l_title)

    journal = f"{ref_first_col('JOURNAL')}{db_obj.summary}"
    l_journal = break_by_column(journal)
    text += "\n".join(l_journal)

    pubmed = f"{ref_first_col('PUBMED')}{db_obj.pubmed_id}\n"
    text += pubmed
    return text

def ref_first_col(text):
    return f"  {text}{' '*(10-len(text))}"

def break_by_column(text_value:str, ncol=80, space_offset=12):
    text_value = text_value.strip("\n")
    len_text = len(text_value)
    if len_text <= ncol:
        return [text_value]
    lines = []
    words = text_value.split(' ')

    line = ""
    only_space = True
    while len(words) > 0:
        word = words.pop(0)
        if word == '':
            mock_line = f"{line} "
        else:
            if only_space:
                only_space = False
                mock_line = f"{line}{word}"
            else:
                mock_line = f"{line} {word}"
        if len(mock_line) <= ncol:
            line = mock_line
        else:
            lines.append(line)
            # starting in the second line, we always add spaces
            # in the beginning of the line if space_offset is greater than 0
            line = f"{' '*space_offset}{word}"
    if len(line) > 0:
        lines.append(line)
    return lines