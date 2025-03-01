from abc import abstractmethod
import os

ACCESSORY_GENE_FILE = "tncentral_accessory_gene_annotation.txt"
TA_GENE_FILE = "tncentral_TA_gene_annotation.txt"
TRANSPOSASE_FILE = "tncentral_transposase_annotation.txt"
CARD_CATEGORIES_FILE = "aro_categories.tsv"
CARD_INDEX_FILE = "aro_index.tsv"
METAL_TARGETS_FILE = "metal_targets.txt"


class TnBaseAnnotation:
    def __init__(self, lineNumber: int):
        self.lineNumber = lineNumber
    
    @property
    def lineNumber(self) -> int:
        return self.__lineNumber

    @lineNumber.setter
    def lineNumber(self, value):
        self.__lineNumber = value

    @classmethod
    @abstractmethod
    def from_line(cls, lineNumber: int, line: str) -> "TnBaseAnnotation":
        pass

    @abstractmethod
    def search(self) -> bool:
        pass

    @abstractmethod
    def to_datatable(self) -> dict:
        pass


class TnAccessoryBase(TnBaseAnnotation):
    def __init__(
        self,
        lineNumber: int,
        geneClass: str,
        gene: str,
        product: str,
        sequenceFamily: str,
    ):
        super().__init__(lineNumber)
        self.geneClass = geneClass
        self.gene = gene
        self.product = product
        self.sequenceFamily = sequenceFamily


    @property
    def geneClass(self) -> str:
        return self.__geneClass

    @geneClass.setter
    def geneClass(self, value):
        self.__geneClass = value

    @property
    def gene(self) -> str:
        return self.__gene

    @gene.setter
    def gene(self, value):
        self.__gene = value

    @property
    def product(self) -> str:
        return self.__product

    @product.setter
    def product(self, value):
        self.__product = value

    @property
    def sequenceFamily(self) -> str:
        return self.__sequenceFamily

    @sequenceFamily.setter
    def sequenceFamily(self, value):
        self.__sequenceFamily = value


class TnAccessoryGene(TnAccessoryBase):
    def __init__(
        self,
        lineNumber: int,
        geneClass: str,
        subClass: str,
        gene: str,
        product: str,
        sequenceFamily: str,
        chemistry: str,
    ):
        super().__init__(lineNumber, geneClass, gene, product, sequenceFamily)
        # self.geneClass = geneClass
        self.subClass = subClass
        # self.gene = gene
        # self.product = product
        # self.sequenceFamily = sequenceFamily
        self.chemistry = chemistry

    def search(self, text) -> bool:
        if self.subClass.lower().find(text.lower()) != -1:
            return True
        if self.gene.lower().find(text.lower()) != -1:
            return True
        if self.product.lower().find(text.lower()) != -1:
            return True
        if self.sequenceFamily.lower().find(text.lower()) != -1:
            return True
        if self.chemistry.lower().find(text.lower()) != -1:
            return True
        return False

    def to_datatable(self) -> dict:
        """Return object data in easily serializable format"""
        return {
            "line_number": self.lineNumber,
            "gene_class": self.geneClass,
            "subclass": self.subClass,
            "gene": self.gene,
            "product": self.product,
            "sequence_family": self.sequenceFamily,
            "chemistry": self.chemistry,
            "buttons": "",
        }

    @classmethod
    def from_line(cls, lineNumber: int, line: str) -> "TnAccessoryGene":
        line = line.strip("\n")
        cols = line.split("\t")
        return cls(
            lineNumber=lineNumber,
            geneClass=cols[0],
            subClass=cols[1],
            gene=cols[2],
            product=cols[3],
            sequenceFamily=cols[4],
            chemistry=cols[5],
        )

    @property
    def subClass(self) -> str:
        return self.__subClass

    @subClass.setter
    def subClass(self, value):
        self.__subClass = value

    @property
    def chemistry(self) -> str:
        return self.__chemistry

    @chemistry.setter
    def chemistry(self, value):
        self.__chemistry = value


