"""Core functions."""

import os
import nibabel as nb
import numpy as np
from matplotlib.cm import get_cmap
from matplotlib.pyplot import figure
import matplotlib.pyplot as plt
from imageio import mimwrite
from skimage.transform import resize
from PIL import Image


def parse_filename(filepath):
    """Parse input file path into directory, basename and extension.

    Parameters
    ----------
    filepath: string
        Input name that will be parsed into directory, basename and extension.

    Returns
    -------
    dirname: str
        File directory.
    basename: str
        File name without directory and extension.
    ext: str
        File extension.

    """
    path = os.path.normpath(filepath)
    dirname = os.path.dirname(path)
    filename = path.split(os.sep)[-1]
    basename, ext = filename.split(os.extsep, 1)
    return dirname, basename, ext


def load_and_prepare_image(filename, size=1):
    """Load and prepare image data.

    Parameters
    ----------
    filename1: str
        Input file (eg. /john/home/image.nii.gz)
    size: float
        Image resizing factor.

    Returns
    -------
    out_img: numpy array

    """
    # Load NIfTI file
    data = nb.load(filename).get_fdata()

    # Pad data array with zeros to make the shape isometric
    maximum = np.max(data.shape)

    out_img = np.zeros([maximum] * 3)

    a, b, c = data.shape
    x, y, z = (list(data.shape) - maximum) / -2

    out_img[int(x):a + int(x),
    int(y):b + int(y),
    int(z):c + int(z)] = data

    out_img /= out_img.max()  # scale image values between 0-1

    # Resize image by the following factor
    if size != 1:
        out_img = resize(out_img, [int(size * maximum)] * 3)

    maximum = int(maximum * size)

    return out_img, maximum


def create_mosaic_normal(out_img, maximum):
    """Create grayscale image.

    Parameters
    ----------
    out_img: numpy array
    maximum: int

    Returns
    -------
    new_img: numpy array

    """
    new_img = np.array(
        [np.hstack((
            np.hstack((
                np.flip(out_img[i, :, :], 1).T,
                np.flip(out_img[:, maximum - i - 1, :], 1).T)),
            np.flip(out_img[:, :, maximum - i - 1], 1).T))
            for i in range(maximum)])

    return new_img


def create_singleview_normal(out_img, maximum, slicedir="y"):
    """Create grayscale image.

    Parameters
    ----------
    out_img: numpy array
    maximum: int

    Returns
    -------
    new_img: numpy array

    """

    if slicedir == "y":
        new_img = np.array(
            [np.flip(out_img[:, maximum - i - 1, :], 1).T
             for i in range(maximum)])

    elif slicedir == "x":
        new_img = np.array(
            [np.flip(out_img[i, :, :], 1).T
             for i in range(maximum)])

    elif slicedir == "z":
        new_img = np.array(
            [np.flip(out_img[:, :, maximum - i - 1], 1).T
             for i in range(maximum)])

    return new_img


def create_mosaic_depth(out_img, maximum):
    """Create an image with concurrent slices represented with colors.

    The image shows you in color what the value of the next slice will be. If
    the color is slightly red or blue it means that the value on the next slide
    is brighter or darker, respectifely. It therefore encodes a certain kind of
    depth into the gif.

    Parameters
    ----------
    out_img: numpy array
    maximum: int

    Returns
    -------
    new_img: numpy array

    """
    # Load normal mosaic image
    new_img = create_mosaic_normal(out_img, maximum)

    # Create RGB image (where red and blue mean a positive or negative shift in
    # the direction of the depicted axis)
    rgb_img = [new_img[i:i + 3, ...] for i in range(maximum - 3)]

    # Make sure to have correct data shape
    out_img = np.rollaxis(np.array(rgb_img), 1, 4)

    # Add the 3 lost images at the end
    out_img = np.vstack(
        (out_img, np.zeros([3] + [o for o in out_img[-1].shape])))

    return out_img


