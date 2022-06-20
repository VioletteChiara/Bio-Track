from tkinter import *
import numpy as np
import cv2
from BioTrack import UserMessages
import os

""" These functions are based on the work of members of the learnopencv team.
https://github.com/spmallick/learnopencv/blob/master/VideoStabilization/video_stabilization.py"""


f = open("Files/Language", "r")
Language=f.read()
f.close()
Messages = UserMessages.Mess[Language]

def find_pts(Vid, Prem_Im):
    if len(Prem_Im.shape)>2:
        prev_gray=cv2.cvtColor(Prem_Im,cv2.COLOR_BGR2GRAY)
    else:
        prev_gray = Prem_Im.copy()


    quality = 0.05
    found=False
    while not found and quality > 0.01:
        prev_pts = cv2.goodFeaturesToTrack(prev_gray,
                                           maxCorners=200,
                                           qualityLevel=quality,
                                           minDistance=30,
                                           blockSize=3)
        quality = quality - 0.01

        if len(prev_pts) > 10:
            found = True

    Vid.Stab[1]=prev_pts
    return(prev_pts)



def find_best_position(Vid, Prem_Im, frame, show, scale=1):
    prev_pts=Vid.Stab[1]
    try:
        if prev_pts==None:
            prev_pts=find_pts(Vid,Prem_Im)
    except:
        pass

    if len(Prem_Im.shape)>2:
        prev_gray=cv2.cvtColor(Prem_Im,cv2.COLOR_BGR2GRAY)
    else:
        prev_gray = Prem_Im.copy()

    curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h = prev_gray.shape[0]
    w = prev_gray.shape[1]


    if len(prev_pts)>1:
        choose_pts=prev_pts.copy()
        curr_pts, status, err = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None)

        assert choose_pts.shape == curr_pts.shape

        # Filter only valid points
        idx = np.where(status == 1)[0]
        choose_pts = choose_pts[idx]
        curr_pts = curr_pts[idx]

        if len(choose_pts)>1:

            # Find transformation matrix
            m, _ = cv2.estimateAffinePartial2D(choose_pts, curr_pts)  # will only work with OpenCV-3 or less

            # Extract traslation
            dx = -m[0, 2]
            dy = -m[1, 2]

            # Extract rotation angle
            da = -np.arctan2(m[1, 0], m[0, 0])

            # Reconstruct transformation matrix accordingly to new values
            m = np.zeros((2, 3), np.float32)
            m[0, 0] = np.cos(da)
            m[0, 1] = -np.sin(da)
            m[1, 0] = np.sin(da)
            m[1, 1] = np.cos(da)
            m[0, 2] = dx
            m[1, 2] = dy

            # Apply affine wrapping to the given frame
            frame_stabilized = cv2.warpAffine(frame, m, (w, h))

        else:
            frame_stabilized = frame
    else:
        frame_stabilized=frame

    if show:
        first_im = np.copy(Prem_Im)
        cv2.putText(first_im, Messages["Stab3"], (max(1,int(scale*30)), max(1,int(scale*30))), cv2.FONT_HERSHEY_PLAIN, max(1,scale*2), (255, 255, 255), max(2,int(scale*5)))
        cv2.putText(first_im, Messages["Stab3"], (max(1,int(scale*30)), max(1,int(scale*30))), cv2.FONT_HERSHEY_PLAIN, max(1,scale*2), (0, 0, 0), max(1,int(scale*3)))

        cv2.putText(frame, Messages["Stab4"], (max(1,int(scale*30)), max(1,int(scale*30))), cv2.FONT_HERSHEY_PLAIN, max(1,scale*2), (255, 255, 255), max(2,int(scale*5)))
        cv2.putText(frame, Messages["Stab4"], (max(1,int(scale*30)), max(1,int(scale*30))), cv2.FONT_HERSHEY_PLAIN, max(1,scale*2), (0, 0, 0), max(1,int(scale*3)))

        cv2.putText(frame_stabilized, Messages["Stab5"], (max(1,int(scale*30)), max(1,int(scale*30))), cv2.FONT_HERSHEY_PLAIN, max(1,scale*2), (255, 255, 255), max(2,int(scale*5)))
        cv2.putText(frame_stabilized, Messages["Stab5"], (max(1,int(scale*30)), max(1,int(scale*30))), cv2.FONT_HERSHEY_PLAIN, max(1,scale*2), (0, 0, 0), max(1,int(scale*3)))

        for pt in range(len(prev_pts)):
            cv2.circle(first_im, (int(prev_pts[pt][0][0]), int(prev_pts[pt][0][1])), max(1,int(scale*3)), (255,0,0), -1)
            cv2.putText(first_im,str(pt),(int(prev_pts[pt][0][0])+max(1,int(scale*3)), int(prev_pts[pt][0][1])-max(1,int(scale*3))),cv2.FONT_HERSHEY_PLAIN,max(1,scale*1.5),(255,0,0),max(1,int(scale*2)))


        for pt in range(len(curr_pts)):
            cv2.circle(frame, (int(curr_pts[pt][0][0]), int(curr_pts[pt][0][1])), max(1,int(scale*3)), (0,255,200), -1)
            cv2.putText(frame, str(pt), (int(curr_pts[pt][0][0])+max(1,int(scale*3)), int(curr_pts[pt][0][1])-max(1,int(scale*3))), cv2.FONT_HERSHEY_PLAIN, max(1,scale*1.5), (0, 255, 200),max(1,int(scale*2)))


        frame_out1 = cv2.hconcat([frame, frame_stabilized])
        frame_out2 = cv2.hconcat([first_im, np.zeros_like(first_im)])
        frame_out = cv2.vconcat([frame_out2, frame_out1])

        # Store transformation
        return(frame_out)
    else:
        return (frame_stabilized)

def fixBorder(frame):
  s = frame.shape
  # Scale the image 4% without moving the center
  T = cv2.getRotationMatrix2D((s[1]/2, s[0]/2), 0, 1.04)
  frame = cv2.warpAffine(frame, T, (s[1], s[0]))
  return frame