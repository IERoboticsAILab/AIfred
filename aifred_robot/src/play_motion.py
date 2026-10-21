#!/usr/bin/env python3
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import argparse
import os
import rospy
import yaml

# Play motions recorded with record_motion.py (aifred_robot/motions/<name>.yaml), one after
# the other, e.g. explore the desk, then react to what the webcam found.
#
# Raspberry Pi: roslaunch aifred_robot robot.launch
# PC:           rosrun aifred_robot play_motion.py --list
#               rosrun aifred_robot play_motion.py look_around curious --speed 1.5
#               rosrun aifred_robot play_motion.py look_around --mirror --loop

MOTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motions")
STREAM_TIME = 0.3  # frames shorter than this (live recordings) are streamed instead of stopping at each one
MIRRORED = ["waist", "forearm_roll", "wrist_rotate"]  # joints negated to swap left and right

def load(name, mirror):
    with open(os.path.join(MOTIONS_DIR, name + ".yaml")) as f:
        motion = yaml.safe_load(f)
    sign = [-1 if mirror and j in MIRRORED else 1 for j in motion["joints"]]
    return [(fr["time"], [s * p for s, p in zip(sign, fr["pos"])]) for fr in motion["frames"]]

def play(bot, frames, speed):
    for i, (t, pos) in enumerate(frames):
        if i > 0:
            t /= speed  # the first frame is the approach from wherever the arm is, keep it slow
        if t < STREAM_TIME:
            # aim at a profile twice as long as the frame so the motors never stop between frames
            ok = bot.arm.set_joint_positions(pos, moving_time=2 * t, accel_time=t, blocking=False)
            rospy.sleep(t)
        else:
            ok = bot.arm.set_joint_positions(pos, moving_time=t, accel_time=min(0.3, t / 2))
        if not ok:
            print("Skipped frame %d (outside joint or velocity limits)" % i)

def main():
    parser = argparse.ArgumentParser(description="Play recorded AIfred motions.")
    parser.add_argument("names", nargs="*", help="motions to play in order")
    parser.add_argument("--list", action="store_true", help="list recorded motions")
    parser.add_argument("--speed", type=float, default=1.0, help="playback speed factor")
    parser.add_argument("--mirror", action="store_true", help="swap left and right")
    parser.add_argument("--loop", action="store_true", help="repeat until Ctrl+C")
    parser.add_argument("--sleep", action="store_true", help="go to the sleep pose at the end")
    args = parser.parse_args()

    if args.list or not args.names:
        names = sorted(f[:-5] for f in os.listdir(MOTIONS_DIR) if f.endswith(".yaml")) if os.path.isdir(MOTIONS_DIR) else []
        print("\n".join(names) or "No motions recorded yet (rosrun aifred_robot record_motion.py <name>)")
        return

    motions = [(name, load(name, args.mirror)) for name in args.names]
    bot = InterbotixManipulatorXS("wx250s", "arm", gripper_name=None)

    while not rospy.is_shutdown():
        for name, frames in motions:
            print("Playing %s" % name)
            play(bot, frames, args.speed)
        if not args.loop:
            break

    if args.sleep:
        bot.arm.go_to_sleep_pose()

if __name__=='__main__':
    main()
