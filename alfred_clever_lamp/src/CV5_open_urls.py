#!/usr/bin/env python

import rospy
import math
import subprocess
import time
from tf.transformations import euler_from_quaternion
from geometry_msgs.msg import PoseStamped
from alfred_clever_lamp.msg import UrlToOpen


# Global state
initial_yaw = None
last_yaw = None
accumulated_rotation = 0
ROTATION_THRESHOLD = 180
playlist_index = 0
videos = []


def normalize_angle(angle):
    """Normalize angle to be between -pi and pi"""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def circular_list_index(current_index, direction, length):
    """Get next/previous index in circular list"""
    if length == 0:
        return 0
    return (current_index + direction) % length


def run_xdotool(args, delay=0.05):
    """Execute xdotool command with error handling"""
    try:
        subprocess.run(['xdotool'] + args, check=True, timeout=2)
        time.sleep(delay)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        rospy.logwarn(f"xdotool command failed: {e}")
        return False


def open_url(url):
    """Open URL in Chrome and enter fullscreen"""
    rospy.loginfo(f"Opening URL: {url}")
    
    # Set US keyboard layout
    subprocess.run(['setxkbmap', 'us'], check=False)
    time.sleep(0.1)

    # open existing chrome tab
    run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
                 'windowactivate', '--sync'], delay=0.2)
    
    # Exit YouTube fullscreen if active (press 'f')
    run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
                 'windowactivate', '--sync', 'key', 'f'], delay=0.2)
    
    # Exit browser fullscreen (F11)
    #run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
    #             'windowactivate', '--sync', 'key', 'F11'], delay=0.2)
    
    time.sleep(1.0)
    # Focus address bar (Ctrl+L)
    run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
                 'windowactivate', '--sync', 'key', 'ctrl+l'], delay=0.1)
    
    # Clear address bar
    #run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
    #             'windowactivate', '--sync', 'key', 'ctrl+a'], delay=0.05)
    
    # Type URL
    run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
                 'windowactivate', '--sync', 'type', '--clearmodifiers', url], delay=0.1)
    
    # Press Enter
    run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
                 'key', 'Return'], delay=0.5)
    
    # Enter browser fullscreen (F11)
    #run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
    #             'windowactivate', '--sync', 'key', 'F11'], delay=1.5)
    
    # Enter YouTube fullscreen (press 'f')
    # Wait longer for page to load
    #time.sleep(1.5)
    run_xdotool(['search', '--onlyvisible', '--class', 'chrome', 
                 'windowactivate', '--sync', 'key', 'f'], delay=0.2)
    
    # open existing firefox tab
    run_xdotool(['search', '--onlyvisible', '--class', 'firefox', 
                 'windowactivate', '--sync'], delay=0.2)
    
    rospy.loginfo(f"Successfully opened and fullscreened: {url}")


def urls_callback(msg):
    """Handle new playlist URLs"""
    global videos, playlist_index
    
    videos = msg.url_list
    playlist_index = msg.i
    
    if videos and 0 <= playlist_index < len(videos):
        open_url(videos[playlist_index])
        rospy.loginfo(f"Received {len(videos)} URLs, playing index {playlist_index}")
    else:
        rospy.logwarn(f"Invalid playlist: {len(videos)} videos, index {playlist_index}")


def pose_callback(msg):
    """Handle pose updates for gesture control"""
    global initial_yaw, last_yaw, accumulated_rotation, playlist_index, videos
    
    # Extract yaw from quaternion
    _, _, current_yaw = euler_from_quaternion([
        msg.pose.orientation.x,
        msg.pose.orientation.y,
        msg.pose.orientation.z,
        msg.pose.orientation.w
    ])
    
    # Initialize yaw on first callback
    if initial_yaw is None or last_yaw is None:
        initial_yaw = current_yaw
        last_yaw = current_yaw
        rospy.loginfo(f"Initial yaw set to {math.degrees(current_yaw):.1f}°")
        return
    
    # Calculate the actual rotation since last callback
    yaw_diff = normalize_angle(current_yaw - last_yaw)
    accumulated_rotation += math.degrees(yaw_diff)
    
    # Update last_yaw for next iteration
    last_yaw = current_yaw
    
    # Check if we've rotated enough to skip videos
    if len(videos) < 2:
        return
    
    if accumulated_rotation > ROTATION_THRESHOLD:
        # Clockwise rotation - previous video
        playlist_index = circular_list_index(playlist_index, -1, len(videos))
        rospy.loginfo(f"Previous video (rotation: {accumulated_rotation:.1f}°): {videos[playlist_index]}")
        accumulated_rotation = 0
        open_url(videos[playlist_index])
        
    elif accumulated_rotation < -ROTATION_THRESHOLD:
        # Counter-clockwise rotation - next video
        playlist_index = circular_list_index(playlist_index, 1, len(videos))
        rospy.loginfo(f"Next video (rotation: {accumulated_rotation:.1f}°): {videos[playlist_index]}")
        accumulated_rotation = 0
        open_url(videos[playlist_index])


if __name__ == '__main__':
    try:
        rospy.init_node('chromcast_controller')
        rospy.loginfo("Chromcast controller started")
        
        # Subscribe to pose and URL topics
        rospy.Subscriber("/natnet_ros/umh_5/pose", PoseStamped, callback=pose_callback, queue_size=1)
        rospy.Subscriber('/urls_to_open', UrlToOpen, callback=urls_callback, queue_size=1)
        
        rospy.spin()
        
    except rospy.ROSInterruptException:
        rospy.loginfo("Chromcast controller shutting down")