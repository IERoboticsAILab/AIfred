#!/usr/bin/env python3
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import interbotix_xs_modules.mr_descriptions as mrd
import modern_robotics as mr
import numpy as np
from types import SimpleNamespace

# Interbotix bartender demo adapted to AIfred: no gripper, the end effector is the camera.
#
# Raspberry Pi: roslaunch aifred_robot robot.launch
# PC:           rosrun aifred_robot bartender.py

def main():
    bot = InterbotixManipulatorXS("wx250s", "arm", gripper_name=None)

    # IK end effector = wx250s/camera_link (pose at all joints = 0, from aifred.urdf.xacro).
    # The camera looks along its x axis (like the old gripper), so pitch=1.5 means looking down.
    M = np.identity(4)
    M[:3, 3] = [0.485409, 0.036834, 0.36063]
    bot.arm.robot_des = SimpleNamespace(Slist=mrd.wx250s.Slist, M=M)
    bot.arm.T_sb = mr.FKinSpace(M, mrd.wx250s.Slist, bot.arm.joint_commands)

    bot.arm.set_ee_pose_components(x=0.3, z=0.2)
    bot.arm.set_single_joint_position("waist", np.pi/2.0)
    bot.arm.set_ee_cartesian_trajectory(x=0.1, z=-0.16)
    bot.arm.set_ee_cartesian_trajectory(x=-0.1, z=0.16)
    bot.arm.set_single_joint_position("waist", -np.pi/2.0)
    bot.arm.set_ee_cartesian_trajectory(pitch=1.5)
    bot.arm.set_ee_cartesian_trajectory(pitch=-1.5)
    bot.arm.set_single_joint_position("waist", np.pi/2.0)
    bot.arm.set_ee_cartesian_trajectory(x=0.1, z=-0.16)
    bot.arm.set_ee_cartesian_trajectory(x=-0.1, z=0.16)
    bot.arm.go_to_home_pose()
    bot.arm.go_to_sleep_pose()

if __name__=='__main__':
    main()
