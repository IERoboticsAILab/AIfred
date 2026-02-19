#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped
from alfred_clever_lamp.msg import Mode
import time

# Mode [0 -> Arm Controll, 1 -> Homework, 2 -> Generate Image, 3 -> Draw Mode]
current_mode = -1

def pose_callback(msg):
    global current_mode

    height = msg.pose.position.z
    if abs(height) > 0.9:
        current_mode += 1
        if current_mode > 3:
            current_mode = 1
        rospy.loginfo(f"Mode changed to: {current_mode}")
        mode_msg.mode = current_mode
        mode_pub.publish(mode_msg)
        time.sleep(5)

if __name__ == '__main__':
    rospy.init_node('mode_publisher')

    mode_pub = rospy.Publisher('/mode', Mode, queue_size=1)
    mode_msg = Mode()
    mode_msg.mode = current_mode # pub 0 -> Arm Controll
    rospy.loginfo(f"Initial mode: {current_mode}")
    mode_pub.publish(mode_msg)

    rospy.Subscriber("/natnet_ros/umh_5/pose", PoseStamped, callback=pose_callback, queue_size=1)
    rospy.spin()