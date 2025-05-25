#!/usr/bin/env python3

import cv2
import mediapipe as mp
import cv2
import os
import googleapiclient.discovery
from dotenv import load_dotenv
import google.generativeai as genai
import subprocess
import time
import pyautogui
import pyperclip
import tempfile

pyautogui.FAILSAFE = False
load_dotenv()
YOUTUBE_API = os.environ.get("YOUTUBE_DATA_APY_KEY")
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API)
GEMINI_API = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API)
model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")


mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5
)
hands_videos = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5
)

mp_drawing = mp.solutions.drawing_utils

def detectHandsLandmarks(image, hands, draw=True):
    '''
    This function performs hands landmarks detection on an image.
    Args:
        image:   The input image with prominent hand(s) whose landmarks needs to be detected.
        hands:   The Hands function required to perform the hands landmarks detection.
        draw:    A boolean value that is if set to true the function draws hands landmarks on the output image.
        display: A boolean value that is if set to true the function displays the original input image, and the output
                 image with hands landmarks drawn if it was specified and returns nothing.
    Returns:
        output_image: A copy of input image with the detected hands landmarks drawn if it was specified.
        results:      The output of the hands landmarks detection on the input image.
    '''

    # Create a copy of the input image to draw landmarks on.
    output_image = image.copy()

    # Convert the image from BGR into RGB format.
    imgRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Perform the Hands Landmarks Detection.
    results = hands.process(imgRGB)

    # Check if landmarks are found and are specified to be drawn.
    if results.multi_hand_landmarks and draw:

        # Iterate over the found hands.
        for hand_landmarks in results.multi_hand_landmarks:

            # Draw the hand landmarks on the copy of the input image.
            mp_drawing.draw_landmarks(image = output_image, landmark_list = hand_landmarks,
                                      connections = mp_hands.HAND_CONNECTIONS,
                                      landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255,255,255),
                                                                                   thickness=2, circle_radius=2),
                                      connection_drawing_spec=mp_drawing.DrawingSpec(color=(0,255,0),
                                                                                     thickness=2, circle_radius=2))

    # Return the output image and results of hands landmarks detection.
    return output_image, results




def countFingers(image, results):
    '''
    to check if finger is up, we compare
    with the previus joint in the x, y plane,
    and we see with one is higher
    (for tumb we chech x coordinate, for other finger the y coordinate)
    '''
    '''
    This function will count the number of fingers up for each hand in the image.
    Args:
        image:   The image of the hands on which the fingers counting is required to be performed.
        results: The output of the hands landmarks detection performed on the image of the hands.
        draw:    A boolean value that is if set to true the function writes the total count of fingers of the hands on the
                 output image.
        display: A boolean value that is if set to true the function displays the resultant image and returns nothing.
    Returns:
        output_image:     A copy of the input image with the fingers count written, if it was specified.
        fingers_statuses: A dictionary containing the status (i.e., open or close) of each finger of both hands.
        count:            A dictionary containing the count of the fingers that are up, of both hands.
    '''

    # Get the height and width of the input image.
    height, width, _ = image.shape

    # Create a copy of the input image to write the count of fingers on.
    output_image = image.copy()

    # Initialize a dictionary to store the count of fingers of both hands.
    count = {'RIGHT': 0, 'LEFT': 0}

    # Store the indexes of the tips landmarks of each finger of a hand in a list.
    fingers_tips_ids = [mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                        mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.PINKY_TIP]

    # Initialize a dictionary to store the status (i.e., True for open and False for close) of each finger of both hands.
    fingers_statuses = {'RIGHT_THUMB': False, 'RIGHT_INDEX': False, 'RIGHT_MIDDLE': False, 'RIGHT_RING': False,
                        'RIGHT_PINKY': False, 'LEFT_THUMB': False, 'LEFT_INDEX': False, 'LEFT_MIDDLE': False,
                        'LEFT_RING': False, 'LEFT_PINKY': False}


    # Iterate over the found hands in the image.
    for hand_index, hand_info in enumerate(results.multi_handedness):

        # Retrieve the label of the found hand.
        hand_label = hand_info.classification[0].label

        # Retrieve the landmarks of the found hand.
        hand_landmarks =  results.multi_hand_landmarks[hand_index]

        # Iterate over the indexes of the tips landmarks of each finger of the hand.
        for tip_index in fingers_tips_ids:

            # Retrieve the label (i.e., index, middle, etc.) of the finger on which we are iterating upon.
            finger_name = tip_index.name.split("_")[0]

            # Check if the finger is up by comparing the y-coordinates of the tip and pip landmarks.
            if (hand_landmarks.landmark[tip_index].y < hand_landmarks.landmark[tip_index - 2].y):

                # Update the status of the finger in the dictionary to true.
                fingers_statuses[hand_label.upper()+"_"+finger_name] = True

                # Increment the count of the fingers up of the hand by 1.
                count[hand_label.upper()] += 1

        # Retrieve the y-coordinates of the tip and mcp landmarks of the thumb of the hand.
        thumb_tip_x = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x
        thumb_mcp_x = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP - 2].x

        # Check if the thumb is up by comparing the hand label and the x-coordinates of the retrieved landmarks.
        if (hand_label=='Right' and (thumb_tip_x < thumb_mcp_x)) or (hand_label=='Left' and (thumb_tip_x > thumb_mcp_x)):

            # Update the status of the thumb in the dictionary to true.
            fingers_statuses[hand_label.upper()+"_THUMB"] = True

            # Increment the count of the fingers up of the hand by 1.
            count[hand_label.upper()] += 1

    # Return the output image, the status of each finger and the count of the fingers up of both hands.
    return output_image, fingers_statuses, count


