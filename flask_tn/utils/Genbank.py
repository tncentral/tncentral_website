from typing import List
import flask_tn.utils.Constants as Constants
import re


# This class represent a sequence fragment of dna or rna according to a reference
class LocationFragment:
    def __init__(self, start=None, end=None, strand=None):
        # Constructor method to initialize the object with start, end, and strand attributes.
        self.__start: int = (
            start  # private attribute: the start position of a sequence fragment
        )
        self.__end: int = (
            end  # private attribute: the end position of a sequence fragment
        )
        self.__strand: str = strand

    @property
    def start(self) -> int:
        # Getter method for the attribute 'start'.
        return self.__start

    @start.setter
    def start(self, value):
        # Setter method for the attribute 'start'.
        self.__start = value

    @property
    def end(self) -> int:
        return self.__end

    @end.setter
    def end(self, value):
        self.__end = value

    @property
    def strand(self) -> str:
        return self.__strand

    @strand.setter
    def strand(self, value):
        self.__strand = value

    def __str__(self) -> str:
        return f"{self.__start}-{self.__end}-{self.__strand}"


class Qualifier:
    def __init__(self):
        self.__line_number: int = None
        self.__key: str = None
        self.__value: str = []

    @property
    def line_number(self):
        return self.__line_number

    @line_number.setter
    def line_number(self, value):
        self.__line_number = value

    @property
    def key(self):
        return self.__key

    @key.setter
    def key(self, value):
        self.__key = value

    @property
    def value(self):
        return self.__value
    
    @value.setter
    def value(self, new_value):
        if type(new_value) is not list:
            self.__value = [new_value]
        else:
            self.__value = []
            self.__value = new_value.copy()

    def value_to_str(self, strip=False):
        return_line = ""
        for line in self.value:
            line = line.lstrip()
            line = line.strip('\n')
            return_line += line
        if strip:
            return_line = return_line.strip('"')
        return return_line

    def __str__(self) -> str:
        return_line = f"{' '*21}/{self.key}="
        if len(self.__value) > 0:
            return_line += self.__value[0] + "\n"
            for n in range(1, len(self.__value)):
                return_line += f"{' '*21}{self.__value[n]}\n"
        return return_line


class Feature:
    def __init__(self):
        self.__line_number: int = None
        self.__name: str = None
        self.__fragments_text: str = None
        self.__fragments: LocationFragment = []
        self.__qualifiers: Qualifier = []

    def create_qualifier(self, add_after, qualifier_name, value):
        add_index = 0
        for idx in range(0, len(self.qualifiers)):
            if self.qualifiers[idx].key == add_after:
                add_index = idx
        qualifier = Qualifier()
        qualifier.key = qualifier_name
        qualifier.value = value
        self.qualifiers.insert(add_index+1, qualifier)
        # return qual_obj

    def get_qualifier(self, qualifier_name):
        qual_obj = None
        for q in self.qualifiers:
            if q.key == qualifier_name:
                qual_obj = q
                break
        return qual_obj

    @property
    def line_number(self):
        return self.__line_number

    @line_number.setter
    def line_number(self, value):
        self.__line_number = value

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = value

    @property
    def fragments_text(self):
        return self.__fragments_text

    @fragments_text.setter
    def fragments_text(self, value):
        self.__fragments_text = value

    @property
    def fragments(self):
        return self.__fragments
    
    def min_max_pos(self):
        min_pos = self.fragments[0].start
        max_pos = self.fragments[0].end
        if min_pos > max_pos:
            swap_pos = min_pos
            min_pos = max_pos
            max_pos = swap_pos
        for i in range(1,len(self.fragments)):
            start_pos = self.fragments[i].start
            end_pos = self.fragments[i].end
            if start_pos > end_pos:
                swap_pos = start_pos
                start_pos = end_pos
                end_pos = start_pos
            if start_pos < min_pos:
                min_pos = start_pos
            if end_pos < max_pos:
                max_pos = end_pos
        return (min_pos, max_pos)
        

    @fragments.setter
    def fragments(self, fragments):
        self.__fragments = fragments.copy()

    @property
    def qualifiers(self):
        return self.__qualifiers

    def __str__(self) -> str:
        spaces_middle = 16 - len(self.name)
        lines = f"{' '*5}{self.name}{' '*spaces_middle}{self.fragments_text}\n"
        for q in self.qualifiers:
            lines += str(q)
        return lines


