#!/usr/bin/env python3

import cv2 
import mediapipe as mp
import rospy
from alfred_clever_lamp.msg import PointingObject

''' VARIABLES '''
IMAGE_PATH = "/home/gringo/catkin_ws/src/AIfred_clever_lamp/Videos_and_pictures/pointing_object.jpg"
POINTING_STABLE_THRESHOLD = 30  # -> Number of frames to consider as stable pointing gesture
SLEEP_TIME_MS = 5000           # -> time to leave for other nodes to get image and process it before new image
CAMERA_WIDTH = 600
CAMERA_HEIGHT = 500

''' SET UP HANDS MODULE '''
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False,max_num_hands=2,min_detection_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

''' HELPER FUNCTIONS '''
def detect_hands_landmarks(image, hands, draw=True):
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
def recognize_gestures(image, fingers_statuses, count):
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
    return output_image, hands_gestures

def main():
    ''' ROS SETUP '''
    rospy.init_node('pub_pointing_image')
    pub = rospy.Publisher('/point_image', PointingObject, queue_size=1) 
    point_object = PointingObject()

    ''' WEBCAM SET UP '''
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    ''' VARIABLES '''
    pointing_detected_frames = 0    # -> Counts consecutive frames of pointing detection
    image_id = 0

    ''' MAIN LOOP '''
    try:
        while cap.isOpened() and not rospy.is_shutdown():
            ret, frame = cap.read()
            frame = cv2.flip(frame, -1)
            if not ret:
                break

            output_image, results = detect_hands_landmarks(frame, hands, draw=True)
            cv2.imshow('Webcam with Hand Landmarks', output_image)
            ''' count fingers and detect gestures '''
            if results.multi_hand_landmarks:
                output_image, fingers_statuses, count = countFingers(frame, results)
                output_image, hands_gestures = recognize_gestures(output_image, fingers_statuses, count)
                if "POINTING" in hands_gestures.values():
                    pointing_detected_frames += 1
                    if pointing_detected_frames%10 == 0:
                        rospy.loginfo(f"Pointing gesture detected for {pointing_detected_frames} frames.")
                else:
                    pointing_detected_frames = 0

                ''' if pointing gesture is stable, proceed with publishing '''
                if pointing_detected_frames >= POINTING_STABLE_THRESHOLD:
                    rospy.loginfo(f"Pointing stable. publish ID: {image_id} and path")
                    ''' save image for processing '''
                    cv2.imwrite(IMAGE_PATH, frame)
                    point_object.ID = image_id
                    point_object.path = IMAGE_PATH
                    pub.publish(point_object)
                    
                    pointing_detected_frames = 0
                    image_id += 1
                    cv2.waitKey(SLEEP_TIME_MS) # wait for other programs to open the imgae, process it with gemini, open links, and get new poining if needed only after this 5 sec

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        rospy.loginfo("Interrupted by user")
    finally:
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        rospy.loginfo("Resources released")

if __name__ == '__main__':
    main()