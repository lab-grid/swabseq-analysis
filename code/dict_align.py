#################################################
# Dictionary based matching for targed amplicon #
# quantification with NGS                       #
#################################################
import argparse
import itertools
import os
import time
import pandas as pd
import subprocess
import sys
from itertools import chain, combinations, product, repeat, compress
import xml.etree.ElementTree as ET
import csv
from collections import defaultdict
from contextlib import contextmanager


def hamming_circle(s, n, alphabet):
    """
    Generate strings over alphabet whose Hamming distance from s is
    exactly n.

    >>> sorted(hamming_circle("ATG",1,"ATGC"))
    ['AAG', 'ACG', 'AGG', 'ATA', 'ATC', 'ATT', 'CTG', 'GTG', 'TTG']
    
    credit: https://codereview.stackexchange.com/a/88919

    """
    for positions in combinations(range(len(s)), n):
        for replacements in product(range(len(alphabet) - 1), repeat=n):
            cousin = list(s)
            for p, r in zip(positions, replacements):
                if cousin[p] == alphabet[r]:
                    cousin[p] = alphabet[-1]
                else:
                    cousin[p] = alphabet[r]
            yield ''.join(cousin)
            


def hamming_ball(s, n, alphabet):
    """
    Generate strings over alphabet whose Hamming distance from s is
    less than or equal to n.
    """
    return chain.from_iterable(
        hamming_circle(s, i, alphabet)
        for i
        in range(n + 1)
    )



def reverse_complement(seq):
    """
    Reverse compliment a DNA sequenec
    Credit: https://bioinformatics.stackexchange.com/a/3585
    """
    tab = str.maketrans("ACTG", "TGAC")
    return seq.translate(tab)[::-1]


###############################################
# Identify, remove, and categorize duplicates #
###############################################

def list_duplicates_of(seq,item):
    """
    Identifies the position of duplicated sequences
    """
    start_at = -1
    locs = []
    while True:
        try:
            loc = seq.index(item,start_at+1)
        except ValueError:
            break
        else:
            locs.append(loc)
            start_at = loc
    return locs


def remove_duplicates(seqs, classification, target, pattern):
    """
    Recursive function to identify duplicated sequences
    and remove them, which replacing the mismatch classification
    to undetermined since we cannot distinguish between a single
    base substitution or a single base deletion.
    """
    dups = list_duplicates_of(seqs, pattern)
    
    if len(dups) > 1:
        classification[dups[0]] = "undetermined"
        
        del seqs[dups[1]]
        del classification[dups[1]]
        del target[dups[1]]
        
        remove_duplicates(seqs, classification, target, pattern)

##############################################################
# Generate sequence dictionary with desired Hamming distance #
##############################################################