class Genbank:
    def __init__(self):
        self.__header: str = []
        self.__features: Feature = []
        self.__fmt_sequence: str = []
        self.__sequence: str = []

    @property
    def header(self) -> List[str]:
        return self.__header

    @property
    def features(self) -> List[Feature]:
        return self.__features

    @property
    def sequence(self) -> List[str]:
        return self.__sequence

    def empty_sequence(self):
        self.__sequence = []

    def sequence_as_text(self) -> str:
        sequence = ""
        for seq in self.__sequence:
            s1 = "".join(c for c in seq if c.isalpha())
            sequence += s1
        return sequence
    def len_sequence(self) -> int:
        return len(self.sequence_as_text())

    def __str__(self) -> str:
        lines = ""
        for header in self.header:
            lines += header
        lines += f"FEATURES{' '*13}Location/Qualifiers\n"
        for feature in self.features:
            lines += str(feature)
        lines += "ORIGIN\n"
        for seq in self.sequence:
            lines += seq
        lines += "//\n"
        return lines

class TnFeature(Feature):
    def __init__(self):
        super().__init__()
        self.__dict_note = {}
        self.__display_name=""
        self.__tn_type=""
        self.__tn_name=""
    
    @property
    def tn_type(self) -> str:
        if self.__tn_type == "":
            met = super().get_qualifier(Constants.QL_MOBILE_ELEMENT_TYPE)        
            met_array = met.value_to_str(strip=True).split(":")
            self.__tn_type=met_array[0]
            self.__tn_name=":".join(met_array[1:])
        return self.__tn_type

    @property
    def tn_name(self) -> str:
        if self.__tn_type == "":
            met = super().get_qualifier(Constants.QL_MOBILE_ELEMENT_TYPE)        
            met_array = met.value_to_str(strip=True).split(":")
            self.__tn_type=met_array[0]
            self.__tn_name=":".join(met_array[1:])
        return self.__tn_name

    @property
    def dict_note(self) -> dict:
        return self.__dict_note
    
    @dict_note.setter
    def dict_note(self, new_dict):
        self.__dict_note = new_dict.copy()
    
    @property
    def display_name(self) -> str:
        return self.__display_name
    
    @display_name.setter
    def display_name(self, value):
        self.__display_name = value

    def is_valid(self):
        has_label = super().get_qualifier(Constants.QL_LABEL)
        has_note = super().get_qualifier(Constants.QL_NOTE)
        is_v = True
        if not has_label or not has_note:
            is_v = False
        else:
            if super().name == Constants.FT_CDS:
                has_gene = super().get_qualifier(Constants.QL_GENE)
                has_translation = super().get_qualifier(Constants.QL_TRANSLATION)
                if not has_gene or not has_translation:
                    is_v = False
        return is_v

class TnReference():
    def __init__(self, refNumber=0, seqStart=0, seqEnd=0):
        self.__refNumber:int = refNumber
        self.__seqStart:int = seqStart
        self.__seqEnd:int = seqEnd
        self.__authors:str = []
        self.__title:str = []
        self.__journal:str = []
        self.__pubmed:str = []

    @property
    def refNumber(self) -> int:
        return self.__refNumber
    @refNumber.setter
    def refNumber(self, n:int) -> None:
        self.__refNumber = n
    
    @property
    def seqStart(self) -> int:
        return self.__seqStart
    @seqStart.setter
    def seqStart(self,s:int) -> None:
        self.__seqStart = s
    
    @property
    def seqEnd(self) -> int:
        return self.__seqEnd
    @seqEnd.setter
    def seqEnd(self,s:int) -> None:
        self.__seqEnd = s
    
    @property
    def authors(self) -> List[str]:
        return self.__authors
    
    @authors.setter
    def authors(self,a:List[str]) -> None:
        self.__authors = a
    
    @property
    def title(self) -> List[str]:
        return self.__title
    @title.setter
    def title(self,t:List[str]) -> None:
        self.__title = t
    
    @property
    def journal(self) -> List[str]:
        return self.__journal
    @journal.setter
    def journal(self,j:List[str]) -> None:
        self.__journal = j
    
    @property
    def pubmed(self) -> List[str]:
        return self.__pubmed
    @pubmed.setter
    def pubmed(self,p:List[str]) -> None:
        self.__pubmed = p
    
    def __str__(self):
        return_str = f"REFERENCE{' '*3}{self.refNumber}  (bases {self.seqStart} to {self.seqEnd})\n"
        if self.authors:
            return_str += f"{' '*2}AUTHORS{' '*3}{self.authors[0]}\n"
            for i in range(1, len(self.authors)):
                return_str += f"{' '*12}{self.authors[i]}\n"
        if self.title:
            return_str += f"{' '*2}TITLE{' '*5}{self.title[0]}\n"
            for i in range(1, len(self.title)):
                return_str += f"{' '*12}{self.title[i]}\n"
        if self.journal:
            return_str += f"{' '*2}JOURNAL{' '*3}{self.journal[0]}\n"
            for i in range(1, len(self.journal)):
                return_str += f"{' '*12}{self.journal[i]}\n"
        if self.pubmed:
            return_str += f"{' '*2}PUBMED{' '*4}{self.pubmed[0]}\n"
            for i in range(1, len(self.pubmed)):
                return_str += f"{' '*12}{self.pubmed[i]}\n"
        return return_str
        

