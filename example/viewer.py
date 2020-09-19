import pyk4a
from pyk4a import Config, PyK4A, ColorResolution

import cv2
import numpy as np

k4a = PyK4A(Config(color_resolution=ColorResolution.RES_720P,
                   depth_mode=pyk4a.DepthMode.NFOV_UNBINNED,
                   synchronized_images_only=True, ))
k4a.connect()

# getters and setters directly get and set on device
k4a.whitebalance = 4500
assert k4a.whitebalance == 4500
k4a.whitebalance = 4510
assert k4a.whitebalance == 4510


img_color, img_ir, img_depth, img_pcl = k4a.get_capture(transform_to_color=False,pcl=True)
out = cv2.VideoWriter('out.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 20.0, (img_ir.shape[1],img_ir.shape[0]))

while 1:
    img_color, img_ir, img_depth, img_pcl = k4a.get_capture(transform_to_color=False,pcl=True)

    if img_color is not None:
        cv2.imshow('k4a color', img_color[:, :, :3])
    if img_ir is not None:
        img_ir= np.clip(0,255,img_ir/64 ).astype(np.uint8)
        cv2.imshow('k4a ir', img_ir)
        out.write(np.stack([img_ir,img_ir,img_ir]).transpose([1,2,0]).copy())
    if img_depth is not None:
        img_depth = (img_depth.astype(float)/ np.max(img_depth) )
        cv2.imshow('k4a depth', img_depth)
    if img_pcl is not None:
        img_pcl = img_pcl.astype(np.float)
        img_pcl = img_pcl-np.min(img_pcl.reshape(-1,3),axis=0)
        img_pcl = img_pcl/np.max(img_pcl.reshape(-1,3),axis=0)
        cv2.imshow('k4a depth', np.hstack([x for x in img_pcl.transpose([2,0,1])]))


    key = cv2.waitKey(10)
    if key != -1:
        cv2.destroyAllWindows()
        out.release()
        break
k4a.disconnect()
