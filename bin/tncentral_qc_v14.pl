#!/usr/bin/perl
use strict; 
use warnings;
use Bio::SeqIO;

# input: accessory files
# input: input folder
# output: output folder
# my $genbank_files_folder = shift or die "Usage: $0 genbank_folder accessory_folder output_file";
my $genbank_file = shift or die "Usage: $0 genbank_file accessory_folder output_file";
my $accessory_files_folder = shift or die "Usage: $0 genbank_folder accessory_folder output_file";
my $out_name = shift or die "Usage: $0 genbank_folder accessory_folder output_file";

# my $out_name = "qc_out_2022-06-01.txt";
my $out = open_write_file($out_name);

# my $accessory_files_folder = "accessory_files/";
#Read file for checking Toxin/Antitoxin Gene
my $ta_filename = $accessory_files_folder."tncentral_TA_gene_annotation.txt";
my @ta_file = read_file($ta_filename);
fix_line_breaks(\@ta_file);

my %toxin_gene_product;
my %toxin_gene_seq_fam;
my %toxin_gene_target;
my %antitox_gene_product;
my %antitox_gene_seq_fam;

foreach my $line (@ta_file) {
	if ($line =~ /SequenceFamily/) {
		next;
	} else {
		my @line_info = split('\t', $line);
		my $at_type = $line_info[1];
		my $at_gene = $line_info[2];
		my $at_product = $line_info[3];
		my $at_seq_fam = $line_info[4];
		$at_seq_fam =~ s/"//g;
		my $at_target = $line_info[5];
		if ($at_type eq "Toxin") {
			$toxin_gene_product{$at_gene} = $at_product;
			$toxin_gene_seq_fam{$at_gene} = $at_seq_fam;
			$toxin_gene_target{$at_gene} = $at_target;
		}
		
		if ($at_type eq "Antitoxin") {
			$antitox_gene_product{$at_gene} = $at_product;
			$antitox_gene_seq_fam{$at_gene} = $at_seq_fam;
		}
	}
}

#Read file for checking Transposases
my $transposase_filename = $accessory_files_folder."tncentral_transposase_annotation.txt";
my @transposase_file = read_file($transposase_filename);
fix_line_breaks(\@transposase_file);

my %tr_genes;
foreach my $line (@transposase_file) {
	if ($line =~ /SequenceFamily/) {
		next;
	} else {
		my @line_info = split('\t', $line);
		my $tr_gene = $line_info[1];
		$tr_genes{$tr_gene} = 1;
	}
}

#Read file for checking Accessory Genes
my $ag_filename = $accessory_files_folder."tncentral_accessory_gene_annotation.txt";
my @ag_file = read_file($ag_filename);
fix_line_breaks(\@ag_file);

my %ag_gene_product;
my %ag_gene_seq_fam;
my %ag_gene_chem;
my %ag_gene_subclass;
foreach my $line (@ag_file) {
	if ($line =~ /SequenceFamily/) {
		next;
	} else {
		my @line_info = split('\t', $line);
		my $ag_subclass = $line_info[1];
		my $ag_gene = $line_info[2];
		my $ag_product = $line_info[3];
		my $ag_seq_fam = $line_info[4];
		my $ag_chem = $line_info[5];
		$ag_gene_product{$ag_gene} = $ag_product;
		if ($ag_subclass) {
		#Same gene could have more than one subclass and some genes do not have a subclass
			$ag_gene_subclass{$ag_gene} -> {$ag_subclass} = 1;
		}
		#The same gene name can be used for genes in different subclasses. Will assume for
		#now that all genes of that name in the same subclass have the same SequenceFamily
		#and Chemistry
		$ag_gene_seq_fam{$ag_gene} -> {$ag_subclass} = $ag_seq_fam;
		$ag_gene_chem{$ag_gene} -> {$ag_subclass} = $ag_chem;
	}
}


#Get data from CARD for checking ABR genes
# my $card_gene_filename = $accessory_files_folder."aro_categories.tsv";
my $card_gene_filename = $accessory_files_folder."aro_index.tsv";
my @card_gene_file = read_file($card_gene_filename);
fix_line_breaks(\@card_gene_file);

my %gene_aro;
my %gene_mech;
my %gene_fam;
my %gene_target;
foreach my $line (@card_gene_file) {
	if ($line =~ /CVTERM/) {
		next;
	} else {
		my @line_info = split('\t', $line);
		my $gene_name = $line_info[5];
		my $accession = $line_info[0];
		$gene_aro{$gene_name} = $accession;
		
		my $mech = $line_info[10];
		my @mech_array = split(";", $mech);
		foreach my $m (@mech_array) {
			$gene_mech{$gene_name} -> {$m} = 1;
		}
		
		my $fam = $line_info[8];
		my @fam_array = split(";", $fam);
		foreach my $f (@fam_array) {
			$gene_fam{$gene_name} -> {$f} = 1;
		}
		
		my $target = $line_info[9];
		my @target_array = split(";", $target);
		foreach my $t (@target_array) {
			if (!($t eq "N/A")) {
				$gene_target{$gene_name} -> {$t} = 1;
			
			}
		}
	}
}
		
# my $card_cat_filename = $accessory_files_folder."aro_index.tsv";
my $card_cat_filename = $accessory_files_folder."aro_categories.tsv";
my @card_cat_file = read_file($card_cat_filename);
fix_line_breaks(\@card_cat_file);	


my %fam_acc;
my %mech_acc;
my %target_acc;
foreach my $line (@card_cat_file) {
	if ($line =~ /ARO Accession/) {
		next;
	} else {
		my @line_info = split('\t', $line);
		my $cat = $line_info[0];
		my $name = $line_info[2];
		my $accession = $line_info[1];
		if ($cat eq "AMR Gene Family") {
			$fam_acc{$name} = $accession;
		} elsif ($cat eq "Drug Class") {
			$target_acc{$name} = $accession;
		} elsif ($cat eq "Resistance Mechanism") {
			$mech_acc{$name} = $accession;
		} else {
			print "Non-matching category\n";
		}
	}
}

