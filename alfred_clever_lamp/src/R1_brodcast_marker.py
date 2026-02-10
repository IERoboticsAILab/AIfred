#!/usr/bin/env python3
import rospy
import tf_conversions
import tf2_ros
import geometry_msgs.msg
from geometry_msgs.msg import PoseStamped

global pos_base 

def pose_callback(msg):
    global pos_base
    br = tf2_ros.TransformBroadcaster()
    t = geometry_msgs.msg.TransformStamped()

    t.header.stamp = rospy.Time.now()
    t.header.frame_id = "wx250s/base_link"
    t.child_frame_id = "umh_5_new"
    t.transform.translation.x = (msg.pose.position.y-pos_base[1]) 
    t.transform.translation.y = -(msg.pose.position.x-pos_base[0])
    t.transform.translation.z = (msg.pose.position.z-pos_base[2]) 
    t.transform.rotation.x = 0.0
    t.transform.rotation.y = 0.0
    t.transform.rotation.z = 0.0
    t.transform.rotation.w = 1.0

    br.sendTransform(t)

def base_callback(msg):
    global pos_base
    pos_base = (msg.pose.position.x, msg.pose.position.y, msg.pose.position.z)

if __name__ == '__main__':
    rospy.init_node('tf2_broadcaster')
    rospy.Subscriber("/natnet_ros/umh_5/pose", PoseStamped, callback=pose_callback, queue_size=1)
    rospy.Subscriber("/natnet_ros/real_base_wx250s/pose", PoseStamped, callback=base_callback, queue_size=1)
    rospy.spin()