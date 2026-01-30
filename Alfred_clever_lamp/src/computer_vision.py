#!/usr/bin/env python3

''' IMPORT MODULES '''
import sys
import os
import cv2
import re
from PIL import Image as PIL_Image
import google.generativeai as genai
import mediapipe as mp
from dotenv import load_dotenv
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
from my_functions import countFingers, detectHandsLandmarks, search_yt, circular_list, open_url, format_math
import webbrowser
import googleapiclient.discovery
import rospy
from tf.transformations import euler_from_quaternion
import geometry_msgs.msg
from geometry_msgs.msg import PoseStamped
import math
import subprocess
import pyautogui
import time

''' SET UP HANDS MODULE '''
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False,max_num_hands=2,min_detection_confidence=0.5)
hands_videos = mp_hands.Hands(static_image_mode=False,max_num_hands=2,min_detection_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils


''' SET UP YOUTUBE '''


''' SET UP MATH EQUATION MODULE '''


''' SET UP GEMINI MODULE '''
#load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../scripts/.env"))
#GEMINI_API = os.environ.get("GEMINI_API_KEY")
#genai.configure(api_key=GEMINI_API)
#model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25") #("gemini-2.0-pro-exp-02-05") # gemini-1.5-pro # 
''' SET UP GEMINI MODULE '''
import requests
import base64
from io import BytesIO

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../scripts/.env"))
GEMINI_API = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API:
    raise RuntimeError("GEMINI_API_KEY not found. Put it in a .env file or export it.")

def gemini_generate_with_image(prompt_text: str, image_path: str, model: str = "gemini-2.0-flash") -> str:
    # Load image using cv2 and convert to PIL
    cv2_image = cv2.imread(image_path)
    if cv2_image is None:
        raise RuntimeError(f"Could not load image: {image_path}")
    
    # Convert BGR (cv2) to RGB (PIL)
    cv2_image_rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    pil_image = PIL_Image.fromarray(cv2_image_rgb)
    
    # Convert PIL image to base64
    buffered = BytesIO()
    pil_image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Prepare API request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_base64
                        }
                    },
                    {
                        "text": prompt_text
                    }
                ]
            }
        ]
    }
    
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates in response: {data}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


''' SET UP WEBCAM'''
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 600)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 500)


''' SET UP YOUTUBE API '''
YOUTUBE_API = os.environ.get("YOUTUBE_DATA_APY_KEY")
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API)


''' HANDS GESTURE RECOGNITION '''
def recognizeGestures(image, fingers_statuses, count):
    output_image = image.copy()
    hands_labels = ['RIGHT', 'LEFT']
    hands_gestures = {'RIGHT': "UNKNOWN", 'LEFT': "UNKNOWN"}
    for hand_index, hand_label in enumerate(hands_labels):
        if count[hand_label] == 2  and fingers_statuses[hand_label+'_MIDDLE'] and fingers_statuses[hand_label+'_INDEX']:
            hands_gestures[hand_label] = "V SIGN"
        elif count[hand_label] == 3 and fingers_statuses[hand_label+'_THUMB'] and fingers_statuses[hand_label+'_INDEX'] and fingers_statuses[hand_label+'_PINKY']:
            hands_gestures[hand_label] = "SPIDERMAN SIGN"
        elif count[hand_label] == 5:
            hands_gestures[hand_label] = "HIGH-FIVE SIGN"
        elif (count[hand_label] == 1 and fingers_statuses[hand_label+'_INDEX']) or (count[hand_label] == 2 and fingers_statuses[hand_label+'_INDEX'] and fingers_statuses[hand_label+'_THUMB']):
            hands_gestures[hand_label] = "POINTING"
            screenshot_path = "pointing_object.jpg"
            cv2.imwrite(screenshot_path, frame)
    return output_image, hands_gestures


''' INITIALIZE VARIABLES '''
pointing_detected_frames = 0    # -> Counts consecutive frames of pointing detection
pointing_stable_threshold = 30  # -> Number of frames to consider as stable
cooldown_counter = 0            # -> Counter for cooldown
cooldown_frames = 30            # -> Cooldown period in frames
is_processing = False           # -> Flag to indicate if processing is ongoing
speack_back = False              # -> to make Alfred speack back
videos = []                     # -> List of videos to play
global ply_index
ply_index = 0                   # -> Index of the video to play
youtube_OR_media = "youtube"    # -> last point was for random immage (youtube) or for math equation (media)?


''' SET UP ROS NODE '''
global initial_yaw
global accumulated_rotation
# Initialize variables
initial_yaw = None
accumulated_rotation = 0

def normalize_angle(angle):
    """Normalize angle to be between -pi and pi"""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle

def pose_callback(msg):
    global initial_yaw
    global accumulated_rotation
    global ply_index
    
    ''' if lift marker, pause video '''
    hight = msg.pose.position.z
    if (hight > 0.9 or hight < -0.9) and youtube_OR_media == "youtube":
        # Try to focus or open Chrome
        subprocess.run(['xdotool', 'search', '--onlyvisible', '--class', 'chrome', 'windowactivate'], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pyautogui.press('space')
        subprocess.run(['xdotool', 'search', '--onlyvisible', '--class', 'firefox', 'windowactivate'], 
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    ''' detect ros messages '''
    _, _, current_yaw = euler_from_quaternion([
        msg.pose.orientation.x, 
        msg.pose.orientation.y, 
        msg.pose.orientation.z, 
        msg.pose.orientation.w
    ])
    
    # Initialize reference yaw if this is the first callback
    if initial_yaw is None:
        initial_yaw = current_yaw
        print("Initial yaw set to %.2f degrees" % (current_yaw * 180.0 / math.pi))
        return
    
    # Calculate angular difference
    yaw_diff = current_yaw - initial_yaw
    
    # Increment or decrement accumulated rotation based on direction
    if yaw_diff > 0:
        accumulated_rotation += 1
    elif yaw_diff < 0:
        accumulated_rotation -= 1
    
    # Check thresholds for video changes
    rotation_threshold = 180  # Adjust based on desired sensitivity
    
    if accumulated_rotation > rotation_threshold and len(videos) >= 2 and youtube_OR_media == "youtube":
        # Play previous video
        print("\n\nPREVIOUS VIDEO")
        ply_index = circular_list(ply_index, direction=-1, length=len(videos))
        print(f"Playing previous YouTube video: {videos[ply_index]}")
        open_url(videos[ply_index], youtube_OR_media)
        accumulated_rotation = 0  # Reset after triggering
        
    elif accumulated_rotation < -rotation_threshold and len(videos) >= 2 and youtube_OR_media == "youtube":
        # Play next video
        print("\n\nNEXT VIDEO")
        ply_index = circular_list(ply_index, direction=1, length=len(videos))
        print(f"Playing next YouTube video: {videos[ply_index]}")
        open_url(videos[ply_index], youtube_OR_media)
        accumulated_rotation = 0  # Reset after triggering
    
    # Update initial yaw for the next comparison
    initial_yaw = current_yaw

rospy.init_node('computer_vision')
rospy.Subscriber("/natnet_ros/umh_5/pose", PoseStamped, callback=pose_callback, queue_size=1)

''' MAIN LOOP '''
while cap.isOpened():
    try:
        ret, frame = cap.read()
        frame = cv2.flip(frame, -1)
        if not ret:
            break

        ''' if not processing and cooldown is complete, proceed with detection '''
        if not is_processing and cooldown_counter == 0:
            output_image, results = detectHandsLandmarks(frame, hands, draw=True)
            cv2.imshow('Webcam with Hand Landmarks', output_image)

            ''' count fingers and detect gestures '''
            if results.multi_hand_landmarks:
                output_image, fingers_statuses, count = countFingers(frame, results)
                output_image, hands_gestures = recognizeGestures(output_image, fingers_statuses, count)

                ''' check for pointing gesture reached stable threshold '''
                if "POINTING" in hands_gestures.values():
                    pointing_detected_frames += 1
                    if pointing_detected_frames%5 == 0:
                        print(f"Pointing gesture detected for {pointing_detected_frames} frames.")
                else:
                    pointing_detected_frames = 0

                ''' if pointing gesture is stable, proceed with processing '''
                if pointing_detected_frames >= pointing_stable_threshold:
                    is_processing = True

                    ''' save image for processing '''
                    screenshot_path = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/pointing_object.jpg"
                    cv2.imwrite(screenshot_path, frame)

                    #''' Generate links and description using GEMINI '''
                    #image = cv2.imread(screenshot_path)
                    #image = PIL_Image.fromarray(image)
                    #cv2.waitKey(2000)
#
                    #''' generate links and description using GEMINI '''
                    #prompt = """
                    #I need a very careful structured response from you:
                    #    give me in your prompt first, just 2 words to describe what I am pointing at with my index finger.
                    #    Then give me a wikipedia link to dive deeper into the topic.
                    #    DON'T PROVIDE WITH NOTHING ELSE, NO DESCRIPTIONS, NO CONTEXT, NO ADDITIONAL INFORMATION, NO PARENTESIS OR STRANGE INDEXTING OF THE TEXT.
                    #    Planar text, 2 raws, 2 words and one link to wikipedia.
                    #    --------------------------------------------------
                    #    Otherwise, if you detect math equations: In that case the precise structure is the following:
                    #        - in the first line write 'MATH EQUATION DETECTED'
                    #        - a wikipedia link to explanation of the princiuple in the math equation. Just give the link, no parentesis, no description, etc...
                    #        - in the following lines, write at at most 3 steps and the solution. Each step in different line.
                    #    --------------------------------------------------
                    #    Otherwise, if you detect code (python, C++, Java, etc...): In that case the precise structure is very similar to math one:
                    #        - in the first line write 'MATH EQUATION DETECTED' 
                    #        - a wikipedia link to explanation of the codeing principle. Just give the link, no parentesis, no description, etc...
                    #        - in the following lines, write at at most 3 lines of code (for example fix line with errors) and result of the code if possible. Each step in different line.
                    #"""
                    #
                    #contents = [image, prompt]
                    #print("\n-------thinking--------")
                    #response = model.generate_content(contents)
                    #response_text = response.text
                    #print("\n-------Response--------")
                    #print(response_text)
                    ''' generate links and description using GEMINI '''
                    cv2.waitKey(2000)

                    prompt = """
                    I need a very careful structured response from you:
                        give me in your prompt first, just 2 words to describe what I am pointing at with my index finger.
                        Then give me a wikipedia link to dive deeper into the topic.
                        DON'T PROVIDE WITH NOTHING ELSE, NO DESCRIPTIONS, NO CONTEXT, NO ADDITIONAL INFORMATION, NO PARENTESIS OR STRANGE INDEXTING OF THE TEXT.
                        Planar text, 2 raws, 2 words and one link to wikipedia.
                        --------------------------------------------------
                        Otherwise, if you detect math equations: In that case the precise structure is the following:
                            - in the first line write 'MATH EQUATION DETECTED'
                            - a wikipedia link to explanation of the princiuple in the math equation. Just give the link, no parentesis, no description, etc...
                            - in the following lines, write at at most 3 steps and the solution. Each step in different line.
                        --------------------------------------------------
                        Otherwise, if you detect code (python, C++, Java, etc...): In that case the precise structure is very similar to math one:
                            - in the first line write 'MATH EQUATION DETECTED' 
                            - a wikipedia link to explanation of the codeing principle. Just give the link, no parentesis, no description, etc...
                            - in the following lines, write at at most 3 lines of code (for example fix line with errors) and result of the code if possible. Each step in different line.
                    """
                    
                    print("\n-------thinking--------")
                    response_text = gemini_generate_with_image(prompt, screenshot_path, model="gemini-2.0-flash")
                    print("\n-------Response--------")
                    print(response_text)

                    ''' Not Math Equation Detected '''
                    if "MATH EQUATION DETECTED" not in response_text and "CODE DETECTED" not in response_text:
                        youtube_OR_media = "youtube"
                        ''' open youtube url using GEMINI 2 words description '''
                        match_words = re.search(r"^(.*)", response_text)
                        words = match_words.group(0) if match_words else None
                        print(f"\n{words}")
                        videos = []
                        search_response = search_yt(words)
                        for i, search_result in enumerate(search_response.search_results):
                            if i == 0:
                                print(f"Playing YouTube video: {search_result.video_id}\nURL: {search_result.url}")
                                open_url(search_result.url, youtube_OR_media)
                            videos.append(search_result.url)
                        ''' open wikipedia url in GEMINI response '''
                        match_url = re.search(r"(https?://[^\s\]]+)", response_text)
                        url = match_url.group(0) if match_url else None
                        print(f"\n{url}")
                        webbrowser.get('firefox').open_new_tab(url)
                    else:
                        youtube_OR_media = "media"
                        ''' extract math equation steps and solution '''
                        match_url = re.search(r"(https?://[^\s\]]+)", response_text)
                        url = match_url.group(0) if match_url else None
                        webbrowser.get('firefox').open_new_tab(url)
                        print(f"\nURL_wikipedia: {url}")
                        steps = response_text.split("\n")[2:]
                        result = steps[-1]
                        print(steps)
                        ''' format math equation '''
                        url = format_math(steps)
                        open_url(url, youtube_OR_media)

                    ''' reset stability counter and cooldown counter '''
                    pointing_detected_frames = 0
                    cooldown_counter = cooldown_frames
                    is_processing = False
                    cv2.waitKey(2000)

        ''' if no hands detected, reset stability counter '''
        if cooldown_counter > 0:
            cooldown_counter -= 1

        ''' break the loop if 'q' is pressed '''
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    except KeyboardInterrupt:
        break

''' release resources '''
cap.release()
cv2.destroyAllWindows()
print("\nfree resources")