class TnTaGene(TnAccessoryBase):
    def __init__(
        self,
        lineNumber: int,
        geneClass: str,
        subClass: str,
        gene: str,
        product: str,
        sequenceFamily: str,
        target: str,
    ):
        super().__init__(lineNumber, geneClass, gene, product, sequenceFamily)
        # self.geneClass = geneClass
        self.subClass = subClass
        # self.gene = gene
        # self.product = product
        # self.sequenceFamily = sequenceFamily
        self.target = target

    def search(self, text) -> bool:
        if self.subClass.lower().find(text.lower()) != -1:
            return True
        if self.gene.lower().find(text.lower()) != -1:
            return True
        if self.product.lower().find(text.lower()) != -1:
            return True
        if self.sequenceFamily.lower().find(text.lower()) != -1:
            return True
        if self.target.lower().find(text.lower()) != -1:
            return True
        return False

    def to_datatable(self) -> dict:
        """Return object data in easily serializable format"""
        return {
            "line_number": self.lineNumber,
            "gene_class": self.geneClass,
            "subclass": self.subClass,
            "gene": self.gene,
            "product": self.product,
            "sequence_family": self.sequenceFamily,
            "target": self.target,
            "buttons": "",
        }

    @classmethod
    def from_line(cls, lineNumber: int, line: str) -> "TnTaGene":
        line = line.strip("\n")
        cols = line.split("\t")
        return cls(
            lineNumber=lineNumber,
            geneClass=cols[0],
            subClass=cols[1],
            gene=cols[2],
            product=cols[3],
            sequenceFamily=cols[4],
            target=cols[5],
        )

    @property
    def subClass(self) -> str:
        return self.__subClass

    @subClass.setter
    def subClass(self, value):
        self.__subClass = value

    @property
    def target(self) -> str:
        return self.__target

    @target.setter
    def target(self, value):
        self.__target = value

class TnTransposase(TnAccessoryBase):
    def __init__(
        self,
        lineNumber: int,
        geneClass: str,
        gene: str,
        product: str,
        sequenceFamily: str
    ):
        super().__init__(lineNumber, geneClass, gene, product, sequenceFamily)
        

    def search(self, text) -> bool:
        if self.gene.lower().find(text.lower()) != -1:
            return True
        if self.product.lower().find(text.lower()) != -1:
            return True
        if self.sequenceFamily.lower().find(text.lower()) != -1:
            return True
        return False

    def to_datatable(self) -> dict:
        """Return object data in easily serializable format"""
        return {
            "line_number": self.lineNumber,
            "gene_class": self.geneClass,
            "gene": self.gene,
            "product": self.product,
            "sequence_family": self.sequenceFamily,
            "buttons": "",
        }

    @classmethod
    def from_line(cls, lineNumber: int, line: str) -> "TnTransposase":
        line = line.strip("\n")
        cols = line.split("\t")
        return cls(
            lineNumber=lineNumber,
            geneClass=cols[0],
            gene=cols[1],
            product=cols[2],
            sequenceFamily=cols[3]
        )

class CARD_Category(TnBaseAnnotation):
    def __init__(
        self,
        lineNumber: int,
        category: str,
        accession: str,
        name: str
    ):
        super().__init__(lineNumber)
        self.category = category
        self.accession = accession
        self.name = name

    def search(self, text) -> bool:
        if self.category.lower().find(text.lower()) != -1:
            return True
        if self.accession.lower().find(text.lower()) != -1:
            return True
        if self.name.lower().find(text.lower()) != -1:
            return True
        return False

    def to_datatable(self) -> dict:
        """Return object data in easily serializable format"""
        return {
            "line_number": self.lineNumber,
            "category": self.category,
            "accession": self.accession,
            "name": self.name,
            "buttons": "",
        }

    @classmethod
    def from_line(cls, lineNumber: int, line: str) -> "CARD_Category":
        line = line.strip("\n")
        cols = line.split("\t")
        return cls(
            lineNumber=lineNumber,
            category=cols[0],
            accession=cols[1],
            name=cols[2]
        )

