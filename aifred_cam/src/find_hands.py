#!/usr/bin/env python3


'''
script that finds heands using mediapipe and publish their TF
'''

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import mediapipe as mp


class ShowingImage(object):

    def __init__(self):
        rospy.init_node('pub_mediapipe_hand_landmarks', anonymous=True)
        self.image_sub = rospy.Subscriber(
            "/aifred_cam/image_raw",
            Image,
            self.camera_callback
        )
        self.bridge_object = CvBridge()

        self.mp_hands = mp.solutions.hands # specify to use hands detection (not pose, face, etc.)
        self.hand = self.mp_hands.Hands() # create a hand object
        self.mp_drawing = mp.solutions.drawing_utils # drawing utilities

    def camera_callback(self, data):
        try:
            # We select bgr8 because it is the OpenCV default encoding
            frame = self.bridge_object.imgmsg_to_cv2(
                data,
                desired_encoding="bgr8"
            )
        except CvBridgeError as e:
            print(e)
            return

        result = self.hand.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if result.multi_hand_landmarks: # if hand landmarks are detected
            for hand_landmarks in result.multi_hand_landmarks:
                print(hand_landmarks)
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

        cv2.imshow("image", frame)
        cv2.waitKey(1)


if __name__ == '__main__':
    try:
        ShowingImage()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
    finally:
        cv2.destroyAllWindows()