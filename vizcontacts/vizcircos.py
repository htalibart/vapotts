import uuid
import os
import shutil
import math

from comutils import files_management as fm
from vizcontacts.contacts_management import *

# write links in main circos conf file
def write_links(conf_file, coupling_dicts_for_sequence_indexed_by_colors, links_folder, thickness=1):

    for color in coupling_dicts_for_sequence_indexed_by_colors:
        links_filename = links_folder+color+".links"
        with open(links_filename, 'w') as f:
            thick_coeff = 20*thickness
            d = coupling_dicts_for_sequence_indexed_by_colors[color]
            for c in d:
                t = d[c]*thick_coeff
                if (t>=1):
                    f.write(str(c[0]+1)+" 0 1 "+str(c[1]+1)+" 0 1 thickness="+str(t)+"\n")

            # write link in conf_file
            conf_file.write("""
            <link>
            file          = """+links_filename+"""
            color         = """+color+"""
            radius        = 0.99r
            bezier_radius = 0.1r
            thickness     = 5
            </link>
            """) 



# main circos conf file
def write_conf(circos_conf_filename, karyotype_filename, links_folder, output_circos_image, coupling_dicts_for_sequence_indexed_by_colors, thickness=1):
    with open(circos_conf_filename, 'w') as f:
        f.write("""

        karyotype = """+karyotype_filename+"""

       # <plots>
       # <plot>
       # type = histogram
       # file = histogram_filename
       # r1 = 0.99r
       # r0 = 0.80r
       # thickness = 5
       # color = grey
       # extend_bin = no
       # orientation = in
       # </plot>
       # </plots>

        <ideogram>

        <spacing>
        default = 0.005r
        </spacing>

        # ideogram position, thickness and fill
        radius           = 0.90r
        thickness        = 10p
        fill             = yes


        #stroke_thickness = 1
        #stroke_color     = black

        # ideogram labels
        show_label     = yes
        label_with_tag = yes
        label_font     = light
        label_radius   = dims(ideogram,radius_outer) + 0.05r
        label_center   = yes
        label_size     = 20p
        label_color    = black
        label_parallel = no
        label_case     = upper 


        # ideogram cytogenetic bands, if defined in the karyotype file
        show_bands            = yes
        fill_bands            = yes
        band_stroke_thickness = 2
        band_stroke_color     = grey
        band_transparency     = 1

        </ideogram>

        <image>
        <<include etc/image.conf>>
        file* = """+output_circos_image+"""
        </image>

        <links>""")

        write_links(f, coupling_dicts_for_sequence_indexed_by_colors, links_folder, thickness=thickness)

        f.write("""
        </links>

        # RGB/HSV color definitions, color lists, location of fonts,
        # fill patterns
        <<include etc/colors_fonts_patterns.conf>> # included from Circos distribution

        # debugging, I/O an dother system parameters
        <<include etc/housekeeping.conf>> # included from Circos distribution

        """
        )



def get_displayed_position(pos, numbering_type, pdb_file=None, chain_id=None, sequence=None):
    """ returns the position that will be displayed around the Circos circle according to the required numbering type"""
    if numbering_type=='sequence':
        return pos+1
    elif numbering_type=='pdb':
        if (pdb_file is not None) and (chain_id is not None) and (sequence is not None):
            pdb_pos = get_real_pos_to_pdb_pos(pdb_file, chain_id, sequence)[pos]
            if pdb_pos is None:
                return ('#')
            else:
                return pdb_pos
        else:
            raise Exception("No PDB chain / sequence")
    else:
        raise Exception("Unknown numbering type")


# KARYOTYPE
# chr - id label start end color
def write_karyotype(karyotype_filename, sequence, seq_pos_to_mrf_pos, numbering_type, pdb_file=None, chain_id=None):
    with open(karyotype_filename,"w") as f:
        for pos in range(len(sequence)):
            if seq_pos_to_mrf_pos[pos] is None:
                color = "black"
            else:
                color = "dgrey"
            displayed_position = get_displayed_position(pos, numbering_type, pdb_file=pdb_file, chain_id=chain_id, sequence=sequence)
            f.write("chr - "+str(pos+1)+" "+str(displayed_position)+"-"+sequence[pos]+" 0 1 "+color+"\n")


