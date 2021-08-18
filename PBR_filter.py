# Written by Dr Daniel Buscombe, Marda Science LLC
# for the USGS Coastal Change Hazards Program
#
# MIT License
#
# Copyright (c) 2021, Marda Science LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from tkinter import filedialog
from tkinter import *
import os, sys, getopt
import numpy as np
from imageio import imread, imwrite
import matplotlib.pyplot as plt
import numpy as np
from skimage.color import rgb2hsv, hsv2rgb
# from glob import glob
from skimage.restoration import denoise_wavelet, estimate_sigma, rolling_ball

from functools import partial
# rescale_sigma=True required to silence deprecation warnings
_denoise_wavelet = partial(denoise_wavelet, rescale_sigma=True)
from skimage import util

# import warnings filter
from warnings import simplefilter
# ignore all future warnings
simplefilter(action='ignore', category=RuntimeWarning)

# =========================================================
def rescale(dat,mn,mx):
    """
    rescales an input dat between mn and mx
    """
    m = np.nanmin(dat.flatten())
    M = np.nanmax(dat.flatten())
    return (mx-mn)*(dat-m)/(M-m)+mn

# =========================================================
def sharpen(Z, radius, do_plot):

    sigma_est = estimate_sigma(Z, multichannel=True, average_sigmas=False)
    region = denoise_wavelet(Z, multichannel=True, rescale_sigma=True, wavelet_levels=6, convert2ycbcr=True,
                              method='BayesShrink', mode='soft', sigma=np.max(sigma_est)*5)
    original = rescale(region,0,255)

    Zo = np.ma.filled(original, fill_value=np.nan).copy()
    hsv = rgb2hsv(Zo)
    im = (0.299 * Zo[:,:,0] + 0.5870*Zo[:,:,1] + 0.114*Zo[:,:,2])
    im[Z[:,:,0]==0]=0

    ##https://scikit-image.org/docs/dev/auto_examples/segmentation/plot_rolling_ball.html#sphx-glr-auto-examples-segmentation-plot-rolling-ball-py
    ##background = rolling_ball(im, radius=100)
    image_inverted = util.invert(im)
    background_inverted = rolling_ball(image_inverted, radius=radius)
    filtered_image_inverted = image_inverted - background_inverted
    filtered_image = util.invert(filtered_image_inverted)
    background = util.invert(background_inverted)

    background[np.isnan(background)] = 0
    background[np.isinf(background)] = 0
    intensity = (im/background)
    intensity[np.isnan(intensity)] = 0
    intensity[np.isinf(intensity)] = 0
    intensity = (255*intensity).astype('uint8')

    sharpened = hsv2rgb(np.dstack([hsv[:,:,0], hsv[:,:,1], intensity]))

    sharpened[:,:,0] = rescale(sharpened[:,:,0],Z[:,:,0].min(), Z[:,:,0].max())
    sharpened[:,:,1] = rescale(sharpened[:,:,1],Z[:,:,1].min(), Z[:,:,2].max())
    sharpened[:,:,2] = rescale(sharpened[:,:,2],Z[:,:,2].min(), Z[:,:,1].max())
    sharpened = (sharpened).astype('uint8')

    if do_plot:
        plt.figure(figsize=(12,12))
        plt.subplot(231); plt.imshow(Z); plt.axis('off'); plt.title('a)', loc='left')
        plt.subplot(232); plt.imshow(original.astype('uint8')); plt.axis('off'); plt.title('b)', loc='left')

        plt.subplot(233); plt.imshow(background, cmap='gray'); plt.axis('off'); plt.title('c)', loc='left')

        plt.subplot(234); plt.imshow(im, cmap='gray'); plt.axis('off'); plt.title('d)', loc='left')
        plt.subplot(235); plt.imshow(intensity, cmap='gray'); plt.axis('off'); plt.title('e)', loc='left')

        plt.subplot(236); plt.imshow(sharpened, cmap='gray'); plt.axis('off'); plt.title('f)', loc='left')

        # plt.show()
        plt.savefig(f.replace('.jpg','_filt_fig_breakdown.png'), dpi=300, bbox_inches='tight')
        plt.close()

    return sharpened.astype('uint8')


#============================================================
# =========================================================

def do_filter(f, radius, do_plot):
    Z = imread(f)
    #radius = 3
    sharpened = sharpen(Z, radius, do_plot)
    imwrite(f.replace('.jpg','_filt.png'),sharpened)

    if do_plot:
        plt.subplot(221); plt.imshow(Z); plt.axis('off')
        plt.subplot(222); plt.imshow(sharpened); plt.axis('off')
        plt.subplot(223); plt.imshow(Z[:250,:250,:]); plt.axis('off')
        plt.subplot(224); plt.imshow(sharpened[:250,:250,:]); plt.axis('off')
        # plt.show()
        plt.savefig(f.replace('.jpg','_filt_fig.png'), dpi=300, bbox_inches='tight')
        plt.close()

###==================================================================
#===============================================================
if __name__ == '__main__':

    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv,"h:r:p:")
    except getopt.GetoptError:
        print('python PBR_filter.py -r radius (px) -doplot 0 (1)')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('Example usage python PBR_filter.py -r 5')
            print('Example usage python PBR_filter.py -r 6 -p 1')
            sys.exit()
        elif opt in ("-r"):
            radius = arg
            radius = int(radius)
        elif opt in ("-p"):
            do_plot = arg
            do_plot = int(do_plot)

    if 'do_plot' not in locals():
        do_plot = 0
    if 'radius' not in locals():
        radius = 3
    print("PBR: pan-sharpen with background subtraction and radius %i" % (radius))

    #files = glob('*.jpg')
    root = Tk()
    files = filedialog.askopenfilenames(initialdir = "./",title = "Select image file",filetypes = (("image file","*.jpg"),("all files","*.*")))
    root.withdraw()
    print("%s files selected" % (len(files)))

    for f in files:
        print(f)
        do_filter(f,radius, do_plot)
