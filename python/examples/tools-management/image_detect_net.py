#!/usr/bin/env python3
#
# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

import sys
import argparse
import threading
import requests
from jetson_inference import imageNet, detectNet
from jetson_utils import videoSource, videoOutput, cudaFont, Log
import tkinter as tk
from tkinter import messagebox
import csv
from datetime import datetime

#LINE header
url = "https://notify-api.line.me/api/notify"
access_token = 'your LINE token'        # write your LINE token
headers = {'Authorization': 'Bearer ' + access_token}


def start_gui():
    # make a window
    root = tk.Tk()
    root.title("products management tool")

    # make labels
    label = tk.Label(root, text="products management")
    label.pack(pady=10)

    def log_action(action, who, what):
        '''
        input CSV
        action: lend or return
        who: unknown, handsome or pretty
        what: objects that can be borrowed
        '''
        with open('action_log.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([action, who, what, timestamp])

        return timestamp
    
    # lend button click
    def on_lend_click():
        with detected_objects_lock:
            what = detected_objects.copy()
        if classLabel and what:
            timestamp = log_action('lend', classLabel, ', '.join(what))
            info = ("Information", f"{classLabel} borrowed {', '.join(what)} at {timestamp}")
            message = info
            payload = {'message': message}
            r = requests.post(url, headers=headers, params=payload,)
            messagebox.showinfo("Information", f"{classLabel} borrowed {', '.join(what)} at {timestamp}")
            
            
    # return button click
    def on_return_click():
        with detected_objects_lock:
            what = detected_objects.copy()
        if classLabel and what:
            timestamp = log_action('return', classLabel, ', '.join(what))
            info = ("Information", f"{classLabel} returned {', '.join(what)} at {timestamp}")
            message = info
            payload = {'message': message}
            r = requests.post(url, headers=headers, params=payload,)
            messagebox.showinfo("Information", f"{classLabel} returned {', '.join(what)} at {timestamp}")
            

    # make buttons
    lend_button = tk.Button(root, text="lend", command=on_lend_click)   # lend
    lend_button.pack(pady=10)
    return_button = tk.Button(root, text="return", command=on_return_click)     # return
    return_button.pack(pady=10)

    root.mainloop()     # loop


# parse the command line
parser = argparse.ArgumentParser(description="Classify and locate objects in a live camera stream using image recognition and object detection DNNs.", 
                                 formatter_class=argparse.RawTextHelpFormatter, 
                                 epilog=imageNet.Usage() + detectNet.Usage() + videoSource.Usage() + videoOutput.Usage() + Log.Usage())

parser.add_argument("input", type=str, default="", nargs='?', help="URI of the input stream")
parser.add_argument("output", type=str, default="", nargs='?', help="URI of the output stream")
parser.add_argument("--classification_network", type=str, default="googlenet", help="pre-trained image classification model to load (see below for options)")
parser.add_argument("--detection_network", type=str, default="ssd-mobilenet-v2", help="pre-trained object detection model to load (see below for options)")
parser.add_argument("--topK", type=int, default=1, help="show the topK number of class predictions (default: 1)")
parser.add_argument("--overlay", type=str, default="box,labels,conf", help="detection overlay flags (e.g. --overlay=box,labels,conf)\nvalid combinations are:  'box', 'labels', 'conf', 'none'")
parser.add_argument("--threshold", type=float, default=0.5, help="minimum detection threshold to use") 

try:
    args = parser.parse_known_args()[0]
except:
    print("")
    parser.print_help()
    sys.exit(0)

# load the networks
# note: to hard-code the paths to load a model, the following API can be used:
#
# classification_net = imageNet(model="/jetson-inference/python/training/classification/models/tools/resnet18.onnx", 
#                               labels="/jetson-inference/python/training/classification/data/tools/labels.txt", 
#                               input_blob="input_0", 
#                               output_blob="output_0")

classification_net = imageNet(args.classification_network, sys.argv)
detection_net = detectNet(args.detection_network, sys.argv, args.threshold)

# create video sources & outputs
input = videoSource(args.input, argv=sys.argv)
output = videoOutput(args.output, argv=sys.argv)
font = cudaFont()

dic = {}
obj_lst = ["keyboard", "mouse", "cup", "bottle", "cell phone", "book"]
detected_objects = []
classLabel = "unknown"

# rock
detected_objects_lock = threading.Lock()

# Create and start the GUI thread
gui_thread = threading.Thread(target=start_gui)
gui_thread.start()

# process frames until EOS or the user exits
while True:
    # capture the next image
    img = input.Capture()

    if img is None: # timeout
        continue  

    
    # classify the image and get the topK predictions
    predictions = classification_net.Classify(img, topK=args.topK)

    # draw predicted class labels
    for n, (classID, confidence) in enumerate(predictions):
        classLabel = classification_net.GetClassLabel(classID)
        confidence *= 100.0

        dic[classLabel] = None
        print(f"imagenet:  {confidence:05.2f}% class #{classID} ({classLabel})")

        font.OverlayText(img, text=f"{confidence:05.2f}% {classLabel}", 
                            x=5, y=5 + n * (font.GetSize() + 5),
                            color=font.White, background=font.Gray40)
    
    # detect objects in the image (with overlay)
    detections = detection_net.Detect(img, overlay="none")
    display_objs = []
    objs = []
    img_height, img_width, img_channels = img.shape
    camera_bottom_detect = [d for d in detections if d.Center[1] > img_height/2]

    # print the detections
    print("detected {:d} objects in image".format(len(camera_bottom_detect)))

    for detection in camera_bottom_detect:
        label = detection_net.GetClassDesc(detection.ClassID)
        print(f"detected object: {label}")
        print(detection)

        if label in obj_lst:
            print(True)
            display_objs.append(detection)
            objs.append(label)

    dic[classLabel] = objs

    # detected_objects rock and update
    with detected_objects_lock:
        detected_objects = objs

    for k, v in dic.items():
        print(f"[RESULT]{k}: {v}")
    detection_net.Overlay(img, display_objs, overlay=args.overlay)
                        
    # render the image
    output.Render(img)

    # update the title bar
    output.SetStatus("Classification: {:s} | Detection: {:s} | Network {:.0f} FPS".format(classification_net.GetNetworkName(), args.detection_network, classification_net.GetNetworkFPS()))

    # print out performance info
    classification_net.PrintProfilerTimes()
    detection_net.PrintProfilerTimes()

    # exit on input/output EOS
    if not input.IsStreaming() or not output.IsStreaming():
        break
