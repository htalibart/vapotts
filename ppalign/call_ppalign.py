import ctypes
import time
import pandas as pd

from ppalign.compute_scores import *
from makepotts.potts_object import *
from makepotts.potts_model import *
import comutils.files_management as fm

import pkg_resources
PPALIGN_CPP_LIBRARY = pkg_resources.resource_filename('ppalign', 'ppalign_solver.so')

PPALIGN_SOLVER = ctypes.CDLL(PPALIGN_CPP_LIBRARY)
INFINITY = 1000000000

def align_two_potts_models(mrfs, output_folder, insert_costs=None, n_limit_param=INFINITY, iter_limit_param=1000, t_limit=36000, disp_level=1, epsilon_sim=0.005, w_percent=100, w_norm_min=0, remove_w_where_conserved=False, use_w=True, use_v=True, gamma=1.0, theta=0.9, stepsize_min=0.000000005, nb_non_increasing_steps_max=500, alpha_w=1, sim_min=-100, offset_v=0, remove_v0=False, insertion_penalties_coefficient=1, gap_open=8, gap_extend=0, free_end_gaps=False, ignore_gap_symbol=True, **kwargs):

    if (ignore_gap_symbol):
        for mrf in mrfs:
            if mrf.w.shape[2]==21:
                mrf.w[:,:,20,:]=0
                mrf.w[:,:,:,20]=0
            if mrf.v.shape[1]==21:
                mrf.v[:,20]=0

    # handle output files and folder
    if not output_folder.is_dir():
        fm.create_folder(output_folder)
    aln_res_file = fm.get_aln_res_file_name(output_folder)
    info_res_file = fm.get_info_res_file_name(output_folder)
    aln_with_gaps_res_file = fm.get_aln_with_gaps_res_file(output_folder)

    # total PPalign time starts now
    time_start = time.time()
  

   # DEFINE TYPES FOR CTYPES
    c_float_p = ctypes.POINTER(ctypes.c_float) # pointer to float
    c_int_p = ctypes.POINTER(ctypes.c_int) # pointer to int


    # FIELDS
    if use_v:
        if remove_v0: # remove v0 from every field if necessary
            vs = [mrf.v-np.tile(get_background_v0(q=mrf.v.shape[1],**kwargs),(mrf.ncol,1)) for mrf in mrfs]
        else:
            vs = [mrf.v for mrf in mrfs]
        # always give C++ program field vectors with q=21 => add zeroes if necessary
        vs_after_pad = []
        for v in vs:
            new_v = np.zeros((v.shape[0],21))
            if ignore_gap_symbol: # ignore gap symbol in similarity score
                new_v[:,:20]=v[:,:20]
            else:
                new_v[:,:v.shape[1]]=v
            vs_after_pad.append(new_v)
        v_flats = [np.ascontiguousarray(v.flatten()) for v in vs_after_pad] # flatten for ctypes
    else:
        v_flats = [np.ascontiguousarray(np.zeros((mrf.v.shape[0],21))).flatten() for mrf in mrfs]
    c_vs = [vflat.astype(np.float32).ctypes.data_as(c_float_p) for vflat in v_flats]


    # COUPLINGS
    if use_w:
        edges_maps = [get_edges_map(mrf, w_percent, w_norm_min, remove_w_where_conserved) for mrf in mrfs]
        # always give C++ program coupling matrices 21x21 => add zeroes if necessary
        ws = []
        for mrf in mrfs:
            new_w = np.zeros((mrf.w.shape[0],mrf.w.shape[1],21,21))
            if ignore_gap_symbol:
                new_w[:,:,:20,:20] = mrf.w[:,:,:20,:20]
            else:
                new_w[:,:,:mrf.w.shape[2],:mrf.w.shape[3]]=mrf.w
            ws.append(new_w)
        w_flats = [np.ascontiguousarray(w.flatten()) for w in ws]
    else: # if no coupling: edge map where edges are all 0
        edges_maps = [np.zeros((mrf.w.shape[0:2])) for mrf in mrfs]
        w_flats = [np.ascontiguousarray(np.zeros((mrf.w.shape[0],mrf.w.shape[1],21,21))).flatten() for mrf in mrfs]
    c_ws = [wflat.astype(np.float32).ctypes.data_as(c_float_p) for wflat in w_flats]

    selfcomps = [compute_selfscore(mrf, edges_map, alpha_w=alpha_w, remove_v0=remove_v0, offset_v=offset_v, use_v=use_v, use_w=use_w, **kwargs) for mrf, edges_map in zip(mrfs, edges_maps)] #s(A,A) and s(B,B)
    epsilon = get_epsilon(epsilon_sim, selfcomps) # epsilon so that 2*s(A,B)/(s(A,A)+s(B,B)) < @epsilon_sim
    score_min = (1/2)*sim_min*sum(selfcomps); # stop computation if LB < score_min 

    c_edges_maps = [np.ascontiguousarray(edges_map.flatten(), dtype=np.int32).ctypes.data_as(c_int_p) for edges_map in edges_maps]


    # INSERTIONS
    if insert_costs is None:
        if free_end_gaps:
            print("insert costs is None, filling with gap open = ",gap_open," and gap extend = ", gap_extend, " (external gap costs = 0)")
            insert_opens = [np.ascontiguousarray(np.hstack((np.zeros((1)), np.ones((mrfs[mrf_ind].ncol-1))*gap_open, np.zeros(1)))) for mrf_ind in range(2)]
            insert_extends = [np.ascontiguousarray(np.hstack((np.zeros((1)), np.ones((mrfs[mrf_ind].ncol-1))*gap_extend, np.zeros(1)))) for mrf_ind in range(2)]
        else:
            print("insert costs is None, filling with gap open = ",gap_open," and gap extend = ", gap_extend)
            insert_opens = [np.ascontiguousarray(np.ones((mrfs[mrf_ind].ncol+1))*gap_open) for mrf_ind in range(2)]
            insert_extends = [np.ascontiguousarray(np.ones((mrfs[mrf_ind].ncol+1))*gap_extend) for mrf_ind in range(2)]
    else:
        insert_opens = [np.multiply(np.ascontiguousarray(insert_costs[mrf_ind]['open']),insertion_penalties_coefficient) for mrf_ind in range(2)]
        insert_extends = [np.multiply(np.ascontiguousarray(insert_costs[mrf_ind]['extend']),insertion_penalties_coefficient) for mrf_ind in range(2)]
        if free_end_gaps:
            for mrf_ind in range(2):
                for end in [0,-1]:
                    insert_opens[mrf_ind][end]=0
                    insert_extends[mrf_ind][end]=0
    c_insert_opens = [insert_open.astype(np.float32).ctypes.data_as(c_float_p) for insert_open in insert_opens]
    c_insert_extends = [insert_extend.astype(np.float32).ctypes.data_as(c_float_p) for insert_extend in insert_extends]


    
    # CHECK IF OK
    for mrf_ind in range(2):
        assert(len(insert_opens[mrf_ind]==mrfs[mrf_ind].ncol+1))
        assert(len(insert_extends[mrf_ind]==mrfs[mrf_ind].ncol+1))


    PPALIGN_SOLVER.call_from_python.argtypes=[c_float_p, c_float_p, c_float_p, c_float_p, ctypes.c_int, ctypes.c_int, c_int_p, c_int_p, ctypes.c_double, ctypes.c_double, c_float_p, c_float_p, c_float_p, c_float_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_double]

    PPALIGN_SOLVER.call_from_python(*c_vs, *c_ws, *[ctypes.c_int(mrf.ncol) for mrf in mrfs], *c_edges_maps, *[ctypes.c_double(selfcomp) for selfcomp in selfcomps], *c_insert_opens, *c_insert_extends, ctypes.c_char_p(str(aln_res_file).encode('utf-8')), ctypes.c_char_p(str(info_res_file).encode('utf-8')), ctypes.c_char_p(str(aln_with_gaps_res_file).encode('utf-8')), ctypes.c_int(n_limit_param), ctypes.c_int(iter_limit_param), ctypes.c_double(t_limit), ctypes.c_int(disp_level), ctypes.c_double(epsilon), ctypes.c_double(gamma), ctypes.c_double(theta), ctypes.c_double(stepsize_min), ctypes.c_int(nb_non_increasing_steps_max), ctypes.c_double(score_min), ctypes.c_double(alpha_w), ctypes.c_double(offset_v))

    total_computation_time = time.time()-time_start

    df = pd.read_csv(info_res_file)
    df['total_time'] = total_computation_time
    df.to_csv(info_res_file, index=False, na_rep='nan')
    infos_solver = fm.get_infos_solver_dict_from_ppalign_output_file(info_res_file)
    
    if not math.isnan(df['similarity_global']):
        aligned_positions_dict = fm.get_aligned_positions_dict_from_ppalign_output_file(aln_res_file)
        aligned_positions_with_gaps_dict = fm.get_aligned_positions_with_gaps_dict_from_ppalign_output_file(aln_with_gaps_res_file)
    else:
        aligned_positions_dict = {}
        aligned_positions_with_gaps_dict = {}

    return aligned_positions_dict, aligned_positions_with_gaps_dict, infos_solver


def align_two_objects(objects, output_folder, **kwargs):
    return align_two_potts_models([o.potts_model for o in objects], output_folder, **kwargs)