class TnGenbank(Genbank):
    def __init__(self):
        super().__init__()
        self.__pubmed_ids: int = []
        self.__references: TnReference = []
        self.__main_feature:TnFeature = None
        self.__accession: str = ""
        self.__tn_type: str = ""
        self.__name: str =""

    @property
    def pubmed_ids(self) -> List[int]:
        return self.__pubmed_ids
    
    @property
    def references(self) -> List[TnReference]:
        return self.__references

    @property
    def accession(self) -> str:
        if self.__accession == "":
            self.get_main_feature()
        return self.__accession
    
    @accession.setter
    def accession(self, a) -> None:
        self.__accession = a

    @property
    def tn_type(self) -> str:
        if self.__tn_type == "":
            self.get_main_feature()
        return self.__tn_type
    
    @property
    def name(self) -> str:
        if self.__name == "":
            self.get_main_feature()
        return self.__name
    
    def get_main_feature(self) -> TnFeature:
        if self.__main_feature == None:
            for feature in self.features:
                if feature.name == Constants.FT_MOBILE_ELEMENT:
                    self.__main_feature = feature
                    met = feature.get_qualifier(Constants.QL_MOBILE_ELEMENT_TYPE)
                    met_array=met.value_to_str(strip=True).split(":")
                    tn_type = met_array[0]
                    name = ":".join(met_array[1:])
                    self.__tn_type=tn_type
                    self.__name=name
                    note_obj = feature.get_qualifier(Constants.QL_NOTE)
                    note_txt = note_obj.value_to_str()
                    (dict_note, dict_error) = dict_from_note(feature.name, note_txt)
                    self.__main_feature.dict_note = dict_note
                    self.__accession=dict_note[Constants.NT_ACCESSION]
                    break
        return self.__main_feature
    
    # Return the children features children of an associated element
    def children_feature(self, feature_name, parent_obj = None) -> List[TnFeature] :
        # searched_name = parent
        main_feature = self.get_main_feature()
        if parent_obj == None:
            parent_obj = main_feature
        
        children = []
        for feature in super().features:
            if feature.is_valid() and feature.name == feature_name:
                if len(feature.dict_note) == 0:
                    note_obj = feature.get_qualifier(Constants.QL_NOTE)
                    if note_obj:
                        note_txt = note_obj.value_to_str()
                        (dict_notes, dict_error) = dict_from_note(feature_name, note_txt)
                        feature.dict_note = dict_notes
                    label = feature.get_qualifier(Constants.QL_LABEL).value_to_str()
                    feature.display_name=label

                condition1 = (
                    Constants.NT_ASSOCIATED_ELEMENT in feature.dict_note and
                    feature.dict_note[Constants.NT_ASSOCIATED_ELEMENT] == parent_obj.tn_name
                )
                condition2 = (
                    feature.name==Constants.FT_MOBILE_ELEMENT and 
                    feature.dict_note[Constants.NT_ACCESSION] != main_feature.dict_note[Constants.NT_ACCESSION]
                )
                condition3 = (
                    feature.name==Constants.FT_MOBILE_ELEMENT and 
                    Constants.NT_ACCESSION in feature.dict_note and
                    feature.dict_note[Constants.NT_ACCESSION] != "" and
                    feature.dict_note[Constants.NT_ACCESSION] != None
                )
                
                if condition1 or (condition2 and condition3):
                    if is_child_by_position(parent_obj, feature):
                        children.append(feature)
        return children
    
    def __str__(self) -> str:
        lines = ""
        first_comment = False
        for header in self.header:
            if not first_comment and header.startswith("COMMENT"):
                first_comment = True
                for ref in self.references:
                    lines += str(ref)
            lines += header

        if not first_comment: # if there is no COMMENT section in the header
                              # we print the references after all header lines
            for ref in self.references:
                lines += str(ref)

        lines += f"FEATURES{' '*13}Location/Qualifiers\n"
        for feature in self.features:
            lines += str(feature)
        lines += "ORIGIN\n"
        for seq in self.sequence:
            lines += seq
        lines += "//\n"
        return lines