def create_mosaic_RGB(out_img1, out_img2, out_img3, maximum):
    """Create RGB image.

    Parameters
    ----------
    out_img: numpy array
    maximum: int

    Returns
    -------
    new_img: numpy array

    """
    # Load normal mosaic image
    new_img1 = create_mosaic_normal(out_img1, maximum)
    new_img2 = create_mosaic_normal(out_img2, maximum)
    new_img3 = create_mosaic_normal(out_img3, maximum)

    # Create RGB image (where red and blue mean a positive or negative shift
    # in the direction of the depicted axis)
    rgb_img = [[new_img1[i, ...], new_img2[i, ...], new_img3[i, ...]]
               for i in range(maximum)]

    # Make sure to have correct data shape
    out_img = np.rollaxis(np.array(rgb_img), 1, 4)

    # Add the 3 lost images at the end
    out_img = np.vstack(
        (out_img, np.zeros([3] + [o for o in out_img[-1].shape])))

    return out_img


def write_gif_normal(filename, size=1, fps=18):
    """Procedure for writing grayscale image.

    Parameters
    ----------
    filename: str
        Input file (eg. /john/home/image.nii.gz)
    size: float
        Between 0 and 1.
    fps: int
        Frames per second

    """
    # Load NIfTI and put it in right shape
    out_img, maximum = load_and_prepare_image(filename, size)

    # Create output mosaic
    new_img = create_mosaic_normal(out_img, maximum)

    # Figure out extension
    ext = '.{}'.format(parse_filename(filename)[2])

    # Write gif file

    # change image datatype
    new_img = new_img * 255
    new_img = new_img.astype('uint8')

    mimwrite(filename.replace(ext, '.gif'), new_img,
             format='gif', fps=int(fps * size))

    return new_img


def write_gif_singleview_normal(filename, size=1, fps=18):
    """Procedure for writing grayscale image.

    Parameters
    ----------
    filename: str
        Input file (eg. /john/home/image.nii.gz)
    size: float
        Between 0 and 1.
    fps: int
        Frames per second

    """
    # Load NIfTI and put it in right shape
    out_img, maximum = load_and_prepare_image(filename, size)

    # Create output mosaic
    if "cor" in filename:
        slicedir = "y"
        ax = (1, 2)
    elif "sag" in filename:
        slicedir = "x"
        ax = (0, 1)
    else:
        slicedir = "y"
        ax = (1, 2)
    new_img = create_singleview_normal(out_img, maximum, slicedir=slicedir)

    mask = np.all(new_img != 0, axis=ax)
    if np.any(mask):
        new_img = new_img[mask]

    # Figure out extension
    ext = '.{}'.format(parse_filename(filename)[2])

    # Write gif file

    # change image datatype
    new_img = new_img * 255
    new_img = new_img.astype('uint8')

    mimwrite(filename.replace(ext, '.gif'), new_img,
             format='gif', fps=int(fps * size))

    return new_img


def write_gif_depth(filename, size=1, fps=18):
    """Procedure for writing depth image.

    The image shows you in color what the value of the next slice will be. If
    the color is slightly red or blue it means that the value on the next slide
    is brighter or darker, respectifely. It therefore encodes a certain kind of
    depth into the gif.

    Parameters
    ----------
    filename: str
        Input file (eg. /john/home/image.nii.gz)
    size: float
        Between 0 and 1.
    fps: int
        Frames per second

    """
    # Load NIfTI and put it in right shape
    out_img, maximum = load_and_prepare_image(filename, size)

    # Create output mosaic
    new_img = create_mosaic_depth(out_img, maximum)

    # Figure out extension
    ext = '.{}'.format(parse_filename(filename)[2])

    # change image datatype
    new_img = new_img * 255
    new_img = new_img.astype('uint8')

    # Write gif file
    mimwrite(filename.replace(ext, '_depth.gif'), new_img,
             format='gif', fps=int(fps * size))