## BEGIN: Added by Francislon
#Read file for heavy metal target
my $metal_filename = $accessory_files_folder."metal_targets.txt";
my @metal_lines = read_file($metal_filename);
fix_line_breaks(\@metal_lines);
my %metal_tar;
foreach my $line (@metal_lines) {
		$metal_tar{lc($line)} = 1;
}
## END: Added by Francislon

# GOTO
# opendir my $dir, $genbank_files_folder or die "Cannot open directory: $!"; # ADDED BY FSO
# my @files = readdir $dir;

# foreach my $file (@files) {
	# $file =~ /\/35-GenBank\/(.*?)\.gb/; # CHANGED BY FSO
	if($genbank_file =~ /^\.{1,2}$/){
		next;	
	}
	$genbank_file =~ /(.*?)\.gb/; # FSO Comment
	my $file_short = $1; # FSO Comment

	#Check the format of the filename
	my $file_te;
	if ($genbank_file =~ /^(.+)\.gb$/) {
		$file_te = $1;
	} else {
		my $message = "Filename format error";
		print $out "NA\t$message\n";
	} 
	my $inseq = Bio::SeqIO->new(-file   => $genbank_file,
                            -format => 'genbank');

	#Check for presence of label field for features that
	#have Capture = yes in the note field.
	my %features = ( 	CDS => 1,
	           			repeat_region => 1, 
    	           		misc_feature => 1,
    	           		mobile_element => 1); 
	
	while (my $seq = $inseq->next_seq) {
  		for my $feat_object ($seq->get_SeqFeatures) {
   			my $ptag = $feat_object->primary_tag;
   			my $note_text;
   			my %all_tags;
   			for my $tag ($feat_object->get_all_tags) {
   				$all_tags{$tag} = 1;
   				#Get the note text
   				if ($tag eq "note") {
   					for my $value ($feat_object->get_tag_values($tag)) {
   						$note_text .= $value;
   					}
   				}
   			}
   			
   			if ($note_text) {
   				#Check whether the note contains Capture = yes
   				if ($note_text =~ /Capture\s*=\s*yes/) {
   					#Check whether the feature is one of the allowed types. If the feature
   					#type is not one of the allowed types, the feature won't be checked for
   					#any other errors; the feature type needs to be fixed first.
   					my $feature_type_error = 0;
   					if (!exists $features{$ptag}) {
   						my $message = "Feature type error";
   						$feature_type_error = 1;
   						print $out "$note_text\t$message\n";
   					}
   					#Capture other entries in the note field
   					my $name;
   					my $element;
   					my $library_name;
   					my $accession;
   					my $class;
   					my $subclass;
   					my $seq_fam;
   					my $chemistry;
   					my $target;
   					
   					#Note: if the Name field is missing or misspelled, this will match to
   					#the "Name" string in LibraryName. This will cause a "Name and Label mismatch"
   					#error to be reported rather than a "Name field missing" error
   					if ($note_text =~ /Name\s*=(.*?);/) {
   						$name = $1;
   						$name = extract_note_field($name);
   					}
   				
   					if ($note_text =~ /AssociatedElement\s*=(.*?);/) {
   						$element = $1;
   						$element = extract_note_field($element);
					}
   				
   					if ($note_text =~ /LibraryName\s*=(.*?);/) {
   						$library_name = $1;
   						$library_name = extract_note_field($library_name);
					}
					
					if ($note_text =~ /Accession\s*=(.*?);/) {
   						$accession = $1;
   						$accession = extract_note_field($accession);
					}
					
					if ($note_text =~ /Class\s*=(.*?);/) {
   						$class = $1;
   						$class = extract_note_field($class);
					}
					
					if ($note_text =~ /Subclass\s*=(.*?);/) {
   						$subclass = $1;
   						$subclass = extract_note_field($subclass);
					}
					
					if ($note_text =~ /SequenceFamily\s*=(.*?);/) {
   						$seq_fam = $1;
   						$seq_fam = extract_note_field($seq_fam);
					}
					
					if ($note_text =~ /Chemistry\s*=(.*?);/) {
   						$chemistry = $1;
   						$chemistry = extract_note_field($chemistry);
					}
					
					if ($note_text =~ /Target\s*=(.*?);/) {
   						$target = $1;
   						$target = extract_note_field($target);
					}
					
   					#Check for the label
   					#field and print an error message if not found. These features will
   					#not be checked for any other errors. The label will need to be fixed
   					#first. If the label is found then check other parts of the feature. Since
   					#we know these features have labels, we can use the label to describe the
   					#feature in the error message.
   					if (exists $features{$ptag}) {
   						if (!exists $all_tags{'label'}) {
   							my $message = "Label field missing";
   							print $out "$note_text\t$message\n";
   					
   						} else {
   							#Get label field text
   							my $label_text;
   							for my $value ($feat_object->get_tag_values('label')) {
   								$label_text .= $value;
   							}
   							#Trim left and right whitespace from label text
   							$label_text =~ s/^\s+|\s+$//g;
   							my $label_name;
   							my $label_element;
   							my $label_format_error = 0;
   							if ($label_text =~ /(.*) \((.*)\)/)  {
   								$label_name = $1;
   								$label_element = $2;
   							} elsif ($ptag eq 'mobile_element') {
   								$label_name = $label_text;
   							} else {
   								my $message = "Label format error";	
   								print $out "$label_text\t$message\n";
   								$label_format_error = 1;
   							}
   						
   							#Check for cases where IRL/IRR/IR are not of type repeat_region and
   							#cases where res sites are not of type misc_feature; make an exception
   							#for the res sites that have IR as part of their name: these should be
   							#type misc_feature
   							if ($feature_type_error == 0) {
   								my $message = "Check feature type";
   								if ($name) {
   									if (($name =~ /IR/) and (!$name =~ /^res_/) and ($ptag ne 'repeat_region')) {
   										print $out "$label_text\t$message\n";
   									}
   							
   									if ((($name =~ /^res$/) or ($name =~ /res_/)) and ($ptag ne 'misc_feature')) {
   										print $out "$label_text\t$message\n";
   									}
   									
   									if (($name =~ /IR/) and ($name =~ /^res_/) and ($ptag ne 'misc_feature')) {
   										print $out "$label_text\t$message\n";
   									}
   								}
   							}
   						
   						
   							#Check the res sites and repeat regions
   							#The same checks are done for both of these types of features
   							if (($ptag eq "misc_feature") or ($ptag eq "repeat_region")) {
   								#Check that the Name and Associated Element fields in note
   								#correspond to the label
   								if ($name) {
   									if ($label_format_error == 0) {
   										if ($name ne $label_name) {
   											my $message = "Label and Name mismatch";
   											print $out "$label_text\t$message\n";
   										}
   									}
   								} else {
   									my $message = "Name field missing";
   									print $out "$label_text\t$message\n";
   								}
   							
   								if ($element) {
   									if ($label_format_error == 0) {
   										if ($element ne $label_element) {
   											my $message = "Label and AssociatedElement mismatch";
   											print $out "$label_text\t$message\n";
   										}
   									}
   								} else {
   									my $message = "AssociatedElement field missing";
   									print $out "$label_text\t$message\n";
   								}
   								
   								#Figure out the sequence length (if it is 6bp or less we
   								#don't save it in the library so don't report it if LibraryName
   								#is missing)
   								my $short_seq = 0;
   								my $feature_seq = $feat_object->seq->seq;
   								if (length $feature_seq <=6) {
   									$short_seq = 1;
   								}
   						
   								#Check that LibraryName is present and is of correct format
   								if ($library_name) {
   									if (!($library_name =~ /(.*) \((.*)\)/)) {
   										my $message = "LibraryName format error";
   										print $out "$label_text\t$message\n";
   									}
   								} else {
   									if ($short_seq == 0) {
   										my $message = "LibraryName missing";
   										print $out "$label_text\t$message\n";
   									}
   								}	
   							}
   							
   							#Check the mobile_element features
   							if ($ptag eq "mobile_element") {
   							#Check that the Accession field is present and in the correct format
   							#and that the first part of the Accession matches the label. If the
   							#label matches the first part of the file name, then assume this is the
   							#main mobile element and check whether the Accession number matches the file name
   							#Note that if there is a problem with the format of the file name, the latter
   							#will not be checked
   								if ($accession) {
   									my $accession_name;
   									if ($accession =~ /^(\S+)-\S+$/) {
   										$accession_name = $1;
   										my $label_name_reformat = $label_name;
   										if ($label_name_reformat =~ /::/) {
   											$label_name_reformat =~ s/::/_/g;
   										}
   										
   										if ($accession_name ne $label_name_reformat) {
   											my $message = "Label and Accession mismatch";
   											print $out "$label_text\t$message\n";
   										}
   										if ($file_te) {
   											if (($file_te eq $label_name) and ($file_short ne $accession)) {
   												my $message = "Accession and filename mismatch";
   												print $out "$label_text\t$message\n";
   											}
   										}	
   										
   									} else {
   										my $message = "Accession formatting error";
   										print $out "$label_text\t$message\n";
   									}
   								} else {
   									my $message = "Accession missing";
   									print $out "$label_text\t$message\n";
   								}
   								
   								#Check that the mobile element type field is present and of the
   								#correct format. Check that the name part of the mobile element
   								#type field (the part after the :) matches the label.
   								my $me_type_text;
   								for my $value ($feat_object->get_tag_values('mobile_element_type')) {
   									$me_type_text .= $value;
   								}	
   								
   								if ($me_type_text) {
   									if ($me_type_text =~ /.*?:(.*)/) {
   										my $me_type_name = $1;
   										$me_type_name =~ s/^\s+|\s+$//g;
   										if ($me_type_name) {
   											if ($me_type_name ne $label_name) {
   												my $message = "Mismatch between label and name field of mobile_element_type";
   												print $out "$label_text\t$message\n";
   											}
   										}
   									} else {
   										my $message = "Name missing from mobile_element_type";
   										print $out "$label_text\t$message\n";
   									}
   								} else {
   									my $message = "mobile_element_type field missing";
   									print $out "$label_text\t$message\n";
   								}
   							}
   							
   							#Check the CDS features
   							if ($ptag eq "CDS") {
   								#Check for presence of gene field; check that 
   								#gene field matches name part of label. Note: for ABR genes
   								#we include the ARO ID in the gene field; disregard that part
   								#when matching to the label
   								my $gene_text;
   								my $gene_name;
   								if (!exists $all_tags{'gene'}) {
   									my $message = "Gene field missing";
   									print $out "$label_text\t$message\n";
   								} else {
   									#Get gene field text
   									for my $value ($feat_object->get_tag_values('gene')) {
   										$gene_text .= $value;
   									}
   									#Remove initial and trailing white spaces
   									if ($gene_text) {
   										$gene_text =~ s/^\s+|\s+$//g;
   									}
   									if ($gene_text =~ /(.*?)\(ARO/) {
   										$gene_name = $1;
   									} else {
   										$gene_name = $gene_text;
   									}
   									$gene_name =~ s/^\s+|\s+$//g;
   									
   									
    	           					
   									if ($label_format_error == 0) {
   										if ($gene_name ne $label_name) {
   											my $message = "Label and Gene mismatch";
   											print $out "$label_text\t$message\n";
   										}
   									}	
   								}
   								
   								#Check for presence of product field
   								my $product_text;
   								my $product_missing = 0;
   								if (!exists $all_tags{'product'}) {
   									$product_missing = 1;
   									my $message = "Product field missing";
   									print $out "$label_text\t$message\n";
   								} else {
   									#Get product field text
   									for my $value ($feat_object->get_tag_values('product')) {
   										$product_text .= $value;
   									}
   									#Remove initial and trailing white spaces
   									if ($product_text) {
   										$product_text =~ s/^\s+|\s+$//g;
   									}
   								}
   								
   								#Check that the product name is OK: should be same as the gene name except with the 
   								#first letter capitalized or be N/A
   								if ($gene_name) {
   									if (!(($product_text eq ucfirst $gene_name) or ($product_text eq "N/A"))) {
    	           							my $message = "Product name is incorrect given gene name.";
    	           							print $out "$label_text\t$message\n";
    	           					}
    	           				}
   								
   								#Extract information from function field, if any
   								my $function_text;
   								if (exists $all_tags{'function'}) {
   									#Get product field text
   									for my $value ($feat_object->get_tag_values('function')) {
   										$function_text .= $value;
   									}
   									#Remove initial and trailing white spaces
   									if ($function_text) {
   										$function_text =~ s/^\s+|\s+$//g;
   									}
   								}
   								
   								#Check for presence of translation field
   								if (!exists $all_tags{'translation'}) {
   									my $message = "Translation missing";
   									print $out "$label_text\t$message\n";
   								}
   								
   								#Check for presence of the AssociatedElement field and
   								#check that it matches the Label
   								if ($element) {
   									if ($label_format_error == 0) {
   										if ($element ne $label_element) {
   											my $message = "Label and AssociatedElement mismatch";
   											print $out "$label_text\t$message\n";
   										}
   									}
   								} else {
   									my $message = "AssociatedElement field missing";
   									print $out "$label_text\t$message\n";
   								}
   								
   								#Check that LibraryName is present and is of correct format
   								if ($library_name) {
   									if (!($library_name =~ /(.*) \((.*)\)/)) {
   										my $message = "LibraryName format error";
   										print $out "$label_text\t$message\n";
   									}
   								} else {
   									my $message = "LibraryName missing";
   									print $out "$label_text\t$message\n";
   									
   								}	
   							
   								
   								#Check for presence of Class field and make sure the entry
   								#for Class is one of the allowed types
   								my @classes = ("Transposase", "Accessory Gene", "Integron Integrase", "Passenger Gene");
   								my %allowed_class;
   								foreach my $c (@classes) {
   									$allowed_class{$c} = 1;
   								}
   								
    	           				if ($class) {
    	           					if (!exists $allowed_class{$class}) {
    	           						my $message = "Class error";
    	           						print $out "$label_text\t$message\n";
    	           					}
    	           				} else {
    	           					my $message = "Class field missing";
    	           					print $out "$label_text\t$message\n";
    	           				}
    	           				
    	           				#Check fields for each class
    	           				if ($class) {
    	           					
    	           					#Check other fields for Transposase class
    	           					if ($class eq "Transposase") {
    	           						#Check that Subclass field is blank
    	           						if ($subclass) {
    	           							my $message = "Unexpected entry in Subclass field";
    	           							print $out "$label_text\t$message\n";
    	           						}
    	           					
    	           						#Check that the Chemistry field is one of the allowed chemistries
    	           						#(Blank is also OK)
    	           						my @chemistries = ("DDE", "HUH", "DEDD");
    	           						my %allowed_chem;
    	           						foreach my $ch (@chemistries) {
    	           							$allowed_chem{$ch} = 1;
    	           						}
    	           					
    	           						if ($chemistry) {
    	           							if (!exists $allowed_chem{$chemistry}) {
    	           								my $message = "Check Chemistry field. See list of allowed entries.";
    	           								print $out "$label_text\t$message\n";
    	           							}
    	           						}
    	           					
    	           						#Check that Target field is blank
    	           						if ($target) {
    	           							my $message = "Unexpected entry in Target field";
    	           							print $out "$label_text\t$message\n";
    	           						}
    	           						
    	           						#Check whether the gene name is on the list of known transposases
    	           						#If not, give a warning
    	           						if ($gene_name) {
    	           							#Gene might be a truncated or disrupted version of a known transposase gene
    	           							my $gene_name_core;
    	           							if (($gene_name =~ /(.*?) /) or ($gene_name =~ /(.*?)_/)) {
    	           								$gene_name_core = $1;
    	           							} else {
    	           								$gene_name_core = $gene_name;
    	           							}
    	           							if (!exists $tr_genes{$gene_name_core}) {
    	           								my $message = "Unexpected gene name for Tranposase Class.";
    	           								print $out "$label_text\t$message\n";
    	           							}
    	           						}
    	           					}
    	           				
    	           					#Check fields for Accessory Gene class
    	           					if ($class eq "Accessory Gene") {
    	           						#Check that the gene name is on the list of allowed Accessory Gene names 
    	           						#Gene might be a truncated or disrupted version of a known accessory gene
    	           						my $gene_name_core;
    	           						if ($gene_name) {
    	           							if (($gene_name =~ /(.*?) /) or ($gene_name =~ /(.*?)_/)) {
    	           								$gene_name_core = $1;
    	           							} else {
    	           									$gene_name_core = $gene_name;
    	           							}
    	           						}
    	           						
    	           						if ($gene_name_core) {
    	           							if (exists $ag_gene_product{$gene_name_core}) {
    	           							
    	           								#Check that the subclass is OK given the gene name
    	           								if ($subclass) {
    	           									if (exists $ag_gene_subclass{$gene_name_core} -> {$subclass}) {
    	           										#Check that the SequenceFamily is correct given the subclass
    	           										if ($ag_gene_seq_fam{$gene_name_core} -> {$subclass}) {
    	           											#There should be a SequenceFamily for this gene/subclass combo
    	           											if ($seq_fam) {
    	           												my $correct_seq_fam = $ag_gene_seq_fam{$gene_name_core} -> {$subclass};
    	           												if ($seq_fam ne $correct_seq_fam) {
    	           													my $message = "SequenceFamily is not correct given gene name and subclass.";
    	           													print $out "$label_text\t$message\n";
    	           												}
    	           											
    	           											} else {
    	           												my $message = "SequenceFamily missing.";
    	           												print $out "$label_text\t$message\n";
    	           											}
    	           										} else {
    	           											#There shouldn't be SequenceFamily for this gene/subclass combo
    	           											if ($seq_fam) {
    	           												my $message = "No SequenceFamily should be listed for this gene name/subclass.";
    	           												print $out "$label_text\t$message\n";
    	           											}
    	           										}
    	           										
    	           										#Check that the Chemistry is correct given the subclass
    	           										if ($ag_gene_chem{$gene_name_core} -> {$subclass}) {
    	           											my $correct_chem = $ag_gene_chem{$gene_name_core} -> {$subclass};
    	           											#There should be a Chemistry for this gene/subclass combo
    	           											if ($chemistry) {
    	           												#my $correct_chem = $ag_gene_chem{$gene_text} -> {$subclass};
    	           												if ($chemistry ne $correct_chem) {
    	           													my $message = "Chemistry is not correct given gene name and subclass.";
    	           													print $out "$label_text\t$message\n";
    	           												}
    	           											
    	           											} else {
    	           												my $message = "Chemistry field missing.";
    	           												print $out "$label_text\t$message\n";
    	           											}
    	           										} else {
    	           											#There shouldn't be SequenceFamily for this gene/subclass combo
    	           											if ($chemistry) {
    	           												my $message = "No Chemistry should be listed for this gene name/subclass.";
    	           												print $out "$label_text\t$message\n";
    	           											}
    	           										}			
    	           								
    	           									} else {
    	           									
    	           										my $message = "Subclass is not correct given gene name.";
    	           										print $out "$label_text\t$message\n";
    	           									}
    	           								
    	           								
    	           								} else {
    	           									if ($ag_gene_subclass{$gene_name_core}) {
    	           										#Gene is supposed to have a subclass and it is not present
    	           										my $message = "Subclass field missing.";
    	           										print $out "$label_text\t$message\n";
    	           									}
    	           								}	
    	           								
    	           							} else {
    	           								my $message = "Gene name is not on allowed list of Accessory Genes.";
    	           								print $out "$label_text\t$message\n";
    	           							}
    	           						
    	           							#Check that Target field is blank
    	           							if ($target) {
    	           								my $message = "Unexpected entry in Target field";
    	           								print $out "$label_text\t$message\n";
    	           							}
    	           						}
    	           					}
    	           							
    	           						
    	           					#Check fields for Passenger Gene class
    	           					if ($class eq "Passenger Gene") {
    	           						if ($subclass) {
    	           							my @pg_subclasses = ("Antibiotic Resistance", "Heavy Metal Resistance", "Toxin", "Antitoxin", "Plant Pathogenicity", "Other", "Hypothetical");
    	           							my %allowed_pg_subclass;
    	           							foreach my $sub (@pg_subclasses) {
    	           								$allowed_pg_subclass{$sub} = 1;
    	           							}
    	           						
    	           							if (!exists $allowed_pg_subclass{$subclass}) {
    	           								my $message = "Check Subclass field";
    	           								print $out "$label_text\t$message\n";
    	           							}
    	           							
    	           							#Check the Hypothetical and Other Genes. They should have no entry
    	           							#for Chemistry and Target fields. Hypothetical genes should additionally
    	           							#have no entry in the SequenceFamily field. The product field should
    	           							#match the gene field except for case unless the gene is a fragment, in
    	           							#case the product should be N/A.
    	           							
    	           							if (($subclass eq "Other") or ($subclass eq "Hypothetical")) {
    	           								if ($chemistry) {
    	           									my $message = "Unexpected entry in Chemistry field";
	           										print $out "$label_text\t$message\n";
	           									}
	           									
	           									if ($target) {
    	           									my $message = "Unexpected entry in Target field";
	           										print $out "$label_text\t$message\n";
	           									}
	           									
	           									if ($product_text) {
	           										if ((lc $product_text ne lc $gene_text) and ($product_text ne "N/A")) {
	           											my $message = "Mismatch in /gene and /product fields";
	           											print $out "$label_text\t$message\n";
	           										}
	           									}
	           								}
	           								
	           								if ($subclass eq "Hypothetical") {
    	           								if ($seq_fam) {
    	           									my $message = "Unexpected entry in SequenceFamily field";
	           										print $out "$label_text\t$message\n";
	           									}
	           									
	           									if ($label_text =~ /hypothetical/i) {
	           										my $message = "Gene name should not be Hypothetical";
	           										print $out "$label_text\t$message\n";
	           									}
	           								}
	           									
	           								#Check the Heavy Metal Resistance genes; they should have a metal
	           								#in the Target field, and no entry for SequenceFamily or Chemistry
	           								if ($subclass eq "Heavy Metal Resistance") {
    	           								# my %metal_tar = (	"mercury" => 1,
	           										# 	 			"nickel" => 1,
	           										# 	 			"chromate" => 1,
	           										# 	 			"arsenic" => 1,
	           										# 	 			"cadmium" => 1,
	           										# 	 			"cobalt" => 1,
	           										# 	 			"zinc" => 1,
	           										# 	 			"copper" => 1,
	           										# 	 			"lead" => 1,
																# 				"silver" => 1 # added by Francislon
																# 		);
	           											 				 		
	           									if ($target) {
	           										my @single_targets = split("\\|\\|", $target);
	           										foreach my $t (@single_targets) {
	           											if (!exists $metal_tar{lc($t)}) {
	           												my $message = "Check Target";
	           												print $out "$label_text\t$message\n";
	           											}
	           										}
	           									} else {
	           										my $message = "Heavy metal entry missing in Target field?";
	           										print $out "$label_text\t$message\n";
	           									}
	           							
	           									if ($seq_fam) {
    	           									my $message = "Unexpected entry in SequenceFamily field";
    	           									print $out "$label_text\t$message\n";
    	           								}
    	           					
    	           								if ($chemistry) {
    	           									my $message = "Unexpected entry in Chemistry field";
    	           									print $out "$label_text\t$message\n";
    	           								}
	           								}
	           								
	           								#Check Toxin genes. Make sure that gene, product, SequenceFamily, and
	           								#Target fields are consistent and that Chemistry field is blank
	           								if ($subclass eq "Toxin") {
	           									
	           									if (exists $toxin_gene_product{$gene_text}) {
	           										if ($product_text) {
	           											if ($product_text ne $toxin_gene_product{$gene_text}) {
	           												my $message = "/product field of TA gene is not correct given /gene field";
    	           											print $out "$label_text\t$message\n";
    	           										}
    	           									}
    	           									if ($seq_fam) {
    	           										if ($seq_fam ne $toxin_gene_seq_fam{$gene_text}) {
	           												my $message = "SequenceFamily field of TA gene is not correct given /gene field";
    	           											print $out "$label_text\t$message\n";
    	           										}
    	           									} else {
    	           										my $message = "SequenceFamily field missing";
    	           										print $out "$label_text\t$message\n";
    	           									}
    	           									
    	           									if ($target) {
    	           										if ($target ne $toxin_gene_target{$gene_text}) {
	           												my $message = "Target field of TA gene is not correct given /gene field";
    	           											print $out "$label_text\t$message\n";
    	           										}
    	           									}
    	           								} else {
    	           									my $message = "Entry in /gene field not found on TA gene list";
    	           									print $out "$label_text\t$message\n";	
    	           								}	
    	           							
    	           								if ($chemistry) {
    	           										my $message = "Unexpected entry in Chemistry field";
    	           										print $out "$label_text\t$message\n";
    	           								}
    	           							}
    	           							
    	           							if ($subclass eq "Antitoxin") {
	           									if (exists $antitox_gene_product{$gene_text}) {
	           										if ($product_text) {
	           											if ($product_text ne $antitox_gene_product{$gene_text}) {
	           												my $message = "/product field of TA gene is not correct given /gene field";
    	           											print $out "$label_text\t$message\n";
    	           										}
    	           									}
    	           									if ($seq_fam) {
    	           										if ($seq_fam ne $antitox_gene_seq_fam{$gene_text}) {
	           												my $message = "SequenceFamily field of TA gene is not correct given /gene field";
    	           											print $out "$label_text\t$message\n";
    	           										}
    	           									} else {
    	           										my $message = "SequenceFamily field missing";
    	           										print $out "$label_text\t$message\n";
    	           									}
    	           								} else {
    	           									my $message = "Entry in /gene field not found on TA gene list";
    	           									print $out "$label_text\t$message\n";	
    	           								}	
    	           							
    	           								if ($chemistry) {
    	           										my $message = "Unexpected entry in Chemistry field";
    	           										print $out "$label_text\t$message\n";
    	           								}
    	           								
    	           								if ($target) {
    	           									my $message = "Unexpected entry in Target field";
    	           									print $out "$label_text\t$message\n";
    	           								}
    	           							}				
	           						
    	           						
    	           							#Check ABR genes
    	           							if ($subclass eq "Antibiotic Resistance") {
    	           								if ($gene_name) {
    	           									#Make exceptions for the GNAT_fam, tetC and tetD genes (which are not in CARD) and partial genes that have "_p" in the name
    	           									if (($gene_name =~ /GNAT_fam/) or ($gene_name eq "tetC") or ($gene_name eq "tetD") or ($gene_name =~ /_p/)) {
    	           										next;
    	           									}
    	           									#Check format of gene name--should be ABC (ARO:00001224)
    	           									if ($gene_text =~ /^(.*?) \((ARO:.*?)\)/) {
    	           										my $gene_name = $1;
    	           										my $gene_acc = $2;
    	           									
    	           										#Make an exception for adding "bla" as a prefix to beta-lactamase genes
    	           										#and for genes that are partial or truncated
    	           										my $gene_name_short = $gene_name;
    	           										if ($gene_name_short =~ /^bla /) {
    	           											$gene_name_short =~ s/^bla //;
    	           										}
    	           									
    	           										if ($gene_name_short =~ /(.*?)_/) {
    	           											$gene_name_short = $1;
    	           										} 
    	           									
    	           										#Check that gene name has correct ARO accession
    	           										if (exists $gene_aro{$gene_name_short}) {
    	           											if ($gene_acc ne $gene_aro{$gene_name_short}) {
    	           												my $message = "Gene name and ARO accession mismatch";
    	           												print $out "$label_text\t$message\n";
    	           											} else {
    	           												#Check function field; check that each function is of the form xxxxx (ARO:00001234);
    	           												#if so, check that the text and accession agree with CARD
    	           												if ($function_text) {
    	           													my @fun_array = split("\\|\\|", $function_text);
    	           													my %fun_hash;
    	           													foreach my $f (@fun_array) {
    	           														if ($f =~ /^(.*?) \((ARO:.*?)\)/) {
    	           															my $fun_name = $1;
    	           															my $fun_acc = $2;
    	           															#Put the functions from CARD into a hash to later
    	           															#check that they are correct and complete for that gene according to CARD
    	           															$fun_hash{$fun_name} = $fun_acc;
    	           															if (exists $mech_acc{$fun_name}) {
    	           																if ($fun_acc ne $mech_acc{$fun_name}) {
    	           																	my $message = "Function and ARO accession mismatch: $fun_name";
    	           																	print $out "$label_text\t$message\n";
    	           																} 		
    	           															} else {
    	           																my $message = "Function not found in CARD: $fun_name";
    	           																print $out "$label_text\t$message\n";
    	           															}
    	           														
    	           														} else {
    	           															my $message = "Function not in CARD format: $f";
    	           															print $out "$label_text\t$message\n";
    	           														}
    	           													}
    	           											
    	           													#Check that the functions are correct and complete for that gene according to CARD
    	           													my @missing_functions;
    	           													foreach my $f (keys %{$gene_mech{$gene_name_short}}) {
    	           														push (@missing_functions, $f) unless exists $fun_hash{$f};
    	           													}
    	           											
    	           													my @extra_functions;
    	           													foreach my $f (keys %fun_hash) {
    	           														push (@extra_functions, $f) unless exists ($gene_mech{$gene_name_short} ->{$f});
    	           													}
    	           											
    	           													foreach my $f (@missing_functions) {
    	           														my $message = "CARD function for this gene missing: $f";
    	           														print $out "$label_text\t$message\n";
    	           													}
    	           											
    	           													foreach my $f (@extra_functions) {
    	           														my $message = "Function not associated with this gene in CARD: $f";
    	           														print $out "$label_text\t$message\n";
    	           													}
    	           												} else {
    	           													my $message = "Function field missing";
    	           													print $out "$label_text\t$message\n";
    	           												}
    	           										
    	           												#Check the SequenceFamily field; check that each SequenceFamily is of the form xxxxx (ARO:00001234);
    	           												#if so, check that the family name and accession agree with CARD
    	           												if ($seq_fam) {
    	           													my @fam_array = split("\\|\\|", $seq_fam);
    	           													my %fam_hash;
    	           													foreach my $f (@fam_array) {
    	           														if ($f =~ /^(.*?) \((ARO:.*?)\)/) {
    	           															my $fam_name = $1;
    	           															my $fam_acc = $2;
    	           															#Put the families from CARD into a hash to later
    	           															#check that they are correct and complete for that gene according to CARD
    	           															$fam_hash{$fam_name} = $fam_acc;
    	           															if (exists $fam_acc{$fam_name}) {
    	           																if ($fam_acc ne $fam_acc{$fam_name}) {
    	           																	my $message = "SequenceFamily and ARO accession mismatch: $fam_name";
    	           																	print $out "$label_text\t$message\n";
    	           																} 		
    	           															} else {
    	           																my $message = "SequenceFamily not found in CARD: $fam_name";
    	           																print $out "$label_text\t$message\n";
    	           															}
    	           														
    	           														} else {
    	           															my $message = "SequenceFamily not in CARD format: $f";
    	           															print $out "$label_text\t$message\n";
    	           														}
    	           													}
    	           											
    	           													#Check that the functions are correct and complete for that gene according to CARD
    	           													my @missing_fams;
    	           													foreach my $f (keys %{$gene_fam{$gene_name_short}}) {
    	           														push (@missing_fams, $f) unless exists $fam_hash{$f};
    	           													}
    	           											
    	           													my @extra_fams;
    	           													foreach my $f (keys %fam_hash) {
    	           														push (@extra_fams, $f) unless exists ($gene_fam{$gene_name_short} ->{$f});
    	           													}
    	           											
    	           													foreach my $f (@missing_fams) {
    	           														my $message = "CARD SequenceFamily for this gene missing: $f";
    	           														print $out "$label_text\t$message\n";
    	           													}
    	           											
    	           													foreach my $f (@extra_fams) {
    	           														my $message = "SequenceFamily not associated with this gene in CARD: $f";
    	           														print $out "$label_text\t$message\n";
    	           													}	
    	           												} else {
    	           													my $message = "Entry missing in SequenceFamily field?";
    	           													print $out "$label_text\t$message\n";
    	           												}
    	           										
    	           												#Check targets
    	           												#Check the target field; check that each target is of the form xxxxx (ARO:00001234);
    	           												#if so, check that the target name and accession agree with CARD
    	           												if ($target) {
    	           													my @target_array = split("\\|\\|", $target);
    	           													my %target_hash;
    	           													foreach my $t (@target_array) {
    	           											
    	           													
    	           														if ($t =~ /^(.*?) \((ARO:.*?)\)/) {
    	           															my $target_name = $1;
    	           															my $tar_acc = $2;
    	           															#Put the targets from CARD into a hash to later
    	           															#check that they are correct and complete for that gene according to CARD
    	           															$target_hash{$target_name} = $tar_acc;
    	           															if (exists $target_acc{$target_name}) {
    	           																if ($tar_acc ne $target_acc{$target_name}) {
    	           																	my $message = "Target and ARO accession mismatch: $target_name";
    	           																	print $out "$label_text\t$message\n";
    	           																}
    	           															} elsif ($gene_name =~ /van/) {
    	           															#Make an exception for the "van" genes where we want to list vancomycin as a target
    	           															#even though it isn't a drug class according to CARD
    	           																if ($target_name ne "vancomycin") {
    	           																	my $message = "Target not found in CARD: $target_name";
    	           																	print $out "$label_text\t$message\n";
    	           																}
    	           															
    	           																if (($target_name eq "vanomycin") and ($tar_acc ne "ARO:0000028")) {
    	           																	my $message = "Target and ARO accession mismatch: $target_name";
    	           																	print $out "$label_text\t$message\n";
    	           																}		
    	           															} else {
    	           															
    	           																my $message = "Target not found in CARD: $target_name";
    	           																print $out "$label_text\t$message\n";
    	           															}
    	           														
    	           														} else {
    	           														
    	           															my $message = "Target not in CARD format: $t";
    	           															print $out "$label_text\t$message\n";
    	           														
    	           														}
    	           													}
    	           											
    	           													#Check that the targets are correct and complete for that gene according to CARD
    	           													my @missing_targets;
    	           													foreach my $t (keys %{$gene_target{$gene_name_short}}) {
    	           														push (@missing_targets, $t) unless exists $target_hash{$t};
    	           														if ($gene_name_short eq "qacL") {
    	           															print "TRUE\n";
    	           															print "*$t*\n";
    	           														}
    	           													}
    	           											
    	           													my @extra_targets;
    	           													foreach my $t (keys %target_hash) {
    	           														push (@extra_targets, $t) unless exists ($gene_target{$gene_name_short} ->{$t});
    	           													}
    	           											
    	           												foreach my $t (@missing_targets) {
    	           													my $message = "CARD Target for this gene missing: $t";
    	           													print $out "$label_text\t$message\n";
    	           												}
    	           											
    	           													foreach my $t (@extra_targets) {
    	           														#Make an exception for listing vancomycin as a target for van genes
    	           														if (!(($t eq "vancomycin") and ($gene_name =~ /van/))) {
    	           															my $message = "Target not associated with this gene in CARD: $t";
    	           															print $out "$label_text\t$message\n";
    	           														}
    	           													}
    	           												} else {
    	           													my $message = "Target field missing";
    	           													print $out "$label_text\t$message\n";
    	           												}
    	           										
    	           											}
    	           												
    	           										} else {
    	           											my $message = "Gene name not found in CARD";
    	           											print $out "$label_text\t$message\n";
    	           										}
    	           								
    	           									} else {
    	           										my $message = "ABR gene name is not of the format ABC (ARO:00001234)";
    	           										print $out "$label_text\t$message\n";
    	           									}
    	           								}	
    	           							}
    	           						
    	           						} else {
    	           							my $message = "Subclass field missing";
    	           							print $out "$label_text\t$message\n";
    	           						} 
    	           					}
    	           					
    	           					#Check integron integrases
    	           					if ($class eq "Integron Integrase") {
    	           						#Check that subclass is present and one of the allowed subclasses
    	           						my %int_subclass = ("Class 1" => 1,
	           											 	"Class 2" => 1,
	           											 	"Class 3" => 1);
	           							
	           							if ($subclass) {
	           								if (!exists $int_subclass{$subclass}) {
	           									my $message = "Check Subclass field";
	           									print $out "$label_text\t$message\n";
	           								}
	           							} else {
	           								my $message = "Subclass field missing";
	           								print $out "$label_text\t$message\n";
	           							}
	           							
	           							#Check that SequenceFamily is present, is one of the allowed families and corresponds to the subclass
	           							my %int_fam = (	"Class 1 Integron Tyrosine Integrase" => 1,
	           											"Class 2 Integron Tyrosine Integrase" => 1,
	           											"Class 3 Integron Tyrosine Integrase" => 1);
	           							if ($seq_fam) {
	           								if (exists $int_fam{$seq_fam}) {
	           									$seq_fam =~ /(.*) Integron/;
	           									my $int_class = $1;
	           									if ($int_class ne $subclass) {
	           										my $message = "Subclass and SequenceFamily mismatch";
	           										print $out "$label_text\t$message\n";
	           									}
	           								} else {
	           									my $message = "Check SequenceFamily";
	           									print $out "$label_text\t$message\n";
	           								}
	           							} else {
	           								my $message = "Entry missing in SequenceFamily field?";
	           								print $out "$label_text\t$message\n";
	           							}
	           							
	           							#Check that Chemistry field is present and is one of the allowed types
	           							if ($chemistry) {
	           								my %int_chem = ("Tyrosine" => 1);
	           								if (!exists $int_chem{$chemistry}) {
	           									my $message = "Check Chemistry field";
	           									print $out "$label_text\t$message\n";
	           								}
	           							} else {
	           								my $message = "Chemistry field missing";
	           								print $out "$label_text\t$message\n";
	           							}
	           							
	           							#Check that the gene name is one of the allowed names
	           							my %int_genes = (	"intI1" => 1,
	           												"intI2" => 1,
	           												"intI3" => 1,
	           												"intI1_p" => 1);
	           												
	           							if ($gene_text) {
	           								if (!exists $int_genes{$gene_text}) {
	           									my $message = "Check gene field: $gene_text";
	           									print $out "$label_text\t$message\n";
	           								}
	           							}
	           						}			    						
    	           				}			
   							}
   						} 							
   					}
   				}
   			}
   		}
	}
   					



##########################
#Sub-routines
##########################
sub open_file {
	my ($file_name) = @_;
	my $fh;
	
	unless (open($fh, $file_name)) {
		print "Cannot open file $file_name for reading.\n";
		exit;
	}
	
	return $fh;
}


sub read_file {
	my ($file_name) = @_;
	
	unless (open(FILEHANDLE, $file_name)) {
		print "Cannot open file $file_name for reading.\n";
		exit;
	}

	my @file = <FILEHANDLE>;
	close FILEHANDLE;
	return @file;
}

sub open_write_file {
	my ($file_name) = @_;
	my $fh;
	
	unless (open($fh, ">$file_name")) {
		print "Cannot open file $file_name for writing.\n";
		exit;
	}

	return $fh;
}

sub open_append_file {
	my ($file_name) = @_;
	my $fh;
	
	unless (open($fh, ">>$file_name")) {
		print "Cannot open file $file_name for writing.\n";
		exit;
	}

	return $fh;
}

sub fix_line_breaks {
	my($file_ref) = @_;
	my $file_ref_string = join ('', @$file_ref);
	@$file_ref = split ('\R', $file_ref_string);
	
}

sub make_directory {
    my $directory = @_;
    
    unless(mkdir $directory) {
        die "Unable to create $directory\n";
    }
}	

sub extract_note_field {
	my($field) = @_;
	if ($field =~ /^\s$/) {
   	#If all whitespace, remove the whitespace so $name is undefined (if ($name) = FALSE)
		$field =~ s/\s//g;
	} else {
		#Remove initial and trailing whitespace
		$field =~ s/^\s+|\s+$//g;
	}
	return $field;
}	