def is_child_by_position(feature_parent, feature_child):
    is_child = True
    if len(feature_child.fragments) == 0:
        is_child = False
    else:
        (min_par, max_par) = feature_parent.min_max_pos()
        (min_child, max_child) = feature_child.min_max_pos()    
        if min_child < min_par or max_child > max_par:
            is_child = False
    
    return is_child

def get_fragments(value):
    value = value.replace(" ", "")
    list_fragments = []
    # complement(8781..8818)
    match = re.search("^complement\((\d+)\.\.(\d+)\)$", value)
    if match != None:
        start = int(match.group(1))
        end = int(match.group(2))
        frag = LocationFragment(start, end, "-")
        # fragment = {"start": int(match.group(1)), "end": int(match.group(2)), "strand":"-"}
        list_fragments.append(frag)
    else:
        match = re.search("^(\d+)\.\.(\d+)$", value)
        if match != None:
            start = int(match.group(1))
            end = int(match.group(2))
            frag = LocationFragment(start, end, "+")
            # fragment = {"start": int(match.group(1)), "end": int(match.group(2)), "strand":"+"}
            list_fragments.append(frag)
        else:
            list_fragments = iterate_fragments(value)

    return list_fragments


def iterate_fragments(value):
    list_fragments = []
    match = re.search("^join\((\d+\.\.\d+(,\d+\.\.\d+)*)\)$", value)
    if match != None:
        values = match.group(1)
        parts = values.split(",")
        for part in parts:
            match = re.search("^(\d+)\.\.(\d+)$", part)
            if match != None:
                frag = LocationFragment(int(match.group(1)), int(match.group(2)), "+")
                list_fragments.append(frag)
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
                    frag = LocationFragment(
                        int(match.group(1)), int(match.group(2)), "-"
                    )
                    list_fragments.append(frag)
                else:
                    print("COMPLEMENT ERROROEOROEOR")
    return list_fragments

# qualifier value formatted from a dict
def qvalue_from_dict(feature):
    dict_note = feature.dict_note
    note_keys = Constants.NOTE_FIELDS[feature.name].copy()

    if feature.name == Constants.FT_MOBILE_ELEMENT:
        host = dict_note[Constants.NT_HOST_ORGANISM]
        for host_key in Constants.HOST_FIELDS:
            host = f'{host}||{host_key}={dict_note[host_key]}'
        dict_note[Constants.NT_HOST_ORGANISM] = host

    qvalue = [] # return lines
    len_line = 59 # 21 spaces and 59 characters
    key = note_keys.pop(0)
    current_line = f'/note="{key} = {dict_note[key]}'
    if len(current_line) <= len_line:
        # idx = 1
        note = ""
        while(note_keys):
            key = note_keys.pop(0)
            note = f';{key} = {dict_note[key]}'
            if len(current_line) + len(note) <= len_line:
                current_line = current_line+note
            else:
                note = f';{key} = '
                if len(current_line) + len(note) <= len_line:
                    current_line = current_line+note
                    note = dict_note[key].strip()
                else:
                    qvalue.append(current_line)
                    current_line = ""
                    note = f';{key} = {dict_note[key].strip()}'
                    # 
                # divide value
                split_words = re.findall(r"\w+|[^\w\s]+", note, re.UNICODE)
                # print(split_words)
                while(split_words):
                    word = split_words.pop(0)
                    if word.isalpha() or word.isnumeric():
                        word = ' '+word
                    current_line = current_line.strip()
                    if len(current_line) + len(word) < len_line:
                        current_line = current_line+ word
                    else:
                        split_words.insert(0, word)
                        qvalue.append(current_line)
                        current_line = ""
        qvalue.append(f"{current_line}\"")
        qvalue[0] = qvalue[0].replace('/note=', "")
    else:
        print("Será que acontece alguma vez? Vamos testar")
    return qvalue
    

