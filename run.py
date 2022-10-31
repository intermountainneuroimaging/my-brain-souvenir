#!/usr/bin/env python3
"""My Brain Souvenir entrypoint."""
import logging
import os.path
import flywheel
import sys
import subprocess as sp
import imageio
from flywheel_gear_toolkit.utils.curator import HierarchyCurator
from flywheel_gear_toolkit.utils import walker
from fw_gear_souvenir import parser
from fw_gear_souvenir import gif_nifti
from flywheel_gear_toolkit import GearToolkitContext
import nipype.interfaces.fsl as fsl

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
        modalities = gtk_context.config["image-modalities"].replace(" ", "").split(",")
        if gtk_context.config.get("image-features"):
            features = gtk_context.config["image-features"].replace(" ", "").split(",")
        # check if acquisition meets criteria
        flag = False
        for file in acquisition['files']:
            if (
                    file['type'] == 'nifti' and
                    "ignore-BIDS" not in acquisition.label
            ):
                # secondary check for modalities
                if not file['classification'].get('Measurement') or file['classification'].get('Measurement')[
                    0] not in modalities:
                    continue

                # secondary check for features
                if 'features' in locals():
                    # check for feature match
                    if not file['classification'].get('Features') or file['classification'].get('Features')[
                        0] not in features:
                        continue

                # check if localizer
                if not file['classification'].get('Intent') or file['classification'].get('Intent')[
                    0] == "Localizer":
                    continue


                # download file
                basename, ext = file['name'].split(os.extsep, 1)
                filepath = os.path.join(workdir, acquisition['label'] + os.extsep + ext).replace(" ", "").replace("-",
                                                                                                                  "_")
                file.download(filepath)

                log.info("Building souvenir for file: %s", filepath)

                # generate brain image include pydeface or brain extraction if selected
                gen_image(filepath, workdir, acquisition)

                log.info("My Brain Souvenir stored for acquisition %s", acquisition.label)
                flag = True

                cleanup(gtk_context)

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
    mosaic = gtk_context.config['image-mosaic']

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
    searchfiles = sp.Popen(
        "cd " + gtk_context.work_dir.absolute().as_posix() + "; ls *.nii.gz ",
        shell=True,
        stdout=sp.PIPE,
        stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = searchfiles.communicate()

    filelist = stdout.strip("\n").split("\n")
    os.chdir(gtk_context.work_dir.absolute().as_posix())

    for file in filelist:
        # Determine gif creation mode

        if mode in ['normal', 'pseudocolor', 'depth']:
            if mode == 'normal':
                if mosaic:
                    img = gif_nifti.write_gif_normal(file, size, fps)
                else:
                    img = gif_nifti.write_gif_singleview_normal(file, size, fps)
            elif mode == 'pseudocolor':
                if gtk_context.config.get('colormap') != None:
                    cmap = gtk_context.config['colormap']
                    log.info('  cmap = {}'.format(cmap))
                    img = gif_nifti.write_gif_pseudocolor(file, size, fps, cmap)
                else:
                    log.info('  cmap not set')
                    img = gif_nifti.write_gif_pseudocolor(file, size, fps)
            elif mode == 'depth':
                img = gif_nifti.write_gif_depth(file, size, fps)
        else:
            log.error("Mode: %m not supported, exiting now")

        # build pdf/jpeg
        footnote = 'Incomplete study for research purposes only, not for medical use.'
        basename, ext = file.split(os.extsep, 1)
        image_filename = file.replace(ext, 'jpg')
        gif_nifti.write_image(file, format="jpg", footnote=footnote, outfile=image_filename)

        # Write a video file
        writer = imageio.get_writer(file.replace(ext, 'mov'), fps=fps)
        for im in img:
            writer.append_data(im)
        writer.close()

        # ADD DEPTH IMAGE FOR BRAIN IMAGES
        if "brain" in file:
            img = gif_nifti.write_gif_depth(file, size, fps)


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

    # generate gifs and jep images (run pydeface and brain extraction if need be)
    gen_image(filepath, workdir, acquisition)

    log.info("My Brain Souvenir stored for file %s", file["name"])

    cleanup(gtk_context)

    # set return code
    return_code = 0
    return return_code


def run_pydeface(filepath):
    prc = sp.Popen(
        "pydeface " + filepath,
        shell=True,
        stdout=sp.PIPE,
        stderr=sp.PIPE, universal_newlines=True
    )
    stdout, stderr = prc.communicate()
    log.info("Running pydeface")
    log.info(stdout)
    log.info(stderr)


def run_bet(filepath):
    log.info("Running brain extraction")
    mybet = fsl.BET(in_file=filepath, out_file=filepath.replace(".nii.gz", "_brain.nii.gz"), frac=0.4)
    result = mybet.run()


def cleanup(context):
    """
        Execute a series of steps to store outputs on the proper containers.

        Args:
            context: The gear context object
                containing the 'gear_dict' dictionary attribute with keys/values
                utilized in the called helper functions.
        """

    # check which outputs should be stored for final gear "outputs"
    fmt = gtk_context.config["output-format"]
    if fmt == "all" or fmt == "gif":
        # copy all output files to output dir
        searchfiles = sp.Popen(
            "cd " + context.work_dir.absolute().as_posix() + "; cp *.gif " + context.output_dir.absolute().as_posix(),
            shell=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE, universal_newlines=True
        )
        stdout, _ = searchfiles.communicate()

    if fmt == "all" or fmt == "jpg":
        # copy all output files to output dir
        searchfiles = sp.Popen(
            "cd " + context.work_dir.absolute().as_posix() + "; cp *.jpg " + context.output_dir.absolute().as_posix(),
            shell=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE, universal_newlines=True
        )
        stdout, _ = searchfiles.communicate()

    if fmt == "all" or fmt == "pdf":
        # copy all output files to output dir
        searchfiles = sp.Popen(
            "cd " + context.work_dir.absolute().as_posix() + "; cp *.pdf " + context.output_dir.absolute().as_posix(),
            shell=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE, universal_newlines=True
        )
        stdout, _ = searchfiles.communicate()

    if fmt == "all" or fmt == "mov":
        # copy all output files to output dir
        searchfiles = sp.Popen(
            "cd " + context.work_dir.absolute().as_posix() + "; cp *.mov " + context.output_dir.absolute().as_posix(),
            shell=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE, universal_newlines=True
        )
        stdout, _ = searchfiles.communicate()

    # copy all output files to output dir
    rmfiles = sp.Popen(
        "cd " + context.work_dir.absolute().as_posix() + "; rm -Rf * ",
        shell=True,
        stdout=sp.PIPE,
        stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = rmfiles.communicate()


if __name__ == "__main__":
    # TODO add Singularity capability

    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gtk_context:
    # with GearToolkitContext(config_path='/flywheel/v0/config.json', manifest_path='/flywheel/v0/manifest.json',
    #                             gear_path='/flywheel/v0') as gtk_context:
        gtk_context.init_logging()
        os.environ["PATH"] = "/root/.cache/pypoetry/virtualenvs/my-brain-souvenir-n1iZ4KF1-py3.8/bin:/usr/bin/ffmpeg:" + \
                             os.environ["PATH"]
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

        sys.exit(return_code)
