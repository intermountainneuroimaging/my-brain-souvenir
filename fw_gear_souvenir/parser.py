"""Flywheel gear context parser."""
import argparse

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

    nifti_file = gear_context.get_input_path("nifti")
    input_files = {
        "nifti": nifti_file
    }

    return parent, input_files