def dict_from_note(feature, note):
    note = note.strip()
    note = note.strip('"')

    list_note = note.split(";")
    dict_note = {}
    dict_error = {}

    if feature not in Constants.NOTE_FIELDS:
        dict_error[Constants.ERROR_FEATURE_ND] = note
        return (dict_note, dict_error)

    last_key = ""
    for note in list_note:
        note = note.strip()
        list_value = re.split("\s*=\s*", note)
        # if there is no equal sign in this piece of note
        # probably we have semicolon in the middle of other information
        # or we have a note key without value
        if len(list_value) == 1:
            if last_key == Constants.NT_OTHER_INFORMATION:
                dict_note[Constants.NT_OTHER_INFORMATION] = (
                    dict_note[Constants.NT_OTHER_INFORMATION] + " " + note
                )
            else:
                if Constants.ERROR_SINGLE in dict_error:
                    dict_error[Constants.ERROR_SINGLE].append(note)
                else:
                    dict_error[Constants.ERROR_SINGLE] = [note]
        else:
            if list_value[0] in Constants.SYNONYMS:
                list_value[0] = Constants.SYNONYMS[list_value[0]]
            if list_value[0] in Constants.NOTE_FIELDS[feature]:
                dict_note[list_value[0]] = "=".join(list_value[1:])
            else:
                # field not found
                if Constants.ERROR_FIELD_NOT_FOUND in dict_error:
                    if list_value[0] not in dict_error[Constants.ERROR_FIELD_NOT_FOUND]:
                        dict_error[Constants.ERROR_FIELD_NOT_FOUND].append(
                            list_value[0]
                        )
                else:
                    dict_error[Constants.ERROR_FIELD_NOT_FOUND] = [list_value[0]]

    if Constants.NT_HOST_ORGANISM in dict_note:
        org_values = re.split("\|+", dict_note[Constants.NT_HOST_ORGANISM])
        dict_note[Constants.NT_HOST_ORGANISM] = org_values[0]

        for org_value in org_values[1:]:
            values = re.split("\s*=\s*", org_value)
            if values[0] in Constants.HOST_SYNONYMS:
                values[0] = Constants.HOST_SYNONYMS[values[0]]

            if values[0] in Constants.HOST_FIELDS:
                if len(values) > 1:
                    dict_note[values[0]] = values[1]
                else:
                    dict_note[values[0]] = ""
            else:
                if Constants.ERROR_FIELD_NOT_FOUND in dict_error:
                    if values[0] not in dict_error[Constants.ERROR_FIELD_NOT_FOUND]:
                        dict_error[Constants.ERROR_FIELD_NOT_FOUND].append(values[0])
                else:
                    dict_error[Constants.ERROR_FIELD_NOT_FOUND] = [values[0]]

    for default_nt in Constants.NOTE_FIELDS[feature]:
        if default_nt not in dict_note:
            dict_note[default_nt] = None
            dict_error[Constants.ERROR_NT_FIELD_MISSING]=default_nt
    if feature == Constants.FT_MISC_FEATURE:
        for default_ht in Constants.HOST_FIELDS:
            if default_ht not in dict_note:
                dict_note[default_ht] = None
                dict_error[Constants.ERROR_HT_FIELD_MISSING]=default_ht
    return (dict_note, dict_error)


def feature_by_name(list_features, type, name):
    return_feature = None
    for feature in list_features:
        # note = feature.get_qualifier(Constants.QL_NOTE)
        # (dict, error) = dict_from_note(type, note.value_to_str())
        if type == Constants.FT_REPEAT_REGION or type == Constants.FT_MISC_FEATURE:
            if feature.dict_note[Constants.NT_NAME] == name:
                return_feature = feature
                break
        elif type == Constants.FT_CDS:
            gene = feature.get_qualifier(Constants.QL_GENE).value_to_str().strip('"')
            if gene == name:
                return_feature = feature
                break
    return return_feature


def update_note(feature, keys, values):
    if type(keys) is not list:
        keys = [keys]
        values = [values]

    note = feature.get_qualifier(Constants.QL_NOTE)
    # (dict, error) = dict_from_note(feature.name, note.value_to_str())
    for idx in range(0, len(keys)):
        feature.dict_note[keys[idx]] = values[idx]
    # TODO: throw an error in case error is not empty
    note_value = qvalue_from_dict(feature)
    note.value = note_value

