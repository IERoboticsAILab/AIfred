#!/usr/bin/env python3

import rospy
import math
import tf2_ros
import geometry_msgs.msg
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import time
import random


def start_robot():
    global bot
    print("start robot")
    bot = InterbotixManipulatorXS("wx250s", "arm", "gripper", init_node=False)
    #bot.arm.set_ee_pose_components(x=0.2, y=0, z=0.3, pitch=1.5)
    bot.arm.set_ee_pose_components(x=0, y=0.15, z=0.25, pitch=0.75)
    bot.arm.set_ee_pose_components(x=-0.15, y=0.15, z=0.25, pitch=-0.3)
    bot.arm.set_ee_pose_components(x=-0.15, y=0.15, z=0.25, pitch=0.3)
    bot.arm.set_ee_pose_components(x=-0.15, y=0.15, z=0.25, pitch=0)
    print("done robot")

def out_boundary(x, y):
    # Compute the closest point on the circle boundary
    safe_x = 0.30 * x / math.sqrt(x**2 + y**2)
    safe_y = 0.30 * y / math.sqrt(x**2 + y**2)

    rospy.loginfo("Out of bounds! Moving to safe position.")
    # Perform a 'no' shaking motion
    bot.arm.set_ee_pose_components(x=safe_x, y=safe_y, z=0.3, pitch=1.5, yaw=0.2, accel_time=0.01)
    time.sleep(0.1)
    bot.arm.set_ee_pose_components(x=safe_x, y=safe_y, z=0.3, pitch=1.5, yaw=-0.2, accel_time=0.01)
    time.sleep(0.1)
    
    # Move to the safe point
    bot.arm.set_ee_pose_components(x=safe_x, y=safe_y, z=0.3, pitch=1.5, yaw=0)

if __name__ == '__main__':
    rospy.init_node('clever_lamp')

    tfBuffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tfBuffer)

    rate = rospy.Rate(10.0)
    start_robot()
    
    while not rospy.is_shutdown():
        try:
            trans = tfBuffer.lookup_transform("umh_5_new", "wx250s/base_link", rospy.Time())
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
            rate.sleep()
            continue
        rospy.loginfo(f"trans: {trans}")
        #rospy.loginfo(f"root: {rot}")

        x = -trans.transform.translation.x
        y = -trans.transform.translation.y

        # Check if the point is inside the circle
        if math.sqrt(x**2 + y**2) > 0.30:
            print("out")
            out_boundary(x, y)
        else:
            bot.arm.set_ee_pose_components(x=x, y=y, z=0.3, pitch=1.5, yaw=0)

        rate.sleep()




''' NEED TO ADD CONSTRAINS FOR CRAZY MOOVMENTS OF THE ROBOT '''
'''
import rospy
import math
import tf2_ros
import geometry_msgs.msg
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import time

def start_robot():
    global bot
    print("start robot")
    bot = InterbotixManipulatorXS("wx250s", "arm", "gripper", init_node=False)
    bot.arm.set_ee_pose_components(x=0.2, y=0, z=0.3, pitch=1.5)
    print("done robot")

def already_in_position(new_y, new_x, old_y, old_x):
    if old_y is None or old_x is None:
        return False
    return abs(new_y - old_y) < 0.01 and abs(new_x - old_x) < 0.1

if __name__ == '__main__':
    rospy.init_node('clever_lamp')

    tfBuffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tfBuffer)
    hight = None
    old_tran_y, old_tran_x = None, None
    horizontal = True
    treshold = 0.15

    rate = rospy.Rate(10.0)
    start_robot()
    while not rospy.is_shutdown():
        try:
            trans = tfBuffer.lookup_transform("umh_5_new", "wx250s/base_link", rospy.Time())
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
            rate.sleep()
            continue

        rospy.loginfo(f"trans: {trans}")

        if hight is not None and hight - trans.transform.translation.z >= treshold:
            horizontal = not horizontal
        
        if horizontal:
            bot.arm.set_ee_pose_components(x=-trans.transform.translation.x, y=-trans.transform.translation.y, z=0.3, pitch=1.5, yaw=0)
            hight = trans.transform.translation.z
        else:
            if already_in_position(trans.transform.translation.y, trans.transform.translation.x, old_tran_y, old_tran_x):
                bot.arm.set_ee_pose_components(x=0.3, y=-trans.transform.translation.y, z=abs(trans.transform.translation.x)+0.1, pitch=0, yaw=0, accel_time=0.01)
            else:
                bot.arm.set_ee_pose_components(x=0.3, y=-trans.transform.translation.y, z=abs(trans.transform.translation.x)+0.1, accel_time=0.01)
            
            old_tran_y, old_tran_x = trans.transform.translation.y, trans.transform.translation.x
            hight = trans.transform.translation.z

        rate.sleep()
'''