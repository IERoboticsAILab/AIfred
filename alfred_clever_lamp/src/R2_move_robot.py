#!/usr/bin/env python3

import rospy
import math
import tf2_ros
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import time

def start_robot():
    global bot
    rospy.loginfo("\nstart robot")
    bot = InterbotixManipulatorXS("wx250s", "arm", "gripper", init_node=False)
    bot.arm.set_ee_pose_components(x=0, y=0.15, z=0.25, pitch=0.75, moving_time=2.5)
    bot.arm.set_ee_pose_components(x=-0.15, y=0.15, z=0.25, pitch=-0.3, moving_time=1.3)
    bot.arm.set_ee_pose_components(x=-0.15, y=0.15, z=0.25, pitch=0.3, moving_time=0.9)
    rospy.loginfo("\ndone robot")


def out_boundary(x, y):
    angle = math.atan2(y, x)
    boundary_x = 0.30 * math.cos(angle)
    boundary_y = 0.30 * math.sin(angle)
    bot.arm.set_ee_pose_components(x=boundary_x, y=boundary_y, z=0.3, pitch=1.5, yaw=0.2, moving_time=0.45)
    bot.arm.set_ee_pose_components(x=boundary_x, y=boundary_y, z=0.3, pitch=1.5, yaw=-0.2, moving_time=0.45)
    bot.arm.set_ee_pose_components(x=boundary_x, y=boundary_y, z=0.3, pitch=1.5, yaw=0.2, moving_time=0.45)
    bot.arm.set_ee_pose_components(x=boundary_x, y=boundary_y, z=0.3, pitch=1.5, yaw=-0.2, moving_time=0.45)


if __name__ == '__main__':
    x_offset = 0.22
    y_offset = 0.08

    # --- Deadzone thresholds ---
    MIN_MOVE_DIST  = 0.015   # meters — ignore jitter smaller than 1.5 cm
    MIN_BOUNDARY_DIST = 0.02  # meters — suppress repeated boundary triggers

    rospy.init_node('move_robot')

    tfBuffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tfBuffer)

    rate = rospy.Rate(10.0)
    start_robot()

    # Track last commanded position
    last_cmd_x = None
    last_cmd_y = None
    last_boundary = False   # were we in boundary-shake mode last tick?

    while not rospy.is_shutdown():
        try:
            trans = tfBuffer.lookup_transform("umh_0_new", "wx250s/base_link", rospy.Time())
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
            rate.sleep()
            continue

        x = -trans.transform.translation.x - x_offset
        y = -trans.transform.translation.y - y_offset

        in_boundary = math.sqrt(x**2 + y**2) > 0.30

        if in_boundary:
            # For boundary shakes, only re-trigger if position shifted noticeably
            angle = math.atan2(y, x)
            bx = 0.30 * math.cos(angle)
            by = 0.30 * math.sin(angle)
            out_boundary(x, y)
            last_cmd_x, last_cmd_y = bx, by

        else:
            # Skip tiny movements — deadzone filter
            if last_cmd_x is None or math.sqrt((x - last_cmd_x)**2 + (y - last_cmd_y)**2) > MIN_MOVE_DIST:
                bot.arm.set_ee_pose_components(x=x, y=y, z=0.3, pitch=1.5, yaw=0, moving_time=1.8)
                last_cmd_x, last_cmd_y = x, y

        rate.sleep()