def note_from_dict(feature, dict):
    note_keys = Constants.NOTE_FIELDS[feature]
    key = note_keys[0]
    if key in dict:
        note = f'"{key} = {dict[key]}'
    else:
        note = f'"{key} = '
    for key in note_keys[1:]:
        if key in dict:
            note += f"; {key} = {dict[key]}"
        else:
            note += f"; {key} = "
    note += '"'
    return note

# this function receives a path to a genbank file
# and return a TnGenbank object
def get_genbank_object(gb_path):
    genbank = TnGenbank()
    feature = None
    line_number = 1
    references = []
    last_key = ""
    with open(gb_path, "r", encoding="utf-8") as reader:
        line = reader.readline()
        while line:
            # the header are all lines before the tag FEATURES
            while not line.startswith("FEATURES"):
                # it starts with REFERENCE
                match = re.search("^REFERENCE\s+(\d+)\s+\(bases (\d+) to (\d+)\)\s*$", line)
                if match != None:
                    refNumber=int(match.group(1))
                    seqStart=int(match.group(2))
                    seqEnd=int(match.group(3))
                    reference = TnReference(refNumber, seqStart, seqEnd)
                    line = reader.readline()
                    # genbank.header.append(line)
                    line_number += 1
                    while not line.startswith(("REFERENCE","COMMENT","FEATURES")):
                        match = re.search("^\s{2}(\w+)\s+(.+)$", line)
                        if match:
                            last_key = match.group(1)
                            array_ref = reference.__getattribute__(last_key.lower())
                            array_ref.append(match.group(2))
                            if last_key not in ["AUTHORS","TITLE", "JOURNAL", "PUBMED"]:
                                print(f"Warning: {last_key} is not a valid key for REFERENCE block. Line {line_number}")
                        else:
                            value = line.strip('\n')
                            value = value[12:]
                            array_ref = reference.__getattribute__(last_key.lower())
                            array_ref.append(value)
                            # reference.__setattr__(last_key.lower(), new_value)
                        line = reader.readline()
                        line_number += 1
                        if line.startswith(("COMMENT")):
                            genbank.header.append(line)
                    genbank.references.append(reference)
                else:
                    if not line.startswith(("FEATURES", "REFERENCE")):
                        genbank.header.append(line)
                    line = reader.readline()
                    line_number += 1
                    # genbank.header.append(line)
                    
            # when the loop above exits, the line will be the line with
            # the tag: 'FEATURES             Location/Qualifiers'
            line = reader.readline()
            line_number += 1
            while not line.startswith("ORIGIN"):
                match = re.search("^\s*[xX]+$", line)
                if match == None:
                    match = re.search("^\s{5}(\S+)\s+(.+)$", line)
                    if match != None:
                        feature = TnFeature()
                        feature.line_number = line_number
                        feature.name = match.group(1)
                        feature.fragments_text = match.group(2)
                        list_fragments = get_fragments(feature.fragments_text)
                        feature.fragments = list_fragments
                        genbank.features.append(feature)
                    else:  # qualifiers
                        if line.strip() != "":
                            match = re.search("^\s{21}\/(\w+)(=?)(.*)$", line)
                            last_feature = genbank.features[-1]
                            if match != None:  # qualifier descriptor
                                qualifier_name = match.group(1)
                                value = match.group(3)
                                q = Qualifier()
                                q.line_number = line_number
                                q.key = qualifier_name
                                q.value.append(value)
                                last_feature.qualifiers.append(q)
                            else:  # complementary line of the qualifier
                                last_qualifier = last_feature.qualifiers[-1]
                                line = line.lstrip()
                                line = line.strip("\n")
                                if line != "":
                                    if line == '"':
                                        last_qualifier.value[-1] = last_qualifier.value[-1] + '"'
                                        # last_qualifier.value.append(line)
                                    else:
                                        last_qualifier.value.append(line)
                line = reader.readline()
                line_number += 1
            line = reader.readline()
            line_number += 1
            while not line.startswith("//"):
                genbank.sequence.append(line)
                line = reader.readline()
                line_number += 1
            break
    return genbank


def gb_int(value):
    int_value = None
    if value and value.lower() == "yes":
        int_value = 1
    elif value and value.lower() == "no":
        int_value = 0
    return int_value
