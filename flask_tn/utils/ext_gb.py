import flask_tn.utils as utils
import flask_tn.utils.gb_utils as gb_utils
import re

def gb_to_dict(genbank_file):
    single_entry = []
    list_obj = None
    with open(genbank_file, 'r', encoding="latin1") as reader:
        line = reader.readline()
        while line:
            if re.match("^\/\/\s*$", line) != None:
                single_entry.append(line)
                list_obj = gb_utils.get_dict_from_genbank(single_entry)
            else:
              single_entry.append(line)
            line = reader.readline()
    return list_obj

# def save_dict_to_db(list_obj, external_dict):
#     main_entry = Te_Entry()
#     myit = iter(list_obj)
#     is_main = True
#     dict_objects = {}
#     current_dict = next(myit)
#     count_repeat = 0
#     # we will ignore the first features until we find the mobile element
#     while current_dict:
#         key = list(current_dict.keys())[0]
#         if key == "mobile_element":
#             break
#         else:
#             current_dict = next(myit)
#     # now we iterate through the features
#     while current_dict:
#         key = list(current_dict.keys())[0]
#         if key == "mobile_element" and "Accession" in current_dict[key]["note"]:
#             if is_main:
#                 is_main = False
#                 gb_utils.update_entry_from_dict(main_entry, current_dict[key])
#                 if main_entry.accession:
#                     dict_objects[main_entry.name]=[]
#                     dict_objects[main_entry.name].append(main_entry)
#                     is_main = False
#                     db.session.add(main_entry)
#                 else:
#                     print("errorororoeoe")
#             else:
#                 entry_new = Te_Entry()
#                 gb_utils.update_entry_from_dict(entry_new, current_dict[key])
#                 if entry_new.accession:
#                     if entry_new.name in dict_objects:
#                         if not utils.compare_entries(entry_new, dict_objects[entry_new.name]):
#                             entry_new.parents=main_entry
#                             db.session.add(entry_new)
#                             dict_objects[entry_new.name].append(entry_new)
#                     else:
#                         entry_new.parents=main_entry
#                         dict_objects[entry_new.name]=[]
#                         dict_objects[entry_new.name].append(entry_new)
#                         db.session.add(entry_new)
#         elif key == "repeat_region" and "note" in current_dict[key]:
#             count_repeat += 1
#             repeat_obj = Te_Repeat()
#             fragments = current_dict[key]["fragments"]
#             sequence = ""
#             for fragment in fragments:
#                 te_fragment = Te_Repeat_Fragment()
#                 te_fragment.start=fragment["start"]
#                 te_fragment.end=fragment["end"]
#                 te_fragment.strand=fragment["strand"]
#                 new_sequence = external_dict["sequence"][te_fragment.start-1:te_fragment.end]
#                 if te_fragment.strand == "-":
#                     new_sequence = utils.reverse_complement(new_sequence)
#                 sequence += new_sequence
#                 repeat_obj.fragments.append(te_fragment)
#             repeat_obj.sequence=sequence
#             if "label" in current_dict[key]:
#                 repeat_obj.display_name=current_dict[key]["label"].strip()
#             dict_note = current_dict[key]["note"]
#             if "Name" in dict_note:
#                 repeat_obj.name=dict_note["Name"].strip()
#             if "LibraryName" in dict_note:
#                 repeat_obj.library_name=dict_note["LibraryName"].strip()
#             if "OtherInformation" in dict_note:
#                 repeat_obj.comment=dict_note["OtherInformation"].strip()
            
#             # TODO: check why there is no associated element in dict_objects
#             if "AssociatedElement" in dict_note:
#                 associated_element = dict_note["AssociatedElement"].strip()
#                 repeat_obj.associated_te=associated_element
#                 if associated_element in dict_objects:
#                     length_objects = len(dict_objects[associated_element])
#                     obj = dict_objects[associated_element][length_objects-1]
#                     repeat_obj.te_entry=obj
#                     db.session.add(repeat_obj)
#                 else:
#                     pass
#                     # print(f"Associated element {associated_element}")
#                     # print(f"Repeat: {repeat_obj.display_name}")
#         elif key == "CDS" and "gene" in current_dict[key] and "note" in current_dict[key]:
#             orf_obj = Te_Orf()

#             fragments = current_dict[key]["fragments"]
            
#             for fragment in fragments:
#                 te_fragment = Te_Orf_Fragment()
#                 te_fragment.start=fragment["start"]
#                 te_fragment.end=fragment["end"]
#                 te_fragment.strand=fragment["strand"]
#                 orf_obj.fragments.append(te_fragment)

#             orf_obj.name=current_dict[key]["gene"].strip()

#             if "label" in current_dict[key]:
#                 orf_obj.display_name=current_dict[key]["label"].strip()
#             if "product" in current_dict[key]:
#                 orf_obj.protein_name=current_dict[key]["product"].strip()
#             if "protein_id" in current_dict[key]:
#                 orf_obj.genbank_id=current_dict[key]["protein_id"].strip()
#             if "translation" in current_dict[key]:
#                 orf_obj.sequence=current_dict[key]["translation"].strip()
#             if "function" in current_dict[key]:
#                 orf_obj.function=current_dict[key]["function"].strip()
            
