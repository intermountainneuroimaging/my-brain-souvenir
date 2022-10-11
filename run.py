#!/usr/bin/env python3
"""My Brain Souvenir entrypoint."""
import logging
import os.path

import flywheel
import pandas as pd
import sys
import subprocess as sp
from io import StringIO
from flywheel_gear_toolkit.utils.curator import HierarchyCurator
from flywheel_gear_toolkit.utils import walker
from fw_gear_souvenir import parser
from fw_gear_souvenir import gif_nifti
from flywheel_gear_toolkit import GearToolkitContext
import json

log = logging.getLogger(__name__)


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
        # check if acquisition meets criteria
        flag = False
        for file in acquisition['files']:
            if file['type'] == 'nifti' and file['classification']['Measurement'][0] in ['T1',
                                                                                        'T2'] and "ignore-BIDS" not in acquisition.label:
                # download file
                basename, ext = file['name'].split(os.extsep, 1)
                filepath = os.path.join(workdir, acquisition['label'] + os.extsep + ext)
                file.download(filepath)

                # build souvenir
                img = gif_nifti.write_gif_normal(filepath)

                # build pdf
                footnote = '"My Brain Image" was adapted from gif_your_nifti toolbox (www.github.com/miykael/gif_your_nifti)'
                pdf_filename = filepath.replace(ext, 'pdf')
                gif_nifti.write_pdf(img, footnote=footnote, outfile=pdf_filename)

                log.info("My Brain Souvenir stored for acquisition %s", acquisition.label)
                flag = True

        if not flag:
            log.info("skipping acquisition %s", acquisition.label)

        # set return code
        return_code = 0

        return return_code


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
    with GearToolkitContext() as gtk_context:
        # with GearToolkitContext(config_path='/flywheel/v0/config.json'\
        #                         , manifest_path='/flywheel/v0/manifest.json') as gtk_context:
        gtk_context.init_logging()
        config_dictionary = gtk_context.config_json['inputs']

        # pull api key from hidden file if present (generally file located here... $HOME/.config/flywheel/user.json)
        if os.path.exists('/flywheel/v0/user.json'):
            f = open('/flywheel/v0/user.json')
            data = json.load(f)
            os.environ['API-KEY'] = data["key"]
        config_dictionary['api-key']['key'] = os.environ['API-KEY']

        parent, input_files = parser.parse_config(gtk_context)

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
