import os
import glob
from PIL import Image

base_dir = '/Users/saravanan/Projects/cloud/docs/images/comparison'
pdf_dir = os.path.join(base_dir, 'pdf_pages')

for img in sorted(glob.glob(os.path.join(base_dir, '*.png'))):
    im = Image.open(img)
    w, h = im.size
    aspect = w / h
    # calculate height at width 4.6 inches
    target_w = 4.6
    calc_h = target_w / aspect
    print(f"{os.path.basename(img):30s} -> size: {w}x{h} | aspect: {aspect:.2f} | height at 4.6 in: {calc_h:.2f} in")
