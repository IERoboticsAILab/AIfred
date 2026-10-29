
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import numpy as np
import sys

# This script makes the end-effector perform pick, pour, and place tasks
# Note that this script may not work for every arm as it was designed for the wx250
# Make sure to adjust commanded joint positions and poses as necessary
#
# To get started, open a terminal and type 'roslaunch interbotix_xsarm_control xsarm_control.launch robot_model:=wx250'
# Then change to this directory and type 'python bartender.py  # python3 bartender.py if using ROS Noetic'

def main():
    bot = InterbotixManipulatorXS("aifred", "arm", gripper_name=None)

    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.3, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)

    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.1, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)

    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.3, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)

    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=1, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)

    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=1, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)

    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=1)
    bot.arm.set_ee_pose_components(x=0.2, y=0.0, z=0.4, roll=0, pitch=0, yaw=0)

    bot.arm.set_single_joint_position("wrist_rotate", np.pi/2.0, moving_time=0.9)
    bot.arm.set_single_joint_position("wrist_rotate", 0,         moving_time=0.9)
    bot.arm.set_single_joint_position("wrist_rotate", np.pi/2.0                 )
    bot.arm.set_single_joint_position("wrist_rotate", 0                         )

    bot.arm.set_single_joint_position("wrist_angle", np.pi/2.0, moving_time=0.9)
    bot.arm.set_single_joint_position("wrist_angle", 0,         moving_time=0.9)
    bot.arm.set_single_joint_position("wrist_angle", np.pi/2.0                 )
    bot.arm.set_single_joint_position("wrist_angle", 0                         )



    bot.arm.go_to_sleep_pose()

if __name__=='__main__':
    main()