class CARD_Index(TnBaseAnnotation):
    def __init__(
        self,
        lineNumber: int,
        aroAccession: str,
        cvTermId: int,
        modelSeqId: int,
        modelId: int,
        modelName: str,
        aroName: str,
        proteinAccession: str,
        dnaAccession: str,
        amrGeneFamily: str,
        drugClass: str,
        resistanceMecanism: str,
        cardShortName: str
    ):
        super().__init__(lineNumber)
        self.aroAccession = aroAccession
        self.cvTermId = cvTermId
        self.modelSeqId = modelSeqId
        self.modelId = modelId
        self.modelName = modelName
        self.aroName = aroName
        self.proteinAccession = proteinAccession
        self.dnaAccession = dnaAccession
        self.amrGeneFamily = amrGeneFamily
        self.drugClass = drugClass
        self.resistanceMecanism = resistanceMecanism
        self.cardShortName = cardShortName

    def search(self, text) -> bool:
        if self.aroAccession.lower().find(text.lower()) != -1:
            return True
        if self.cvTermId.lower().find(text.lower()) != -1:
            return True
        if self.modelSeqId.lower().find(text.lower()) != -1:
            return True
        if self.modelId.lower().find(text.lower()) != -1:
            return True
        if self.modelName.lower().find(text.lower()) != -1:
            return True
        if self.aroName.lower().find(text.lower()) != -1:
            return True
        if self.proteinAccession.lower().find(text.lower()) != -1:
            return True
        if self.dnaAccession.lower().find(text.lower()) != -1:
            return True
        if self.amrGeneFamily.lower().find(text.lower()) != -1:
            return True
        if self.drugClass.lower().find(text.lower()) != -1:
            return True
        if self.resistanceMecanism.lower().find(text.lower()) != -1:
            return True
        if self.cardShortName.lower().find(text.lower()) != -1:
            return True
        return False

    def to_datatable(self) -> dict:
        """Return object data in easily serializable format"""
        return {
            "line_number": self.lineNumber,
            "aro_accession": self.aroAccession,
            "cv_term_id": self.cvTermId,
            "model_seq_id": self.modelSeqId,
            "model_id": self.modelId,
            "model_name": self.modelName,
            "aro_name": self.aroName,
            "protein_accession": self.proteinAccession,
            "dna_accession": self.dnaAccession,
            "amr_family": self.amrGeneFamily,
            "drug_class": self.drugClass,
            "resistance_mechanism": self.resistanceMecanism,
            "card_short_name": self.cardShortName,
            "buttons": "",
        }

    @classmethod
    def from_line(cls, lineNumber: int, line: str) -> "CARD_Index":
        line = line.strip("\n")
        cols = line.split("\t")
        return cls(
            lineNumber=lineNumber,
            aroAccession=cols[0],
            cvTermId=cols[1],
            modelSeqId=cols[2],
            modelId=cols[3],
            modelName=cols[4],
            aroName=cols[5],
            proteinAccession=cols[6],
            dnaAccession=cols[7],
            amrGeneFamily=cols[8],
            drugClass=cols[9],
            resistanceMecanism=cols[10],
            cardShortName=cols[11]
        )

class TnMetalTargets(TnBaseAnnotation):
    def __init__(
        self,
        lineNumber: int,
        metalName: str
    ):
        super().__init__(lineNumber)
        self.metalName = metalName

    def search(self, text) -> bool:
        if self.metalName.lower().find(text.lower()) != -1:
            return True
        return False

    def to_datatable(self) -> dict:
        """Return object data in easily serializable format"""
        return {
            "line_number": self.lineNumber,
            "metal_name": self.metalName,
            "buttons": "",
        }

    @classmethod
    def from_line(cls, lineNumber: int, line: str) -> "TnMetalTargets":
        line = line.strip("\n")
        cols = line.split("\t")
        return cls(
            lineNumber=lineNumber,
            metalName=cols[0]
        )


def read_qc_file(filepath):
    list_obj = []
    list_obj = get_obj_from_file(filepath)
    return list_obj


