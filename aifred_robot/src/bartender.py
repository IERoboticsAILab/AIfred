#!/usr/bin/env python3
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import interbotix_xs_modules.mr_descriptions as mrd
import modern_robotics as mr
import numpy as np
from types import SimpleNamespace

# Bartender-like demo for AIfred: the end effector is the camera (wx250s/camera_link).
#
# Raspberry Pi: roslaunch aifred_robot robot.launch
# PC:           rosrun aifred_robot bartender.py

# camera_link pose at all joints = 0 (from aifred.urdf.xacro). The lens is CAM_Y to the
# side of the wrist axis, so the yaw is chosen to keep forearm_roll/wrist_rotate at 0
# (head straight) instead of the default atan2(y, x), which makes IK twist the head.
CAM_X, CAM_Y, CAM_Z = 0.485409, 0.036834, 0.36063

# Camera positions [x, y, z] in metres (base frame) and pitch in rad (pi/2 = looking down)
POSES = [
    [0.45,  0.00, 0.25, 0.0],  # front
    [0.00,  0.45, 0.25, 0.0],  # left
    [0.00,  0.50, 0.15, 0.0],  # left, forward and down
    [0.00,  0.45, 0.25, 0.0],  # left
    [0.00, -0.45, 0.25, 0.0],  # right
    [0.00, -0.35, 0.25, 1.5],  # right, looking down
    [0.00, -0.45, 0.25, 0.0],  # right
    [0.00,  0.45, 0.25, 0.0],  # left
    [0.00,  0.50, 0.15, 0.0],  # left, forward and down
    [0.00,  0.45, 0.25, 0.0],  # left
]

def camera_yaw(x, y):
    # waist angle that puts the (side-offset) camera on (x, y)
    r = np.sqrt(max(x**2 + y**2 - CAM_Y**2, 1e-6))
    return np.arctan2(y, x) - np.arctan2(CAM_Y, r)

def main():
    bot = InterbotixManipulatorXS("wx250s", "arm", gripper_name=None)

    M = np.identity(4)
    M[:3, 3] = [CAM_X, CAM_Y, CAM_Z]
    bot.arm.robot_des = SimpleNamespace(Slist=mrd.wx250s.Slist, M=M)
    bot.arm.T_sb = mr.FKinSpace(M, mrd.wx250s.Slist, bot.arm.joint_commands)

    for x, y, z, pitch in POSES:
        _, ok = bot.arm.set_ee_pose_components(x=x, y=y, z=z, pitch=pitch, yaw=camera_yaw(x, y))
        if not ok:
            print("Unreachable camera pose: x=%.2f y=%.2f z=%.2f pitch=%.2f" % (x, y, z, pitch))

    bot.arm.go_to_home_pose()
    bot.arm.go_to_sleep_pose()

if __name__=='__main__':
    main()
