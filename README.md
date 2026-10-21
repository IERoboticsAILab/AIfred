# aifred_robot


Interbotix WX250s with the AIfred base and head (webcam + projector) replacing the gripper.
URDF, bringup launch, and IK that uses the camera as the end effector. The interbotix
workspace (`~/interbotix_ws`) is only used, never modified: it provides the driver
(`interbotix_xs_sdk`), the arm meshes, and the Python API.

Interbotix WX250s with the AIfred base and head (camera + projector) instead of the gripper.

```bash
# both machines, once
cd ~/catkin_ws && catkin build aifred_robot && source devel/setup.bash
```


```bash
# Raspberry Pi (arm connected, ROS master)
roslaunch aifred_robot robot.launch

# PC (ROS_MASTER_URI = Raspberry Pi)
roslaunch aifred_robot view.launch
rosrun aifred_robot bartender.py
```

```bash
# Raspberry Pi (arm connected, ROS master)
roslaunch interbotix_xsarm_control xsarm_control.launch robot_model:=wx250s use_rviz:=false   motor_configs:=$(rospack find aifred_robot)/config/wx250s_aifred.yaml   mode_configs:=$(rospack find aifred_robot)/config/modes.yaml   external_urdf_loc:=""

# PC (ROS_MASTER_URI = Raspberry Pi)
roslaunch interbotix_xsarm_descriptions remote_view.launch robot_name:=wx250s
```












IK with the camera as end effector (`wx250s/camera_link`, looks along -z, so `pitch=0` = looking down):

```python
from aifred_robot.arm import AIfredManipulator
bot = AIfredManipulator(init_node=False)
bot.arm.set_ee_pose_components(x=0.3, y=0.0, z=0.3)  # camera 30 cm above (0.3, 0), looking down
```