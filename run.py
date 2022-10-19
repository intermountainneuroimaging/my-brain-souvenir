#!/usr/bin/env python3
"""My Brain Souvenir entrypoint."""
import logging
import os.path

import flywheel
import sys
import subprocess as sp
from io import StringIO
from flywheel_gear_toolkit.utils.curator import HierarchyCurator
from flywheel_gear_toolkit.utils import walker
from fw_gear_souvenir import parser
from fw_gear_souvenir import gif_nifti
from flywheel_gear_toolkit import GearToolkitContext
import nipype.interfaces.fsl as fsl
import json

log = logging.getLogger(__name__)

__version__ = "0.2.0"

class Curator(HierarchyCurator):

    def curate_project(self, project: flywheel.Project):
        pass

    def curate_subject(self, subject: flywheel.Subject):
        pass

    def curate_session(self, session: flywheel.Session):
        pass

    def curate_acquisition(self, acquisition: flywheel.Acquisition):
        parents = acquisition.parents
        current_project = gtk_context.client.get(parents.project)
        workdir = str(gtk_context.work_dir)

        # generate modalities list
        modalities = gtk_context.config["modalities"].replace(" ","").split(",")
        # check if acquisition meets criteria
        flag = False
        for file in acquisition['files']:
            if file['type'] == 'nifti' and file['classification']['Measurement'][0] in modalities and "ignore-BIDS" not in acquisition.label:
                # download file
                basename, ext = file['name'].split(os.extsep, 1)
                filepath = os.path.join(workdir, acquisition['label'] + os.extsep + ext)
                file.download(filepath)

                # generate brain image
                gen_image(filepath, workdir, acquisition)

                log.info("My Brain Souvenir stored for acquisition %s", acquisition.label)
                flag = True

        if not flag:
            log.info("skipping acquisition %s", acquisition.label)

        # set return code
        return_code = 0

        return return_code

def gen_image(filepath, workdir=None, acquisition=None):

    # pull config settings
    mode = gtk_context.config['gif-mode']
    fps = gtk_context.config['frames-per-second']
    size = gtk_context.config['image-size']

    # Welcome message
    welcome_str = '{} {}'.format('gif_your_nifti', __version__)
    welcome_decor = '=' * len(welcome_str)
    log.info('{}\n{}\n{}'.format(welcome_decor, welcome_str, welcome_decor))

    log.info('Selections:')
    log.info('  mode = {}'.format(mode))
    log.info('  size = {}'.format(size))
    log.info('  fps  = {}'.format(fps))

    # --- deface input ---
    if gtk_context.config['deface']:
        run_pydeface(filepath)

    # --- BET input ---
    if gtk_context.config['brain-extract']:
        run_bet(filepath)

    # --- build souvenir ---

    # Determine gif creation mode
    if mode in ['normal', 'pseudocolor', 'depth']:
        if mode == 'normal':
            img = gif_nifti.write_gif_normal(filepath, size, fps)
        elif mode == 'pseudocolor':
            if gtk_context.config.get('colormap') != None:
                cmap = gtk_context.config['colormap']
                log.info('  cmap = {}'.format(cmap))
                img = gif_nifti.write_gif_pseudocolor(filepath, size, fps, cmap)
            else:
                log.info('  cmap not set')
                img = gif_nifti.write_gif_pseudocolor(filepath, size, fps)
        elif mode == 'depth':
            img = gif_nifti.write_gif_depth(filepath, size, fps)
    else:
        log.error("Mode: %m not supported, exiting now")

    # build pdf
    footnote = '"My Brain Image" was adapted from gif_your_nifti toolbox (www.github.com/miykael/gif_your_nifti)'
    basename, ext = filepath.split(os.extsep, 1)
    pdf_filename = filepath.replace(ext, 'pdf')
    gif_nifti.write_pdf(img, footnote=footnote, outfile=pdf_filename)


def run_with_single_input(gtk_context, input_files):
    workdir = str(gtk_context.work_dir)

    # generate brain image
    file_id = gtk_context.get_input("nifti")["object"]["file_id"]
    file = gtk_context.client.get_file(file_id)

    acquisition_id = file.parents["acquisition"]
    acquisition = gtk_context.client.get_acquisition(acquisition_id)

    # put input file in work directory
    os.system("cp " + input_files["nifti"] + " " + workdir)

    filepath = os.path.join(workdir, file["name"])

    gen_image(filepath, workdir, acquisition)

    log.info("My Brain Souvenir stored for file %s", file["name"])

    # set return code
    return_code = 0
    return return_code

def run_pydeface(filepath):
    prc = sp.Popen(
        "pydeface "+filepath,
        shell=True,
        stdout=sp.PIPE,
        stderr=sp.PIPE, universal_newlines=True
    )
    stdout, stderr = prc.communicate()

def run_bet(filepath):
    mybet = fsl.BET(in_file=filepath, out_file=filepath)
    result = mybet.run()

def cleanup(context):
    """
        Execute a series of steps to store outputs on the proper containers.

        Args:
            context: The gear context object
                containing the 'gear_dict' dictionary attribute with keys/values
                utilized in the called helper functions.
        """
    # copy all output files to output dir
    searchfiles = sp.Popen(
        "cd " + context.work_dir.absolute().as_posix() + "; cp *.gif " + context.output_dir.absolute().as_posix(),
        shell=True,
        stdout=sp.PIPE,
        stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = searchfiles.communicate()

    # copy all output files to output dir
    searchfiles = sp.Popen(
        "cd " + context.work_dir.absolute().as_posix() + "; cp *.pdf " + context.output_dir.absolute().as_posix(),
        shell=True,
        stdout=sp.PIPE,
        stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = searchfiles.communicate()


if __name__ == "__main__":
    # TODO add Singularity capability

    # Get access to gear config, inputs, and sdk client if enabled.
    # with GearToolkitContext() as gtk_context:
    with GearToolkitContext(config_path='/home/mri/Documents/flywheel-apps/my-brain-souvenir/my-brain-souvenir-0.2.0_inc0.0RC3-63472a895e9df877a1d99db5/config.json'\
                            , manifest_path='/home/mri/Documents/flywheel-apps/my-brain-souvenir/my-brain-souvenir-0.2.0_inc0.0RC3-63472a895e9df877a1d99db5/manifest.json') as gtk_context:
        gtk_context.init_logging()
        # config_dictionary = gtk_context.config_json['inputs']

        # pull api key from hidden file if present (generally file located here... $HOME/.config/flywheel/user.json)
        # apikey_file = os.path.join(os.environ["HOME"], '.config/flywheel/user.json')
        # apikey_file = "/flywheel/v0/user.json"
        # if os.path.exists(apikey_file):
        #     f = open(apikey_file)
        #     data = json.load(f)
        #     os.environ['API-KEY'] = data["key"]
        # config_dictionary['api-key']['key'] = os.environ['API-KEY']

        parent, input_files = parser.parse_config(gtk_context)

        # if nifti file is passed use for brain image
        if input_files["nifti"]:
            return_code = run_with_single_input(gtk_context, input_files)

        # else -- find relevant images
        else:
            # create custom curator
            my_curator = Curator()

            # create walker to walk the parent level
            root_walker = walker.Walker(
                parent,
                depth_first=my_curator.config.depth_first,
                reload=my_curator.config.reload,
                stop_level=my_curator.config.stop_level,
            )

            for container in root_walker.walk():
                return_code = my_curator.curate_container(container)

        cleanup(gtk_context)

        sys.exit(return_code)