def write_gif_rgb(filename1, filename2, filename3, size=1, fps=18):
    """Procedure for writing RGB image.

    Parameters
    ----------
    filename1: str
        Input file for red channel.
    filename2: str
        Input file for green channel.
    filename3: str
        Input file for blue channel.
    size: float
        Between 0 and 1.
    fps: int
        Frames per second

    """
    # Load NIfTI and put it in right shape
    out_img1, maximum1 = load_and_prepare_image(filename1, size)
    out_img2, maximum2 = load_and_prepare_image(filename2, size)
    out_img3, maximum3 = load_and_prepare_image(filename3, size)

    if maximum1 == maximum2 and maximum1 == maximum3:
        maximum = maximum1

    # Create output mosaic
    new_img = create_mosaic_RGB(out_img1, out_img2, out_img3, maximum)

    # Generate output path
    out_filename = '{}_{}_{}_rgb.gif'.format(parse_filename(filename1)[1],
                                             parse_filename(filename2)[1],
                                             parse_filename(filename3)[1])
    out_path = os.path.join(parse_filename(filename1)[0], out_filename)

    # Write gif file
    mimwrite(out_path, new_img, format='gif', fps=int(fps * size))

    return new_img


def write_gif_pseudocolor(filename, size=1, fps=18, colormap='hot'):
    """Procedure for writing pseudo color image.

    The colormap can be any colormap from matplotlib.

    Parameters
    ----------
    filename1: str
        Input file (eg. /john/home/image.nii.gz)
    size: float
        Between 0 and 1.
    fps: int
        Frames per second
    colormap: str
        Name of the colormap that will be used.

    """
    # Load NIfTI and put it in right shape
    out_img, maximum = load_and_prepare_image(filename, size)

    # Create output mosaic
    new_img = create_mosaic_normal(out_img, maximum)

    # Transform values according to the color map
    cmap = get_cmap(colormap)
    color_transformed = [cmap(new_img[i, ...]) for i in range(maximum)]
    cmap_img = np.delete(color_transformed, 3, 3)

    # Figure out extension
    ext = '.{}'.format(parse_filename(filename)[2])

    # change image datatype
    cmap_img = cmap_img * 255
    cmap_img = cmap_img.astype('uint8')

    # Write gif file
    mimwrite(filename.replace(ext, '_{}.gif'.format(colormap)),
             cmap_img, format='gif', fps=int(fps * size))

    return cmap_img


def write_image(filename, format="jpg", footnote=None, outfile="myImagePDF.pdf"):
    """
    Use gif image, generated from above functions to save image as pdf
    Args:
        image: 3D array generated from write_gif_normal (or other write_gif_<type>)
        format: image format (jpeg, png, pdf, ...)
        footnote: short message that can be added to the bottom of pdf
        outfile: filename for output file

    Returns:
        saves pdf as output

    """
    # Load NIfTI and put it in right shape
    out_img, maximum = load_and_prepare_image(filename, 1)

    # Create output mosaic
    if "cor" in filename:
        slicedir = "y"
    elif "sag" in filename:
        slicedir = "x"
    else:
        slicedir = "x"

    image = create_singleview_normal(out_img, maximum, slicedir=slicedir)

    # Figure out extension
    ext = '.{}'.format(parse_filename(filename)[2])

    # change image datatype
    image = image * 255
    image = image.astype('uint8')

    # find the middle frame of the gif 3D image
    midframe = round(image.shape[0] / 2)

    # plot image
    figure(figsize=(8, 6), dpi=300, facecolor='black')
    # fig, ax = plt.subplots()
    imgplot = plt.imshow(image[midframe, :, :])
    imgplot.set_cmap('gray')

    # suppress image axes
    imgplot.axes.get_xaxis().set_visible(False)
    imgplot.axes.get_yaxis().set_visible(False)

    # add logo
    path = os.path.dirname(os.path.realpath(__file__))
    im = Image.open(os.path.join(path, 'support_images/INC_rev_center.png'))
    im.thumbnail((300, 300), Image.ANTIALIAS)  # resizes image in-place
    im_width, im_height = im.size
    bbox = plt.gca().get_window_extent()
    plt.figimage(im, xo=600, yo=80, zorder=3, alpha=1, resize=False)

    # add footnote
    plt.figtext(0.5, 0.075, footnote, fontsize="x-small", color="white", horizontalalignment="center",
                verticalalignment="top")

    plt.savefig(outfile, format=format,
                bbox_inches="tight")
