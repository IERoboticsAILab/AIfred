# What it does
Publishes the webcam image to ROS using the standard `usb_cam` driver. No custom code, just a launch file with AIfred's settings:

- Device: `/dev/video0`
- Format: MJPEG (faster than YUYV on most webcams)
- Resolution: 640x480 at 30 fps
- Frame: `camera_link`

Topics:
- `/aifred_cam/image_raw`: raw image
- `/aifred_cam/image_raw/compressed`: compressed image (use this when streaming to another machine)
- `/aifred_cam/camera_info`: camera info

# How I made it
```bash
sudo apt install ros-noetic-usb-cam
cd ~/catkin_ws/src/AIfred
catkin_create_pkg aifred_cam usb_cam
mkdir aifred_cam/launch          # then wrote launch/camera.launch
```

# How to run it
Build once:
```bash
cd ~/catkin_ws
catkin build aifred_cam
source devel/setup.bash
```

Launch:
```bash
roslaunch aifred_cam camera.launch
```

Check the image:
```bash
rqt_image_view /aifred_cam/image_raw
```

To change device, resolution or fps, edit `launch/camera.launch`. To see what your webcam supports:
```bash
v4l2-ctl --list-formats-ext -d /dev/video0     # sudo apt install v4l-utils
```
