<h1 align="center">AIfred2.0</h1>

### Virtual environment

Run these from the AIfred repository, after sourcing the ROS/catkin workspace.
The venv uses ROS Noetic's system Python (`/usr/bin/python3`) so the compiled ROS modules stay compatible.

**Recreate the venv (anyone cloning the repo)**
```bash
export PATH="$HOME/.local/bin:$PATH"
uv venv --python /usr/bin/python3 --system-site-packages
uv sync --locked --python /usr/bin/python3
source .venv/bin/activate
```

**Add or remove a dependency (it's saved to `pyproject.toml` and `uv.lock` automatically)**
```bash
uv add <package>       # e.g. uv add opencv-python
uv remove <package>
```
Commit `pyproject.toml` and `uv.lock` after every change. Don't use `pip install`, because it doesn't record anything.

**First-time project setup (already done by outors)**
```bash
uv init --bare --python /usr/bin/python3
uv venv --python /usr/bin/python3 --system-site-packages
```








### Create a package
```bash
cd ~/catkin_ws/src/AIfred
catkin_create_pkg aifred_<pkg> rospy std_msgs
```

add nodes

```bash
touch aifred_<pkg>/src/<node>.py # start with: #!/usr/bin/env python3
chmod +x aifred_<pkg>/src/<node>.py
```

Register the script in `aifred_mic/CMakeLists.txt`
```bash
catkin_install_python(PROGRAMS scripts/mic_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
```











### AIfred 2.0 description
This package create AIfred robot modle into the interbotics workspace. Run the auto edit bash file to be able to call the interbotics scripts with AIfred robot model.

### AIfred 2.0 camera
This package boot up the camera topic and publish the camera raw view.

```bash
roslaunch aifred_cam camera.launch      # publishes /aifred_cam/image_raw
```

### AIfred 2.0 microphone (wake up world)
This package uses the webcam microphone to listen to user comands. When user say the trigger word "ALFRED", it then publish the sentence to a topic.