# aifred_robot

ON BOTH RPI AND PC RUN THE `auto_edit_interbotix.sh` that you find in `aifred_descroption`

ON RPI:

```bash
roslaunch interbotix_xsarm_control xsarm_control.launch robot_model:=wx250s use_sim:=true use_rviz:=false
```


ON PC:

```bash
export ROS_MASTER_URI=http://<ip_raspberrypi>:11311
gringo@helena:~$ source catkin_ws/devel/setup.bash 
roslaunch interbotix_xsarm_descriptions remote_view.launch robot_name:=aifred
```
