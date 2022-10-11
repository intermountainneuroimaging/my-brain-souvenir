"""Flywheel gear context parser."""


def parse_config(gear_context):
    """Parse gear config.

    Args:
        gear_context (flywheel_gear_toolkit.GearToolkitContext): context

    Returns:
        (tuple): tuple containing
            - parent container
            - dictionary of input files
            - optional requirements file
    """
    analysis_id = gear_context.destination["id"]
    analysis = gear_context.client.get_analysis(analysis_id)

    get_parent_fn = getattr(gear_context.client, f"get_{analysis.parent.type}")
    parent = get_parent_fn(analysis.parent.id)

    input_file_one = gear_context.get_input_path("additional-input-one")
    input_files = {
        "additional_input_one": input_file_one
    }

    """Commandline interface."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'filename', metavar='path', nargs='+',
        help="Path to image. Multiple paths can be provided."
    )
    parser.add_argument(
        '--mode', type=str, required=False,
        metavar=cfg.mode, default=cfg.mode,
        help="Gif creation mode. Available options are: 'normal', \
            'pseudocolor', 'depth', 'rgb'"
    )
    parser.add_argument(
        '--fps', type=int, required=False,
        metavar=cfg.fps, default=cfg.fps,
        help="Frames per second."
    )
    parser.add_argument(
        '--size', type=float, required=False,
        metavar=cfg.size, default=cfg.size,
        help="Image resizing factor."
    )
    parser.add_argument(
        '--cmap', type=str, required=False,
        metavar=cfg.cmap, default=cfg.cmap,
        help="Color map. Used only in combination with 'pseudocolor' mode."
    )

    args = parser.parse_args()
    cfg.mode = (args.mode).lower()
    cfg.size = args.size
    cfg.fps = args.fps
    cfg.cmap = args.cmap

    # Welcome message
    welcome_str = '{} {}'.format('gif_your_nifti', __version__)
    welcome_decor = '=' * len(welcome_str)
    print('{}\n{}\n{}'.format(welcome_decor, welcome_str, welcome_decor))

    print('Selections:')
    print('  mode = {}'.format(cfg.mode))
    print('  size = {}'.format(cfg.size))
    print('  fps  = {}'.format(cfg.fps))




    return parent, input_files