def create_circos(circos_output_folder, coupling_dicts_for_sequence_indexed_by_colors, sequence, seq_pos_to_mrf_pos, numbering_type, pdb_file=None, chain_id=None, output_circos_image=None, thickness=1):
    of = str(circos_output_folder)+'/'
    if not os.path.isdir(of):
        os.mkdir(of)
    karyotype_filename = of+"karyotype.txt"
    circos_conf_filename = of+"main_conf.txt"
    links_folder = of+"links/"
    if not os.path.isdir(links_folder):
        os.mkdir(links_folder)
    tmp_name = str(uuid.uuid4())
    write_karyotype(karyotype_filename, sequence, seq_pos_to_mrf_pos, numbering_type, pdb_file=pdb_file, chain_id=chain_id)
    write_conf(circos_conf_filename, karyotype_filename, links_folder, tmp_name+".png", coupling_dicts_for_sequence_indexed_by_colors, thickness=thickness)
    #os.system("circos -silent -conf "+circos_conf_filename)
    os.system("circos -conf "+circos_conf_filename)
    if output_circos_image is None:
        output_circos_image = pathlib.Path(of+"circos.png")
    output_circos_image_without_extension = '.'.join(str(output_circos_image).split('.')[:-1])
    for extension in [".svg", ".png"]:
        shutil.move(tmp_name+extension, output_circos_image_without_extension+extension)
    print("Circos image can be found at "+str(output_circos_image))


def create_circos_from_potts_object_and_pdb_chain(potts_object, pdb_file=None, chain_id='A', coupling_sep_min=3, top=20, numbering_type='sequence', output_circos_image=None, thickness=1, auto_top=False, wij_cutoff=None, **args):
    couplings_dict = get_contact_scores_for_sequence(potts_object)
    seq_pos_to_mrf_pos = potts_object.get_seq_pos_to_mrf_pos()
    couplings_dict_with_coupling_sep_min = remove_couplings_too_close(couplings_dict, coupling_sep_min)
    if auto_top:
        top = get_elbow_index(couplings_dict_with_coupling_sep_min)
    if wij_cutoff is not None:
        top = get_cutoff_smaller_than(couplings_dict_with_coupling_sep_min, wij_cutoff)
    if top is not None:
        smaller_couplings_dict = get_smaller_dict(couplings_dict_with_coupling_sep_min, top)
    else:
        smaller_couplings_dict = OrderedDict()
    coupling_dicts_for_sequence_indexed_by_colors = get_colored_true_false_dicts(smaller_couplings_dict, pdb_file, chain_id, real_sequence=potts_object.sequence, colors={True:'green', False:'red'})
    circos_output_folder = str(potts_object.folder.absolute())+"/circos_output"
    create_circos(circos_output_folder, coupling_dicts_for_sequence_indexed_by_colors, potts_object.sequence, seq_pos_to_mrf_pos, numbering_type, pdb_file=pdb_file, chain_id=chain_id, output_circos_image=output_circos_image, thickness=thickness)



def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--potts_folder', help="Feature folder", type=pathlib.Path, required=True)
    parser.add_argument('--pdb_file', help="PDB file", type=pathlib.Path, default=None)
    parser.add_argument('-i', '--pdb_id', help="PDB id", required=False)
    parser.add_argument('-cid', '--chain_id', help="PDB chain id (default : A)", default='A')
    parser.add_argument('-sep', '--coupling_sep_min', help="Min. nb residues between members of a coupling (default : 3)", type=int, default=3)
    parser.add_argument('-n', '--top', help="Nb of couplings displayed (default : 20)", type=int, default=20)
    parser.add_argument('--auto_top', help="Nb couplings displayed = elbow of the score curve (default : False)", default=False, action='store_true')
    parser.add_argument('--wij_cutoff', help="||wij|| <= wij_cutoff (default : no cutoff)", default=None, type=float)
    parser.add_argument('-num', '--numbering_type', help="Use the same numbering type around the circle as sequence (sequence) or PDB structure (pdb) (default : numbering as sequence)", default='sequence')
    parser.add_argument('-o', '--output_circos_image', help="Output circos image (default : [potts_folder]/circos_output/circos.png)", type=pathlib.Path, default=None)
    parser.add_argument('-t', '--thickness', help="Couplings thickness factor (default : 1)", type=float, default=1)

    args = vars(parser.parse_args(args))

    fm.check_if_dir_ok(args["potts_folder"])

    potts_object = Potts_Object.from_folder(args['potts_folder'])
    if args['pdb_file'] is None:
        name = str(potts_object.folder)+'/'+args['pdb_id']
        args['pdb_file'] = fm.fetch_pdb_file(args['pdb_id'], name)
    fm.check_if_file_ok(args["pdb_file"])
    create_circos_from_potts_object_and_pdb_chain(potts_object, **args)

if __name__=="__main__":
    main()

