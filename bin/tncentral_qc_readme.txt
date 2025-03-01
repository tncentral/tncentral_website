TnCentral Quality Control script version tncentral_qc_v13.pl

Accessory files needed (will need to update the script to indicate the correct path to these files):
tncentral_TA_gene_annotation_v4.txt (see line 10)
tncentral_transposase_annotation.txt (see line 45)
tncentral_accessory_gene_annotation_v2.txt (see line 61)
aro_index.tsv (see line 94)
aro_categories.tsv (see line 134)

Changes required before each run:
line 6: update name of output file
line 164: update regular expression for file path

To run:
perl tncentral_qc_v14.pl <PATH TO FOLDER CONTAINING GENBANK FILES>/*

For example:
perl tncentral_qc_v14.pl /Users/karenross/Documents/Bioinformatics/PIR/TnCentral/CurationBatches/35-annotations-2022-03-19/35-GenBank/*