def generate_dictionary(sequence, target, indels: bool = True, rc: bool = False, ham_dist: int = 1):
    """
    Generates a dictionary of expected variants for a given
    sequence from single base substitutions or single base
    deletions. Requires n+1 bases for a given sequenced amplicon.
    It also classifies the type of variat as either a single base
    mismatch, single base deletion, or undetermined.
    
    This version of the function requires a csv file with two colums: 
    1) sequence: this column must be populated with the target sequenecs
    2) target: this column must be populated with values that describe the
    target sequence. For instance, for amplicons, it can list the name of
    amplicon. For indicecs, it can include the position in the 384-well
    plate map.
    """
    
    dictionary = {}
    running_sequence = []
    running_target_sequence = []
    running_target = []
    running_match = []
    for i, s in enumerate(sequence):
    
        dict_sequence = []
        dict_target_sequence = []
        dict_target = []
        dict_match = []
        
        if rc:
            ind_full = reverse_complement(sequence[i].upper())[1:]
            ind = ind_full[0:-1]
        else:
            ind_full = sequence[i].upper()[1:]
            ind = ind_full[0:-1]
    
        dict_sequence.append(ind)
        dict_target.append(target[i])
        dict_match.append("exact match")
    
        if ham_dist == 1:
            dict_sequence = dict_sequence + list(hamming_circle(ind, 1, "ATGCN"))
        elif ham_dist > 1:
            dict_sequence = dict_sequence + list(hamming_ball(ind, ham_dist, "ATGCN"))

        dict_target.extend(repeat(target[i],(len(dict_sequence) - 1)))
        dict_match.extend(repeat("mismatch",(len(dict_sequence) - 1)))
        
        if indels:
            for j, s in enumerate(ind):
                x = [char for char in ind_full]
                del x[j]
                x = ''.join(x)
                dict_sequence.append(x)
                dict_target.append(target[i])
                dict_match.append("base deletion")
                
            for letter in "ATGC":
                for j in range(len(ind) + 1):
                    x = list(ind)
                    x.insert(j, letter)
                    x = x[0:-1]
                    x = ''.join([str(elem) for elem in x])
                    
                    dict_sequence.append(x)
                    dict_target.append(target[i])
                    dict_match.append("base insertion")
        
            # Remove collisions and label undetermined
            for seq in dict_sequence:
                remove_duplicates(dict_sequence, dict_match, dict_target, seq)
        
        dict_target_sequence = [sequence[i][1:-1]] * len(dict_sequence)
        
        running_sequence = running_sequence + dict_sequence
        running_target_sequence = running_target_sequence + dict_target_sequence
        running_target = running_target + dict_target
        running_match = running_match + dict_match
    
    dictionary = defaultdict(dict)
    
    for running_sequence, a, b, c in zip(running_sequence, running_target_sequence, running_target, running_match):
        dictionary[running_sequence] = {'sequence' : a, 'target': b, 'match': c}

    return(dictionary)




##############################
# Sequence matching function #
##############################

def seq_match(index, seqs, ret: str = 'target'):
    match = []
    for i in seqs:
        try:
            match.append(index[i][ret])
        except:
            match.append(float('NaN'))
            #match.append(i)
    return match

#################################################
# Function to read in sequences from FASTQ file #
#################################################

def read_fastq_gz(filename: str, max_line_length: int) -> list:
    with subprocess.Popen(['gunzip', '-c', filename], stdout=subprocess.PIPE) as proc:
        records = list(itertools.islice(proc.stdout, 1, None, 4))
        if len(records[1]) > max_line_length:
            records[:] = [record[0:max_line_length] for record in records]

        proc_code = proc.wait()
        if proc_code != 0:
            raise Exception(f"`gunzip -c {filename}` exited with non-zero code: {str(proc_code)}")

        return records

#######################################################
# Function to list the .fastq.gz files in a directory #
#######################################################

def list_fastq_gz_files(dir: str, extension: str = 'fastq.gz') -> list:
    return [
        f
        for f
        in os.listdir(dir)
        if os.path.isfile(os.path.join(dir, f)) and f.endswith(f"{extension}")
    ]

########################################
# Converts arguments to boolean values #
########################################

def str2bool(v) -> bool:
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

#######################################################
# Times an operation that takes place in a with block #
#######################################################

@contextmanager
def timing():
    tic = time.time()
    try:
        yield None
    finally:
        toc = time.time()
        print(toc - tic)


###################################################
# Parses command-line arguments passed to program #
###################################################

def parse_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument(
        '--rundir',
        dest='rundir',
        type=str,
        help='path to the run directory',
    )
    parser.add_argument(
        '--dictdir',
        dest='dictpath',
        type=str,
        help='path to the dictionary files',
    )
    parser.add_argument(
        '--readmode',
        dest='readmode',
        default='rev',
        help='direction of i5 reads',
    )
    parser.add_argument(
        '--debug',
        dest='debug',
        type=str2bool,
        default=False,
        help='debug mode, extra output',
    )
    return parser.parse_args()

#===============================================================================

if __name__ == '__main__':
    args = parse_args()

    fastq_path = f"{os.path.join(args.rundir, 'out')}/"
    debug = args.debug == 'TRUE'

    # Unzip FASTQ Files