def get_obj_from_file(filepath):
    basename = os.path.basename(filepath)
    list_obj = []
    if basename == ACCESSORY_GENE_FILE:
        list_obj = read_accessory_gene(filepath)
    elif basename == TA_GENE_FILE:
        list_obj = read_ta_gene(filepath)
    elif basename == TRANSPOSASE_FILE:
        list_obj = read_transposase(filepath)
    elif basename == CARD_CATEGORIES_FILE:
        list_obj = read_card_category(filepath)
    elif basename == CARD_INDEX_FILE:
        list_obj = read_card_index(filepath)
    elif basename == METAL_TARGETS_FILE:
        list_obj = read_metal_targets(filepath)
    return list_obj

def read_accessory_gene(filepath):
    list_obj = []
    with open(filepath) as reader:
        first_line = reader.readline()  # header
        for idx, line in enumerate(reader):
            tn_acc_gene = TnAccessoryGene.from_line(idx + 1, line)
            list_obj.append(tn_acc_gene)
    return list_obj

def read_ta_gene(filepath):
    list_obj = []
    with open(filepath) as reader:
        first_line = reader.readline()  # header
        for idx, line in enumerate(reader):
            ta_gene = TnTaGene.from_line(idx + 1, line)
            list_obj.append(ta_gene)
    return list_obj

def read_transposase(filepath):
    list_obj = []
    with open(filepath) as reader:
        first_line = reader.readline()  # header
        for idx, line in enumerate(reader):
            trans_obj = TnTransposase.from_line(idx + 1, line)
            list_obj.append(trans_obj)
    return list_obj

def read_card_category(filepath):
    list_obj = []
    with open(filepath) as reader:
        first_line = reader.readline()  # header
        for idx, line in enumerate(reader):
            card_cat_obj = CARD_Category.from_line(idx + 1, line)
            list_obj.append(card_cat_obj)
    return list_obj

def read_card_index(filepath):
    list_obj = []
    with open(filepath) as reader:
        first_line = reader.readline()  # header
        for idx, line in enumerate(reader):
            card_index_obj = CARD_Index.from_line(idx + 1, line)
            list_obj.append(card_index_obj)
    return list_obj

def read_metal_targets(filepath):
    list_obj = []
    with open(filepath) as reader:
        for idx, line in enumerate(reader):
            metal_obj = TnMetalTargets.from_line(idx + 1, line)
            list_obj.append(metal_obj)
    return list_obj

def update_line_in_file(filepath, line_text, line_number=-1):
    with open(filepath) as file:
        data = file.readlines()

    if line_number == -1:
        line_text = line_text.rstrip("\n")
        data.append(line_text)
    else:
        data[line_number] = line_text

    with open(filepath, "w") as file:
        file.writelines(data)


def delete_line_in_file(filepath, line_number):
    with open(filepath) as file:
        data = file.readlines()

    del data[line_number]

    with open(filepath, "w") as file:
        file.writelines(data)


def validate_file(filepath):
    basename = os.path.basename(filepath)
    list_errors = []
    if basename == ACCESSORY_GENE_FILE:
        list_errors = validate_accessory_or_ta(filepath, "accessory gene")
    elif basename == TA_GENE_FILE:
        list_errors = validate_accessory_or_ta(filepath, "passenger gene")
    elif basename == TRANSPOSASE_FILE:
        list_errors = validate_transposase(filepath)
    elif basename == CARD_CATEGORIES_FILE:
        list_errors = validate_card_category(filepath)
    elif basename == CARD_INDEX_FILE:
        list_errors = validate_card_index(filepath)
    elif basename == METAL_TARGETS_FILE:
        list_errors = validate_metal_targets(filepath)
    

    return list_errors


def validate_accessory_or_ta(filepath, first_col):
    # Class   Subclass        Gene    Product SequenceFamily  Chemistry
    list_errors = []
    with open(filepath) as reader:
        first_line = reader.readline()
        first_cols = first_line.split("\t")
        if len(first_cols) != 6:
            list_errors.append(
                {
                    "line": 1,
                    "error": f"Invalid number of columns. Expected: 6; Found: {len(first_cols)}",
                }
            )
        if first_cols[0] != "Class" or first_cols[1] != "Subclass":
            list_errors.append({"line": 1, "error": "File header not found"})
        for idx, line in enumerate(reader):
            line = line.rstrip("\n")
            cols = line.split("\t")
            if len(cols) != 6:
                list_errors.append(
                    {
                        "line": idx + 2,
                        "error": f"Invalid number of columns. Expected: 6; Found: {len(cols)}",
                    }
                )
            if cols[0].lower() != first_col:
                list_errors.append(
                    {"line": idx + 2, "error": "It is not an accessory gene."}
                )
    return list_errors

