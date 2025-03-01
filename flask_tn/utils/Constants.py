# Genbank NOTE descriptors
TNC_SINGLE='tnc_single'

ERROR_FEATURE_ND='feature_nd'
ERROR_SINGLE='error_single'
ERROR_FIELD_NOT_FOUND='field_not_found'
ERROR_NT_FIELD_MISSING='note_field_missing'
ERROR_HT_FIELD_MISSING='host_field_missing'

FT_MOBILE_ELEMENT="mobile_element"
FT_REPEAT_REGION="repeat_region"
FT_CDS="CDS"
FT_MISC_FEATURE="misc_feature"

QL_MOBILE_ELEMENT_TYPE='mobile_element_type'
QL_LABEL='label'
QL_NOTE='note'
QL_GENE='gene'
QL_TRANSLATION='translation'
QL_FUNCTION='function'
QL_PRODUCT='product'
QL_CODON_START='codon_start'
QL_TRANSL_TABLE='transl_table'


NT_ACCESSION="Accession"
NT_FAMILY="Family"
NT_GROUP="Group"
NT_SYNONYMS="Synonyms"
NT_PARTIAL="Partial"
NT_TRANSPOSITION="Transposition"
NT_OTHER_INFORMATION="OtherInformation"
NT_HOST_ORGANISM="Host:Organism"
NT_CAPTURE="Capture"
NT_ASSOCIATED_ELEMENT="AssociatedElement"
NT_LIBRARY_NAME="LibraryName"
NT_NAME="Name"
NT_CLASS="Class"
NT_SUBCLASS="Subclass"
NT_SEQUENCE_FAMILY="SequenceFamily"
NT_CHEMISTRY="Chemistry"
NT_TARGET="Target"

HT_TAXONOMY="Taxonomy"
HT_BAC_GROUP="BacGroup"
HT_MOLECULAR_SOURCE="MolecularSource"
HT_REGION="Region"
HT_COUNTRY="Country"
HT_OTHER_LOC_INFO="OtherLocInfo"
HT_DATE_IDENTIFIED="DateIdentified"
HT_FIRST="First"

HOST_FIELDS = [
    HT_TAXONOMY, HT_BAC_GROUP, HT_MOLECULAR_SOURCE,HT_REGION,
    HT_COUNTRY, HT_OTHER_LOC_INFO, HT_DATE_IDENTIFIED, HT_FIRST
]

NOTE_FIELDS={
    FT_MOBILE_ELEMENT: [
        NT_ACCESSION, NT_FAMILY, NT_GROUP, NT_SYNONYMS, NT_PARTIAL,
        NT_TRANSPOSITION, NT_OTHER_INFORMATION, NT_HOST_ORGANISM, NT_CAPTURE
    ],
    FT_REPEAT_REGION: [
        NT_NAME, NT_ASSOCIATED_ELEMENT, NT_LIBRARY_NAME, NT_OTHER_INFORMATION,
        NT_CAPTURE
    ],
    FT_CDS: [
        NT_NAME, NT_ASSOCIATED_ELEMENT, NT_CLASS, NT_SUBCLASS, NT_SEQUENCE_FAMILY,
        NT_CHEMISTRY, NT_TARGET, NT_LIBRARY_NAME, NT_OTHER_INFORMATION, NT_CAPTURE
    ],
    FT_MISC_FEATURE: [
        NT_NAME, NT_ASSOCIATED_ELEMENT, NT_LIBRARY_NAME, NT_OTHER_INFORMATION,
        # NT_CLASS, NT_SUBCLASS, NT_CHEMISTRY, NT_TARGET,
        NT_CAPTURE
    ]
}

BOOLEAN_FIELDS = [NT_PARTIAL, NT_TRANSPOSITION, NT_CAPTURE, HT_FIRST]

DB_FIELDS = {
    NT_ACCESSION: "accession", NT_FAMILY: "family", NT_GROUP: "group",
    NT_SYNONYMS: "synonyms", NT_PARTIAL: "partial",NT_TRANSPOSITION: "transposition",
    NT_OTHER_INFORMATION: "comment", NT_HOST_ORGANISM: "organism", NT_CAPTURE: "capture",
    HT_TAXONOMY: "taxonomy", HT_BAC_GROUP: "bacteria_group",
    HT_MOLECULAR_SOURCE: "molecular_source",HT_REGION: "region",
    HT_COUNTRY: "country", HT_OTHER_LOC_INFO: "other_loc",
    HT_DATE_IDENTIFIED: "date", HT_FIRST: "first_isolate"
}
SYNONYMS={
    "Other Information": NT_OTHER_INFORMATION,
    "OtherInformaton": NT_OTHER_INFORMATION,
    "Otherinformation": NT_OTHER_INFORMATION,
    "Cpature": NT_CAPTURE,
    "Synonym": NT_SYNONYMS,
    "Synonmy": NT_SYNONYMS,
    "partial": NT_PARTIAL,
    "Transpositon": NT_TRANSPOSITION,
    "Associated Element": NT_ASSOCIATED_ELEMENT,
    "Host: Organism": NT_HOST_ORGANISM,
    "Hosts: Hosts: Organism": NT_HOST_ORGANISM,
    "Hosts:Hosts: Organism": NT_HOST_ORGANISM,
    "Hosts:Organism": NT_HOST_ORGANISM,
    "Hosts: Organism": NT_HOST_ORGANISM,
}

HOST_FIELDS = [
    HT_TAXONOMY, HT_BAC_GROUP, HT_MOLECULAR_SOURCE, HT_REGION, HT_COUNTRY, 
    HT_OTHER_LOC_INFO, HT_DATE_IDENTIFIED, HT_FIRST
]

HOST_SYNONYMS = {
    "Host:Taxonomy": HT_TAXONOMY,
    "Host:BacGroup": HT_BAC_GROUP,
    "Host:MolecularSource": HT_MOLECULAR_SOURCE,
    "Molecular Source": HT_MOLECULAR_SOURCE,
    "Host:Region": HT_REGION,
    "Host:Country":HT_COUNTRY,
    "Host:OtherLocInfo": HT_OTHER_LOC_INFO,
    "Host:DateIdentified": HT_DATE_IDENTIFIED,
    "Host:First": HT_FIRST
}

# Upload categories
UPLOAD_GENBANK="genbank"
UPLOAD_IMAGE="image"
UPLOAD_SNAPGENE="snapgene"
UPLOAD_QC="qc" # all qc files
UPLOAD_CUSTOM="custom" # snapgene library custom.ftrs
UPLOAD_FAVORITE="favorites" # snapgene library favorites
UPLOAD_CATEGORIES=[
    UPLOAD_GENBANK, UPLOAD_IMAGE, UPLOAD_SNAPGENE,
    UPLOAD_QC, UPLOAD_CUSTOM, UPLOAD_FAVORITE
]