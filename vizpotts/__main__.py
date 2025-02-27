import argparse
import pathlib

from makepotts.potts_object import *
from vizpotts.vizpotts import *
from makepotts.potts_model import *
from comutils import files_management as fm
from ppalign.manage_positions import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--potts_models', help="Potts model (msgpack files)", type=pathlib.Path, nargs='+', default=[])
    parser.add_argument('-pf', '--potts_folders', help="Potts objects (folders generated by MakePotts)", type=pathlib.Path, nargs='+', default=[])
    parser.add_argument('-i', '--i_index', help="i index", type=int, default=None)
    parser.add_argument('-j', '--j_index', help="j index", type=int, default=None)
    parser.add_argument('-1', '--start_at_1', help="Start numbering at 1", action='store_true', default=True), 
    parser.add_argument('-0', '--start_at_0', help="Start numbering at 0", action='store_true', default=False), 
    parser.add_argument('-20', '--force_q_20', help="Act as if all parameters have only q=20 parameters even if they have more", action='store_true', default=False), 
    parser.add_argument('-va', '--visualize_alignment', help="Visualize aligned scores, requires PPalign output folder path (-o option) or aln.csv (-aln) and README.txt (-ar)", action='store_true', default=False), 
    parser.add_argument('-af', '--alignment_folder', help="PPalign output folder", type=pathlib.Path, default=None),
    parser.add_argument('-aln', '--aln_file', help="PPalign output csv file (aln.csv)", type=pathlib.Path, default=None), 
    parser.add_argument('-ar', '--alignment_readme', help="PPalign parameters to compute scores (README.txt)", type=pathlib.Path, default=None), 
    parser.add_argument('-v', '--v_only', help="Only plot vi parameters", action='store_true', default=False), 
    parser.add_argument('-vn', '--v_norms_only', help="Only plot vi norms", action='store_true', default=False), 
    parser.add_argument('-wn', '--w_norms_only', help="Only plot wij norms", action='store_true', default=False), 
    parser.add_argument('-ip', '--insertion_penalties_only', help="Only plot insertion penalties", action='store_true', default=False), 
    parser.add_argument('-alph', '--alphabetical', help="Use alphabetical amino acid order", action='store_true', default=False), 
    parser.add_argument('--w_percent', help="%% couplings considered (wij with lowest norms are set to 0)", default=100, type=float)
    args = vars(parser.parse_args())

    if args["alphabetical"]:
        alphabet=ALPHABET
    else:
        alphabet="CSTPAGNDEQHRKMILVFYW-"


    start_at_1 = args["start_at_1"] and not args["start_at_0"]

    potts_models = [Potts_Model.from_msgpack(potts_model_file) for potts_model_file in args["potts_models"]]
    potts_objects = []
    for potts_folder in args["potts_folders"]:
        po = Potts_Object.from_folder(potts_folder, use_insertion_penalties=True)
        potts_objects.append(po)
        potts_models.append(po.potts_model)

    if args["force_q_20"]:
        for pm in potts_models:
            pm.v = pm.v[:,:20]
            pm.w = pm.w[:,:,:20,:20]

    if args["alignment_readme"] is not None:
        params = fm.get_parameters_from_readme_file(args["alignment_readme"])
    elif args["alignment_folder"] is not None:
        params = fm.get_parameters_from_readme_file(args["alignment_folder"]/"README.txt")
    else:
        params = {"v_rescaling_function":"identity", "w_rescaling_function":"identity"}
        print("No PPalign parameters were provided, using default")
    potts_models = [get_rescaled_potts_model(pm, **params) for pm in potts_models]


    if 'w_percent' not in params:
        params['w_percent'] = args['w_percent']
    if 'w_norm_min' not in params:
        params['w_norm_min'] = 0
    if 'remove_w_where_conserved' not in params:
        params['remove_w_where_conserved'] = False
    for i in range(len(potts_models)):
        potts_models[i] = get_potts_model_without_unused_couplings(potts_models[i], params['w_percent'], params['w_norm_min'], params['remove_w_where_conserved'])


    if (args["i_index"] is not None) and (args["j_index"] is not None):
        for mrf in potts_models:
            i = args["i_index"]
            j = args["j_index"]
            if start_at_1:
                i-=1
                j-=1
            plot_one_wij(mrf.w[i][j], show_figure=False, alphabet=alphabet)
        plt.show()
    else:
        if args["visualize_alignment"]:
            if args["aln_file"] is not None:
                aln_file = args["aln_file"]
            elif args["alignment_folder"] is not None:
                aln_file = args["alignment_folder"]/"aln.csv"
            else:
                raise Exception("aln.csv needed (provide aln.csv with -aln option or output folder with -o option)")


            if len(potts_objects)==2:
                label_dict = get_seq_positions_from_aln_dict(fm.get_aligned_positions_dict_from_ppalign_output_file(aln_file), potts_objects)
                print("labeling with sequences")
            else:
                label_dict=None
                print("labeling with Potts models")

            visualize_v_alignment_with_scalar_product(potts_models, aln_file, start_at_1=start_at_1, show_figure=False, alphabet=alphabet, label_dict=label_dict, **params)
            visualize_v_w_scores_alignment(potts_models, aln_file, start_at_1=start_at_1, show_figure=False, alphabet=alphabet, label_dict=label_dict, **params)
        else:
            for mrf in potts_models:
                if args["v_only"]:
                    visualize_v_parameters(mrf.v, start_at_1=start_at_1, show_figure=False, alphabet=alphabet)
                elif args["v_norms_only"]:
                    visualize_v_norms(mrf.get_v_norms(), start_at_1=start_at_1, show_figure=False)
                elif args["w_norms_only"]:
                    visualize_w_norms(mrf.get_w_norms(), start_at_1=start_at_1, show_figure=True)
                elif args["insertion_penalties_only"]:
                    insertion_penalties = po.get_insertion_penalties()
                    if insertion_penalties is None:
                        raise Exception("no insertion penalties found")
                    visualize_insertion_penalties(insertion_penalties, show_figure=False)
                else:
                    visualize_mrf(mrf, start_at_1=start_at_1, show_figure=False, alphabet=alphabet)
        plt.show()



if __name__ == '__main__':
    main()