def validate_transposase(filepath):
    # Class   Subclass        Gene    Product SequenceFamily  Chemistry
    list_errors = []
    with open(filepath) as reader:
        first_line = reader.readline()
        first_cols = first_line.split("\t")
        if len(first_cols) != 4:
            list_errors.append(
                {
                    "line": 1,
                    "error": f"Invalid number of columns. Expected: 4; Found: {len(first_cols)}",
                }
            )
        if first_cols[0] != "Class" or first_cols[1] != "Gene":
            list_errors.append({"line": 1, "error": "File header not found"})
        for idx, line in enumerate(reader):
            line = line.rstrip("\n")
            cols = line.split("\t")
            if len(cols) != 4:
                list_errors.append(
                    {
                        "line": idx + 2,
                        "error": f"Invalid number of columns. Expected: 4; Found: {len(cols)}",
                    }
                )
            if cols[0].lower() != "transposase":
                list_errors.append(
                    {"line": idx + 2, "error": "It is not a transposase."}
                )
    return list_errors

def validate_card_category(filepath):
    # ARO Category	ARO Accession	ARO Name
    list_errors = []
    with open(filepath) as reader:
        first_line = reader.readline()
        first_cols = first_line.split("\t")
        if len(first_cols) != 3:
            list_errors.append(
                {
                    "line": 1,
                    "error": f"Invalid number of columns. Expected: 3; Found: {len(first_cols)}",
                }
            )
        if first_cols[0] != "ARO Category" or first_cols[1] != "ARO Accession":
            list_errors.append({"line": 1, "error": "File header not found"})
        for idx, line in enumerate(reader):
            line = line.rstrip("\n")
            cols = line.split("\t")
            if len(cols) != 3:
                list_errors.append(
                    {
                        "line": idx + 2,
                        "error": f"Invalid number of columns. Expected: 3; Found: {len(cols)}",
                    }
                )
    return list_errors

def validate_card_index(filepath):
    # ARO Accession\tCVTERM ID\tModel Sequence ID\tModel ID\tModel Name\t
    # ARO Name\tProtein Accession\tDNA Accession\tAMR Gene Family\tDrug Class\t
    # Resistance Mechanism\tCARD Short Name
    list_errors = []
    with open(filepath) as reader:
        first_line = reader.readline()
        first_cols = first_line.split("\t")
        if len(first_cols) != 12:
            list_errors.append(
                {
                    "line": 1,
                    "error": f"Invalid number of columns. Expected: 12; Found: {len(first_cols)}",
                }
            )
        if first_cols[0] != "ARO Accession" or first_cols[1] != "CVTERM ID":
            list_errors.append({"line": 1, "error": "File header not found"})
        for idx, line in enumerate(reader):
            line = line.rstrip("\n")
            cols = line.split("\t")
            if len(cols) != 12:
                list_errors.append(
                    {
                        "line": idx + 2,
                        "error": f"Invalid number of columns. Expected: 12; Found: {len(cols)}",
                    }
                )
    return list_errors

def validate_metal_targets(filepath):
    # ARO Accession\tCVTERM ID\tModel Sequence ID\tModel ID\tModel Name\t
    # ARO Name\tProtein Accession\tDNA Accession\tAMR Gene Family\tDrug Class\t
    # Resistance Mechanism\tCARD Short Name
    list_errors = []
    with open(filepath) as reader:
        for idx, line in enumerate(reader):
            line = line.rstrip("\n")
            cols = line.split("\t")
            if len(cols) != 1:
                list_errors.append(
                    {
                        "line": idx + 2,
                        "error": f"Invalid number of columns. Expected: 1; Found: {len(cols)}",
                    }
                )
    return list_errors