#    for gz in files:
#        fastq = gz[: -3]
#        try:
#            subprocess.check_call('gunzip -c ' + fastq_path + gz + ' >' + fastq_path + fastq, shell=True)
#        except:
#            sys.exit('Shell error')

    # Direction of primers based on instrument run mode
    tree = ET.parse('RunParameters.xml')
    root = tree.getroot()
    chemistry = root.findtext("Chemistry").split(' ')

    if chemistry[1] == 'Rapid':
        rc = False
    else:
        rc = True

    # Make dictionaries
    print('Creating Dictionaries')

    ind1 = []
    ind_target = []
    ind2 = []
    with open("../hash_tables/384_plate_map.csv") as f:
        for row in csv.DictReader(f):
            # Load in index 1 - always reverse compliment
            ind1.append(row['index'])
            ind_target.append(row['target'])
            # Load in index 2 - reverse compliment depending on instrument / kit
            ind2.append(row['index2'])

    ind1_hash_table = generate_dictionary(ind1, ind_target, rc=True, ham_dist=1)
    ind2_hash_table = generate_dictionary(ind2, ind_target, rc=rc, ham_dist=1)

    # Load in amplicons
    amps = []
    amp_targets = []
    with open("../hash_tables/amplicon_map.csv") as f:
        for row in csv.DictReader(f):
            amps.append(row['sequence'])
            amp_targets.append(row['target'])

    amps_hash_table = generate_dictionary(amps, amp_targets)

    # Unzip fastq.gz files
    print('Decompressing and reading fastq.gz files')
    with timing():
        try:
            amps = read_fastq_gz(os.path.join(fastq_path, 'Undetermined_S0_R1_001.fastq.gz'), 26)
        except Exception as ex:
            sys.exit(f"Error decompressing `Undetermined_S0_R1_001.fastq.gz`: {str(ex)}")

        try:
            i1 = read_fastq_gz(os.path.join(fastq_path, 'Undetermined_S0_I1_001.fastq.gz'), 10)
        except Exception as ex:
            sys.exit(f"Error decompressing `Undetermined_S0_I1_001.fastq.gz`: {str(ex)}")

        try:
            i2 = read_fastq_gz(os.path.join(fastq_path, 'Undetermined_S0_I2_001.fastq.gz'), 10)
        except Exception as ex:
            sys.exit(f"Error decompressing `Undetermined_S0_I2_001.fastq.gz`: {str(ex)}")

    print('Aligning sequences')
    with timing():
        results = {
            'i1': seq_match(ind1_hash_table, i1, ret='sequence'),
            'i2': seq_match(ind2_hash_table, i2, ret='sequence'),
            'amps': seq_match(amps_hash_table, amps, ret='target'),
        }

    # Output results
    print('Counting Amplicions')

    results = pd.DataFrame(results)
    if debug:
        print(results.groupby(['amps'], dropna=False).size())
        
        # Top unalined seqs
        # Amps
        check_for_nan = results['amps'].isnull()
        na_amps = pd.DataFrame(list(compress(amps, check_for_nan)), columns=['amps'])
        na_amps\
            .groupby(['amps'], dropna=False)\
            .size()\
            .sort_values()\
            .tail()\
            .to_csv(os.path.join(args.rundir, "top_unaligned_amps.csv"))

        # I1
        check_for_nan = results['i1'].isnull()
        na_amps = pd.DataFrame(list(compress(i1, check_for_nan)), columns=['i1'])
        na_amps\
            .groupby(['i1'], dropna=False)\
            .size()\
            .sort_values()\
            .tail()\
            .to_csv(os.path.join(args.rundir, "top_unaligned_i1.csv"))

        # I2
        check_for_nan = results['i2'].isnull()
        na_amps = pd.DataFrame(list(compress(i2, check_for_nan)), columns=['i2'])
        na_amps\
            .groupby(['i2'], dropna=False)\
            .size()\
            .sort_values()\
            .tail()\
            .to_csv(os.path.join(args.rundir, "top_unaligned_i2.csv"))

    results = results.groupby(['i1','i2','amps'], dropna=False).size()
    results.to_csv(os.path.join(args.rundir, "results.csv"))

    print("Finished")
