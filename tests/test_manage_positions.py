import unittest
import shutil, tempfile
import pathlib

import numpy as np

from makepotts.potts_object import *
from ppalign.manage_positions import *

import pkg_resources
from tests.resources_manager import *

class Test_ManagePositions(unittest.TestCase):

    def setUp(self):
        self.output_folder = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.output_folder)

    def test_get_alignment_with_gaps(self):
        aligned_positions = {"pos_ref":[4,5,7,8,9,10], "pos_2":[0,1,2,3,4,5]}
        alignment_with_gaps = {"pos_ref":[0,1,2,3,4,5,6,7,8,9,10], "pos_2":['-','-','-','-',0,1,'-',2,3,4,5]}
        res = get_alignment_with_gaps(aligned_positions)
        self.assertEqual(alignment_with_gaps, res)

    def test_get_alignment_with_gaps_2(self):
        aligned_positions = {"pos_ref":[4,5,8,9,10], "pos_2":[0,1,3,4,5]}
        alignment_with_gaps = {"pos_ref":[0,1,2,3,4,5,6,7,'-',8,9,10], "pos_2":['-','-','-','-',0,1,'-', '-',2,3,4,5]}
        res = get_alignment_with_gaps(aligned_positions)
        self.assertEqual(alignment_with_gaps, res)

    def test_get_alignment_with_gaps_2(self):
        aligned_positions = {"pos_ref":[0,1,2,3], "pos_2":[0,2,3,4]}
        alignment_with_gaps = {"pos_ref":[0,'-',1,2,3], "pos_2":[0,1,2,3,4]}
        res = get_alignment_with_gaps(aligned_positions)
        self.assertEqual(alignment_with_gaps, res)

    def test_get_alignment_with_gaps_3(self):
        aligned_positions = {"pos_ref":[4,5,8,9,10], "pos_2":[1,2,3,4,5]}
        alignment_with_gaps = {"pos_ref":[0,1,2,3,'-',4,5,6,7,8,9,10], "pos_2":['-','-','-','-',0,1,2,'-','-',3,4,5]}
        res = get_alignment_with_gaps(aligned_positions)
        self.assertEqual(alignment_with_gaps, res)


    def test_aligned_sequences(self):
        aligned_positions = {"pos_ref":[0,1,3], "pos_2":[0,1,2]}
        sequences = ["ARND","ARND"]
        seq_positions = get_alignment_with_gaps(aligned_positions)
        aligned_sequences = aligned_positions_to_aligned_sequences(seq_positions, sequences)
        self.assertEqual(aligned_sequences, ["ARND","AR-N"])

    def test_get_seqs_aligned(self):
        objs = []
        for k in range(2):
            seq_file = FAKE_SEQS_FOLDER/("fake_seq_"+str(k)+".fasta")
            potts_folder = pathlib.Path(tempfile.mkdtemp())
            objs.append(Potts_Object.from_sequence_alone(potts_folder=potts_folder, sequence_file=seq_file, inference_type="one_hot"))
        aligned_positions_with_gaps = {"pos_ref":[0,1,2,3,4,5,6,7,8,9,10], "pos_2":['-','-','-','-',0,1,'-',2,3,4,5]}
        seqs_aligned = get_seqs_aligned(aligned_positions_with_gaps, objs)
        self.assertEqual(seqs_aligned[0], 'YFYFMAEIKEH')
        self.assertEqual(seqs_aligned[1], '----MA-IKDH')

    def test_initial_positions(self):
        aligned_positions = {"pos_ref":[0,1,2,3], "pos_2":[0,1,2,3]}
        initial_pos = {"pos_ref":[1,2,3,4,5], "pos_2":[0,1,2,10,11]}
        original_positions = get_initial_positions(aligned_positions, initial_pos)
        assert(original_positions=={"pos_ref":[1,2,3,4], "pos_2":[0,1,2,10]})


    def test_get_mrf_pos_to_seq_pos(self):
        seq = "EPA"
        aln_seq = "--E-P-A"
        mrf_pos_to_aln_pos = [k for k in range(len(aln_seq))]
        mrf_pos_to_seq_pos = get_mrf_pos_to_seq_pos(aln_seq, seq, mrf_pos_to_aln_pos)
        assert(mrf_pos_to_seq_pos==[None, None, 0, None, 1, None, 2])


#    def test_get_merge_mrf_pos_to_aln_pos(self):
#        mrf_pos_to_aln_pos_list = [[0,1,None,2],[0,1,2]]
#        aligned_positions_dict = {'pos_ref':[1,2,3],'pos_2':[0,1,2]}
#        merged_mrf_pos_to_aln_pos = get_merge_mrf_pos_to_aln_pos(mrf_pos_to_aln_pos_list, aligned_positions_dict)
#        assert(merged_mrf_pos_to_aln_pos==[0,None,1])
#

if __name__=='__main__':
    unittest.main()
