#!/usr/bin/env bash


source /opt/ros/noetic/setup.bash
source ~/interbotix_ws/devel/setup.bash
source ~/catkin_ws/devel/setup.bash
source ~/catkin_ws/src/AIfred/.venv/bin/activate
export DISABLE_ROS1_EOL_WARNINGS=true

export ROS_MASTER_URI=http://10.205.10.254:11311
MASTER_HOST="$(echo "$ROS_MASTER_URI" | sed -E 's#^https?://([^:/]+).*#\1#')"
export ROS_IP="$(ip -4 route get "$MASTER_HOST" | grep -oP 'src \K\S+')"   # local IP that reaches the master
rostopic list

echo "ROS_MASTER_URI=$ROS_MASTER_URI  ROS_IP=$ROS_IP"
exec roslaunch --wait alfred_clever_lamp demo.launch "$@"
