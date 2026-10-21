#!/usr/bin/env python3
from interbotix_xs_modules.arm import InterbotixManipulatorXS
import argparse
import os
import threading
import time
import yaml

# Record a motion by moving AIfred's head by hand (arm torque off), e.g. to explore the desk
# with the webcam or to act out an emotion. Saved to aifred_robot/motions/<name>.yaml and
# replayed with play_motion.py.
#
# Raspberry Pi: roslaunch aifred_robot robot.launch
# PC:           rosrun aifred_robot record_motion.py curious           # keyframes
#               rosrun aifred_robot record_motion.py happy --live      # continuous
#
# Keyframes: move the head, press Enter to save the pose. Type a number before Enter to set
# the seconds to reach that pose (default --duration); Enter without moving = hold. q to finish.
# Live: everything is recorded at --rate Hz between two Enter presses, timing included.

MOTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motions")
APPROACH_TIME = 2.0  # seconds to reach the first pose when the motion is played

def read_joints(bot):
    js = bot.dxl.robot_get_joint_states()
    return [round(js.position[bot.dxl.js_index_map[name]], 3) for name in bot.arm.group_info.joint_names]

def record_keyframes(bot, duration):
    frames = []
    while True:
        cmd = input("[%d] Enter = save pose, <seconds> Enter = save with time, q = finish: " % len(frames)).strip()
        if cmd == "q":
            return frames
        try:
            t = float(cmd) if cmd else duration
        except ValueError:
            print("Not a number: %s" % cmd)
            continue
        frames.append({"time": APPROACH_TIME if not frames else t, "pos": read_joints(bot)})

def record_live(bot, rate):
    input("Move the head to the start pose, then press Enter to start recording...")
    stop = threading.Event()
    threading.Thread(target=lambda: (input("Recording... press Enter to stop.\n"), stop.set()), daemon=True).start()
    frames = [{"time": APPROACH_TIME, "pos": read_joints(bot)}]
    dt = 1.0 / rate
    while not stop.is_set():
        time.sleep(dt)
        frames.append({"time": round(dt, 3), "pos": read_joints(bot)})
    return frames

def main():
    parser = argparse.ArgumentParser(description="Record an AIfred motion by moving the head by hand.")
    parser.add_argument("name", help="motion name (saved to motions/<name>.yaml)")
    parser.add_argument("--live", action="store_true", help="record continuously instead of keyframes")
    parser.add_argument("--rate", type=float, default=10.0, help="live sampling rate [Hz]")
    parser.add_argument("--duration", type=float, default=1.0, help="default seconds between keyframes")
    args = parser.parse_args()

    path = os.path.join(MOTIONS_DIR, args.name + ".yaml")
    if os.path.exists(path) and input("%s exists, overwrite? [y/N] " % path).strip().lower() != "y":
        return

    bot = InterbotixManipulatorXS("wx250s", "arm", gripper_name=None)

    input("HOLD THE ARM: torque will be turned off. Press Enter when ready...")
    bot.dxl.robot_torque_enable("group", "arm", False)
    try:
        frames = record_live(bot, args.rate) if args.live else record_keyframes(bot, args.duration)
    finally:
        # motors hold the current pose; sync the commands so the next move starts from here
        bot.dxl.robot_torque_enable("group", "arm", True)
        bot.arm.capture_joint_positions()

    if not frames:
        print("Nothing recorded.")
        return
    os.makedirs(MOTIONS_DIR, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump({"joints": list(bot.arm.group_info.joint_names), "frames": frames}, f,
                       default_flow_style=None, sort_keys=False)
    print("Saved %d frames (%.1f s) to %s" % (len(frames), sum(fr["time"] for fr in frames), path))

if __name__=='__main__':
    main()
