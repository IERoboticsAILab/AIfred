#! /usr/bin/env python

import rospy
from alfred_clever_lamp.msg import PointingObject, UrlToOpen

def callback(msg):
    image_id = msg.ID
    image_path = msg.path
    rospy.loginfo(f"Received image with ID: {image_id} and path: {image_path}")

    url_msg.ID = image_id
    url_msg.prev_mode = "YOUTUBE"
    url_msg.current_mode = "YOUTUBE"
    url_msg.url_list = ["https://1", "https://2", "https://3"]
    url_msg.i = 0

    pub.publish(url_msg)
    rospy.loginfo(f"Published URLs for image ID: {image_id}")

  

if __name__ == '__main__':
    rospy.init_node('process_image_gemini')
    sub = rospy.Subscriber('/point_image', PointingObject, callback)
    pub = rospy.Publisher('/urls_to_open', UrlToOpen, queue_size=1)
    url_msg = UrlToOpen()

    rospy.spin()