#             dict_note = current_dict[key]["note"]
#             if "Class" in dict_note:
#                 orf_obj.orf_class=dict_note["Class"].strip()
#             if "Subclass" in dict_note:
#                 orf_obj.subclass=dict_note["Subclass"].strip()
#             if "SequenceFamily" in dict_note:
#                 orf_obj.sequence_family=dict_note["SequenceFamily"].strip()
#             if "Chemistry" in dict_note:
#                 orf_obj.chemistry=dict_note["Chemistry"].strip()
#             if "Target" in dict_note:
#                 orf_obj.target=dict_note["Target"].strip()
#             if "LibraryName" in dict_note:
#                 orf_obj.library_name=dict_note["LibraryName"].strip()
#             if "OtherInformation" in dict_note:
#                 orf_obj.comment=dict_note["OtherInformation"].strip()
            
#             if "AssociatedElement" in dict_note:
#                 associated_element = dict_note["AssociatedElement"].strip()
#                 orf_obj.associated_te=associated_element
#                 if associated_element in dict_objects:
#                     length_objects = len(dict_objects[associated_element])
#                     obj = dict_objects[associated_element][length_objects-1]
                
#                     orf_obj.te_entry=obj
#                     db.session.add(orf_obj)

#         elif key == "misc_feature" and "note" in current_dict[key]:
#             res_obj = Te_RecombSite()
#             if "label" in current_dict[key]:
#                 res_obj.display_name=current_dict[key]["label"]
            
#             fragments = current_dict[key]["fragments"]
#             sequence = ""
#             for fragment in fragments:
#                 te_fragment = Te_Recomb_Fragment()
#                 te_fragment.start=fragment["start"]
#                 te_fragment.end=fragment["end"]
#                 te_fragment.strand=fragment["strand"]
#                 new_sequence = external_dict["sequence"][te_fragment.start-1:te_fragment.end]

#                 if te_fragment.strand == "-":
#                     new_sequence = utils.reverse_complement(new_sequence)

#                 sequence += new_sequence
#                 res_obj.fragments.append(te_fragment)
            
#             res_obj.sequence=sequence

#             dict_note = current_dict[key]["note"]
#             if "Name" in dict_note and "AssociatedElement" in dict_note:
#                 res_obj.name=dict_note["Name"].strip()

#                 if "label" in dict_note:
#                     res_obj.display_name=dict_note["label"].strip()
#                 if "LibraryName" in dict_note:
#                     res_obj.library_name=dict_note["LibraryName"].strip()
#                 if "OtherInformation" in dict_note:
#                     res_obj.comment=dict_note["OtherInformation"].strip()
                    
#                 associated_element = dict_note["AssociatedElement"].strip()
#                 res_obj.associated_te=associated_element
#                 if associated_element in dict_objects:
#                     length_objects = len(dict_objects[associated_element])
#                     obj = dict_objects[associated_element][length_objects-1]
#                     res_obj.te_entry=obj
#                     db.session.add(res_obj)
#         else:
#             pass
#         try:
#             current_dict = next(myit)
#         except StopIteration:
#             db.session.commit()
#             break
#     return main_entry

#  This function takes a path to a Genbank file and return two lists and a sequence.
# The two lists are:
# list_info: each element of the list is one eleme
# list_features: each feature in the genbank will be an element in this list
# sequence
def read_gb(genbank_file):
    list_info = []
    list_features = []
    sequence = ""
    with open(genbank_file, "r", encoding="latin1") as reader:
        line = reader.readline()
        last_header = ""
        content = ""
        while re.match("^FEATURES\s+.+$", line) == None:
            match_result = re.match("^(\w+)\s+(.+)$", line)
            if match_result != None:
                last_header = match_result.group(1)
                content = match_result.group(2) + "\n"
                internal_dict = {last_header: content}
                list_info.append(internal_dict)
            else:
                list_info[-1][last_header] = list_info[-1][last_header] + line.lstrip()
            line = reader.readline()
        line = reader.readline()
        last_feature = ""
        last_key = ""
        while re.match("^ORIGIN.*$", line) == None:
            match_result = re.match("^\s{5}(\w+)\s+(.+)$", line)
            if match_result != None:
                last_feature = match_result.group(1)
                dict_feature = {
                    "feature": last_feature,
                    "coordinates": match_result.group(2),
                    "properties": [],
                }
                list_features.append(dict_feature)
            else:
                match_result = re.search("^\s{21}\/(\w+)=(.+)$", line)
                if match_result != None:
                    last_key = match_result.group(1)
                    value = match_result.group(2)
                    value = value.strip('"')
                    internal_dict = {last_key: value}
                    list_features[-1]['properties'].append(internal_dict)
                else:
                    match_result = re.search("^\/(\w+)$", line)
                    match2 = re.search("^[xX]+$", line)
                    if match_result != None or match2 != None:  # tag without value
                        pass
                    else:
                        line = line.strip()
                        line = line.strip('"')
                        value = list_features[-1]['properties'][-1][last_key] + " " + line
                        list_features[-1]['properties'][-1][last_key] = value
            line = reader.readline()
        line = reader.readline()
        while re.match("^//$", line) == None:
            match_result = re.match("^\s+\d+\s+(\S+.+)$", line)
            if match_result != None:
                sequence += match_result.group(1).replace(" ", "")
                # internal_sequence.replace(" ", "")
            else:
                print("Errorrrrrrrrrrrrrrrrrrrrrr")
            line = reader.readline()
    return (list_info, list_features, sequence)
