#!/usr/bin/env python

import rospy
from alfred_clever_lamp.msg import Mode, UrlToOpen, PointingObject
import http.server
import threading
import os
import shutil
import socket
from dotenv import load_dotenv
import cv2
from PIL import Image as PIL_Image



''' IMAGE PATHS '''
ARM_CONTROL_IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/0_arm_control.png"
HOMEWORK_MODE_IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/1_homework.png"
GENERATE_IMAGE_MODE_IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/2_generate_image.png"
DRAW_MODE_IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/3_draw.png"
ALLIGN_PAPER_IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/3_1_draw.png"

''' SETUP GEMINI API '''
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
GEMINI_API = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"

''' PROMPTS '''
PROMPT_HOMEWORK_MODE = ""
PROMPT_GENERATE_IMAGE_MODE = ""
PROMPT_DRAW_MODE = ""



''' HELPER FUNCTIONS '''
def create_custom_page_from_image(image_path):
    """
    Copies the image to a temporary web-accessible directory,
    spins up a local HTTP server (if not already running),
    and returns a URL list that Chrome can open.
    
    Returns:
        list[str]: A list containing the URL to the served HTML page.
    """
    # --- Config ---
    SERVE_DIR = "/tmp/alfred_web"
    PORT = 8765

    # 1. Prepare the serving directory
    os.makedirs(SERVE_DIR, exist_ok=True)

    # 2. Copy the image into the serving directory
    image_filename = os.path.basename(image_path)
    dest_path = os.path.join(SERVE_DIR, image_filename)
    shutil.copy2(image_path, dest_path)

    # 3. Generate a simple HTML page that displays the image
    html_filename = image_filename.rsplit(".", 1)[0] + ".html"
    html_path = os.path.join(SERVE_DIR, html_filename)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Alfred - {image_filename}</title>
    <style>
        body {{
            margin: 0;
            background: #111;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        img {{
            max-width: 100%;
            max-height: 100vh;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <img src="{image_filename}" alt="{image_filename}" />
</body>
</html>"""
    with open(html_path, "w") as f:
        f.write(html_content)

    # 4. Start the HTTP server in a background thread (only once)
    if not _is_port_in_use(PORT):
        handler = http.server.SimpleHTTPRequestHandler
        server = http.server.HTTPServer(("0.0.0.0", PORT), handler)
        # Change the server's working directory to SERVE_DIR
        os.chdir(SERVE_DIR)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        rospy.loginfo(f"HTTP server started at http://localhost:{PORT}")

    # 5. Return the URL(s)
    url = f"http://localhost:{PORT}/{html_filename}"
    rospy.loginfo(f"Image available at: {url}")
    return url
def _is_port_in_use(port: int) -> bool:
    """Check if a local TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

''' CALLBACKS '''
def pointing_object_callback(msg):
    global pointing_object
    pointing_object = True
    rospy.loginfo(f"Received pointing object: {msg.ID}")

def mode_callback(msg):
    global pointing_object
    rospy.loginfo(pointing_object)

    mode = msg.mode
    url_msg = UrlToOpen()
    rospy.loginfo(f"Received mode: {mode}")

    if mode == 0:
        rospy.loginfo("Arm Control Mode Activated")
        url_msg.scene_description = "User in Arm Control Mode, taking familiarity with robot."
        url_msg.current_mode = mode
        urls = [create_custom_page_from_image(image_path=ARM_CONTROL_IMAGE_PATH)]
        url_msg.url_list = urls
        url_msg.i = 0
        rospy.loginfo(f"Publishing URLs: {url_msg.url_list}")
        pub.publish(url_msg)


    elif mode == 1:
        rospy.loginfo("Homework Mode Activated")

        if pointing_object:
            url_msg.scene_description = "pass"
            url_msg.current_mode = mode
            urls = [create_custom_page_from_image(image_path=HOMEWORK_MODE_IMAGE_PATH), "http://gemini"]
            url_msg.url_list = urls
            url_msg.i = 0
            rospy.loginfo(f"Publishing URLs: {url_msg.url_list}")
            pub.publish(url_msg)
        pointing_object = False


    elif mode == 2:
        rospy.loginfo("Generate Image Mode Activated")

        if pointing_object:
            url_msg.scene_description = "pass"
            url_msg.current_mode = mode
            urls = [create_custom_page_from_image(image_path=GENERATE_IMAGE_MODE_IMAGE_PATH), "http://gemini"]
            url_msg.url_list = urls
            url_msg.i = 0
            rospy.loginfo(f"Publishing URLs: {url_msg.url_list}")
            pub.publish(url_msg)
        pointing_object = False


    elif mode == 3:
        rospy.loginfo("Draw Mode Activated")

        if pointing_object:
            url_msg.scene_description = "pass"
            url_msg.current_mode = mode
            urls = [create_custom_page_from_image(image_path=DRAW_MODE_IMAGE_PATH), create_custom_page_from_image(image_path=ALLIGN_PAPER_IMAGE_PATH), "http://gemini"]
            url_msg.url_list = urls
            url_msg.i = 0
            rospy.loginfo(f"Publishing URLs: {url_msg.url_list}")
            pub.publish(url_msg)
        pointing_object = False

            
    else:
        rospy.logwarn("Unknown mode received")

''' MAIN '''
if __name__ == '__main__':
    pointing_object = False

    rospy.init_node('open_mode')
    pub = rospy.Publisher('/urls_to_open', UrlToOpen, queue_size=1)

    rospy.Subscriber('/mode', Mode, callback=mode_callback, queue_size=1)
    rospy.Subscriber('/point_image', PointingObject, callback=pointing_object_callback, queue_size=1)
    rospy.spin()