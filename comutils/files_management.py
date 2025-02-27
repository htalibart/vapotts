import os
import re
import json
import pandas as pd
from Bio import SeqIO, AlignIO, Align
import ctypes
import pathlib
import shutil
import csv
import subprocess

def create_folder(name):
    p = pathlib.Path(name) 
    if not p.is_dir():
        p.mkdir()
    return p

def get_info_res_file_name(output_folder):
    return output_folder/"info.csv"

def get_aln_res_file_name(output_folder):
    return output_folder/"aln.csv"

def get_aln_with_gaps_res_file(output_folder):
    return output_folder/"aln_with_gaps.csv"

def get_aligned_positions_dict_from_ppalign_output_file(aln_res_file):
    """ get {"pos_ref":list of aligned positions in first Potts model, "pos_2":  list of aligned positions in second Potts model} from PPalign output .csv file """
    check_if_file_ok(aln_res_file)
    with open(str(aln_res_file), 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = next(csv_reader)
        aln_dict = {name:[] for name in header}
        for row in csv_reader:
            for k in range(2):
                if (row[k]=='-'):
                    value='-'
                else:
                    try:
                        value = int(row[k])
                    except Exception as e:
                        value = None
                aln_dict[header[k]].append(value)
    assert(len(aln_dict['pos_ref'])==len(aln_dict['pos_2']))
    return aln_dict


def get_aligned_positions_with_gaps_dict_from_ppalign_output_file(aln_with_gaps_res_file):
    """ get {"pos_ref":list of aligned positions with gaps in first Potts model, "pos_2":  list of aligned positions with gaps in second Potts model} from PPalign output .csv file """
    check_if_file_ok(aln_with_gaps_res_file)
    with open(str(aln_with_gaps_res_file), 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = next(csv_reader)
        aln_with_gaps_dict = {name:[] for name in header}
        for row in csv_reader:
            for k in range(2):
                if (row[k]=='-'):
                    value='-'
                else:
                    try:
                        value = int(row[k])
                    except Exception as e:
                        value = None
                aln_with_gaps_dict[header[k]].append(value)
    assert(len(aln_with_gaps_dict['pos_ref'])==len(aln_with_gaps_dict['pos_2']))
    return aln_with_gaps_dict

def get_infos_solver_dict_from_ppalign_output_file(infos_res_file):
    df = pd.read_csv(infos_res_file)
    return df.loc[0].to_dict()


def create_seq_fasta(seq, fastaseq_file, seq_name="Billy"):
    """ creates fasta file @fastaseq_file for @seq and returns sequence name """ #TODO BioPython
    with open(str(fastaseq_file), 'w') as of:
        of.write(">"+seq_name+"\n")
        of.write(seq+"\n")
    return seq_name


def get_sequence_by_name_in_fasta_file(seqname, fasta_file):
    record_dict = SeqIO.to_dict(SeqIO.parse(str(fasta_file), "fasta"))
    return record_dict[seqname]


def get_first_sequence_in_fasta_file(seq_file):
    return str(list(SeqIO.parse(str(seq_file), "fasta"))[0].seq)

def get_first_sequence_name(seq_file):
    return str(list(SeqIO.parse(str(seq_file), "fasta"))[0].id)


def get_first_sequence_clean_name(seq_file):
    actual_name = get_first_sequence_name(seq_file)
    return ''.join(e for e in actual_name if e.isalnum())


def get_nb_columns_in_alignment(aln_file):
    return len(get_first_sequence_in_fasta_file(aln_file))


def get_nb_sequences_in_fasta_file(fasta_file):
    records = list(SeqIO.parse(str(fasta_file), "fasta"))
    return len(records)


def create_file_with_less_sequences(aln_file, aln_1000, nb_sequences=1000, fileformat="fasta"):
    records = list(SeqIO.parse(str(aln_file),fileformat))
    with open(str(aln_1000), 'w') as f:
        SeqIO.write(records[:nb_sequences], f, fileformat)


def split_fasta(fasta_file, seq_folder):
    """ splits @fasta_file into multiple fasta files with 1 single sequence in folder @øeq_folder """
    records = SeqIO.parse(open(str(fasta_file)), "fasta")
    create_folder(seq_folder)
    for record in records:
        with open(str(seq_folder)+str(record.id)+".fasta",'w') as f:
            SeqIO.write(record, f, "fasta")

def get_trimal_ncol(colnumbering_file):
    """ trimal output file to list """
    with colnumbering_file.open() as f:
        col_list = re.sub('[^0-9,.]', '', f.read()).split(',')
    return [int(s) for s in col_list]


def write_readme(folder, **kwargs):
    p = folder/'README.txt'
    with p.open(mode='w') as f:
        json.dump(kwargs, f, default=str)

def copy(old_location, new_location):
    if not new_location.is_file():
        shutil.copy(str(old_location), str(new_location))

def remove_file(filepath):
    if not filepath.is_file():
        raise Exception("file does not exist")
    os.remove(str(filepath))

def get_format(seq_file):
    extension = seq_file.suffix[1:]
    if extension=="fa":
        return "fasta"
    else:
        return extension


def get_list_from_csv(csv_file):
    with open(str(csv_file), 'r') as f:
        csvreader = csv.reader(f)
        row = next(csvreader)
        csv_list = []
        for s in row:
            if s == 'None':
                csv_list.append(None)
            else:
                csv_list.append(int(s))
    return csv_list

def write_list_to_csv(l_, csv_file):
    l = [str(s) for s in l_]
    with open(str(csv_file), 'w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(l)


def check_if_file_ok(f):
    if f is None:
        raise Exception(str(f)+" is not defined")
    elif not os.path.exists(str(f)):
        raise Exception("File not found :"+str(f))

def check_if_dir_ok(d):
    if d is None:
        raise Exception(str(d)+" is not defined")
    elif not os.path.isdir(str(d)):
        raise Exception(str(d)+" is not a directory")


def write_positions_to_csv(positions_dict, output_file):
    """ PPalign aln dict to csv file """
    with open(str(output_file), 'w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(list(positions_dict.keys()))
        for ind in range(len(positions_dict[list(positions_dict.keys())[0]])):
            row = [positions_dict[key][ind] for key in positions_dict]
            csvwriter.writerow(row)


def add_sequence_to_fasta_file_if_missing(unaligned_fasta, sequence_file):
    unaligned_records = list(SeqIO.parse(unaligned_fasta, "fasta"))
    sequence_record = list(SeqIO.parse(sequence_file, "fasta"))[0]
    if str(sequence_record.seq)!=str(unaligned_records[0].seq):
        new_unaligned_records = [sequence_record]+unaligned_records
        SeqIO.write(new_unaligned_records, unaligned_fasta, "fasta")


def remove_positions_with_gaps_in_first_sequence(input_fasta, output_fasta):
    # removes all positions with gaps in the first sequence
    aln = AlignIO.read(str(input_fasta), 'fasta')
    first_sequence = str(aln[0].seq)
    good_positions = [k for k in range(len(first_sequence)) if first_sequence[k]!='-']
    first_pos = good_positions[0]
    clean_aln = Align.MultipleSeqAlignment(aln[:,first_pos:first_pos+1])
    for pos in good_positions[1:]:
        clean_aln+=aln[:,pos:pos+1]
    AlignIO.write(clean_aln, str(output_fasta), 'fasta')
    return output_fasta

def remove_sequences_with_bad_characters(input_fasta, output_fasta, bad_characters=['J','U','Z','B','O','X']):
    all_records = list(SeqIO.parse(str(input_fasta), 'fasta'))
    clean_records = []
    for record in all_records:
        if not any(bad_character in str(record.seq).upper() for bad_character in bad_characters):
            #clean_records.append(record.upper())
            clean_records.append(record)
    SeqIO.write(clean_records, str(output_fasta), 'fasta')


def get_parameters_from_readme_file(readme_file):
    params = json.load(open(str(readme_file)))
    return params
