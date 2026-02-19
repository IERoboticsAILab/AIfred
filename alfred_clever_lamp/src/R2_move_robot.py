#!/usr/bin/env python3

import rospy
import math
import tf2_ros
from interbotix_xs_modules.arm import InterbotixManipulatorXS # type: ignore
import time

def start_robot():
    global bot
    rospy.loginfo("\nstart robot")
    bot = InterbotixManipulatorXS("wx250s", "arm", "gripper", init_node=False) # /home/gringo/interbotix_ws/src/interbotix_ros_toolboxes/interbotix_xs_toolbox/interbotix_xs_modules/src/interbotix_xs_modules/arm.py
    bot.arm.set_ee_pose_components(x=0, y=0.15, z=0.25, pitch=0.75, moving_time=2.5)
    bot.arm.set_ee_pose_components(x=-0.15, y=0.15, z=0.25, pitch=-0.3, moving_time=1.3)
    bot.arm.set_ee_pose_components(x=-0.15, y=0.15, z=0.25, pitch=0.3, moving_time=0.9)
    rospy.loginfo("\ndone robot")


def out_boundary(x, y):
    # Calculate the angle of the point
    angle = math.atan2(y, x)
    # Calculate the point on the boundary of the circle
    boundary_x = 0.30 * math.cos(angle)
    boundary_y = 0.30 * math.sin(angle)
    #rospy.loginfo(f"\nPoint is out of boundary. Moving to boundary point: x={boundary_x:.2f}, y={boundary_y:.2f}")
    # Perform a 'no' shaking motion
    bot.arm.set_ee_pose_components(x=boundary_x, y=boundary_y, z=0.3, pitch=1.5, yaw=0.2, moving_time=0.5)
    bot.arm.set_ee_pose_components(x=boundary_x, y=boundary_y, z=0.3, pitch=1.5, yaw=-0.2, moving_time=0.5)
    # Move to the safe point
    bot.arm.set_ee_pose_components(x=boundary_x, y=boundary_y, z=0.3, pitch=1.5, yaw=0, moving_time=0.5)


if __name__ == '__main__':
    x_offset = 0.25
    y_offset = 0.1
    rospy.init_node('move_robot')

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
        #rospy.loginfo(f"trans: {trans}")
        #rospy.loginfo(f"root: {rot}")

        x = -trans.transform.translation.x
        y = -trans.transform.translation.y
        #rospy.loginfo(f"\nRaw coordinates: x={x:.2f}, y={y:.2f}")
        x -= x_offset
        y -= y_offset
        #rospy.loginfo(f"Offset coordinates: x={x:.2f}, y={y:.2f}")

        # Check if the point is inside the circle
        if math.sqrt(x**2 + y**2) > 0.30:
            out_boundary(x, y)
        else:
            start_time = time.time()
            bot.arm.set_ee_pose_components(x=x, y=y, z=0.3, pitch=1.5, yaw=0, moving_time=1.5)
            end_time = time.time() - start_time
            #rospy.loginfo(f"\nTime taken to move: {end_time:.2f} seconds")
        rate.sleep()