''' functions for YouTube search '''
class Search_Response:
    def __init__(self, search_response) -> None:
        self.prev_page_token = search_response.get('prevPageToken')
        self.next_page_token = search_response.get('nextPageToken')

        # items element contains a list of videos
        items = search_response.get('items')
        self.search_results = [Search_Result(item) for item in items]

class Search_Result:
    def __init__(self, search_result) -> None:
        self.video_id = search_result['id']['videoId']
        self.title = search_result['snippet']['title']
        self.description = search_result['snippet']['description']
        self.url = f"https://www.youtube.com/watch?v={self.video_id}"
        self.thumbnails = search_result['snippet']['thumbnails']['default']['url']

def search_yt(query, max_results=5, page_token=None):
    request = youtube.search().list(
        part="snippet",
        maxResults=max_results,
        pageToken=page_token,
        q=query,
        videoCaption='closedCaption',
        type='video',
    )
    response = request.execute()
    return Search_Response(response)

def circular_list(current_index, direction, length):
    if direction == 1:
        if current_index == length-1:
            return 0
        else:
            return current_index + 1
    else:
        if current_index == 0:
            return length-1
        else:
            return current_index - 1


def open_url(url, youtube_OR_media):
    # Try to focus or open Chrome
    subprocess.run(['xdotool', 'search', '--onlyvisible', '--class', 'chrome', 'windowactivate'], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    # Additional cleanup for video content
    #pyautogui.hotkey('space')  # pause video
    #time.sleep(0.3)
    #pyautogui.press('esc')  # make screen small
    #time.sleep(0.3)
    # Navigate to URL
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.3)
    pyperclip.copy(url)
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.press('return')
    time.sleep(1)

    if youtube_OR_media == "media":
        # Define the mouse click sequence from your JSON
        mouse_actions = [
            #{"type": "click", "x": 1898, "y": 89, "delay": 0.1},
            #{"type": "click", "x": 1645, "y": 693, "delay": 0.2},
            #{"type": "click", "x": 1458, "y": 724, "delay": 0.2},
            #{"type": "click", "x": 1794, "y": 225, "delay": 0.6},
            #{"type": "click", "x": 1617, "y": 193, "delay": 0.9}
            #{  "type": "click",  "x": 1900,  "y": 88,  "delay": 0.2},
            #{  "type": "click",  "x": 1684,  "y": 736,  "delay": 0.2},
            #{  "type": "click",  "x": 1433,  "y": 779,  "delay": 0.2},
            #{  "type": "click",  "x": 1685,  "y": 230,  "delay": 0.5},
            #{  "type": "click",  "x": 1562,  "y": 188,  "delay": 1.0}
            {  "type": "click",  "x": 1896,  "y": 86,  "delay": 0.2},
            {  "type": "click",  "x": 1679,  "y": 739,  "delay": 0.2},
            {  "type": "click",  "x": 1413,  "y": 777,  "delay": 0.2},
            {  "type": "click",  "x": 1622,  "y": 232,  "delay": 0.5},
            {  "type": "click",  "x": 1478,  "y": 195,  "delay": 1.0}
        ]
        
        # Execute the recorded mouse clicks
        print("Executing mouse clicks to stop and restart casting...")
        for i, action in enumerate(mouse_actions):
            # Wait the recorded delay (skip for first action)
            if i > 0 and "delay" in action:
                time.sleep(action["delay"])
            
            # Perform the click
            if action["type"] == "click":
                pyautogui.click(action["x"], action["y"])
                print(f"Clicked at position ({action['x']}, {action['y']})")
    
    # Step 2: Focus Firefox
    subprocess.run(['xdotool', 'search', '--onlyvisible', '--class', 'firefox', 'windowactivate'], 
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    # Step 3: Fullscreen Firefox
    pyautogui.press('f11')

    return True


def format_math(steps):
    html_content = """
    <html>
    <head>
        <title>Math Solution</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background-color: #f9f9f9;
                color: #333;
                padding: 40px;
            }
            h1 {
                text-align: center;
                color: #2c3e50;
                font-size: 3em;
            }
            .step {
                font-size: 3.6em; /* tripled from 1.2em */
                margin: 30px auto;
                width: fit-content;
                background: white;
                padding: 20px 30px;
                border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                text-align: center;
            }
            .solution {
                color: #e74c3c;
                font-weight: bold;
                font-size: 4.2em; /* tripled from 1.4em */
            }
        </style>
    </head>
    <body>
        <h1>Math Solution Steps</h1>
    """

    for step in steps:
        if 'solution' in step.lower():
            html_content += f'<div class="step solution">{step}</div>'
        else:
            html_content += f'<div class="step">{step}</div>'

    html_content += """
    </body>
    </html>
    """

    # Save HTML to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
        f.write(html_content)
        local_path = f.name

    return 'file://' + local_path