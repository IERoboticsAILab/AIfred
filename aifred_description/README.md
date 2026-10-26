# What it does
1. Copies this files into the `interbotics` workspace:

    - `urdf/aifred.urdf.xacro` goes to `interbotix_xsarm_descriptions/urdf/`
    - `meshes/*` goes to `interbotix_xsarm_descriptions/meshes/aifred_meshes/`
    - `config/aifred.yaml` goes to `interbotix_xsarm_control/config/`

2. Adds the aifred kinematics to mr_descriptions.py so the Python API works. It skips this if the entry is already there.
3. Patches the simulator so `use_sim:=true` doesn't crash on the gripper entry in modes.yaml.

Each run just overwrites the files with your latest versions.

# How to run it
Make it executable once and run it:
```bash
chmod +x install_aifred.sh
./install_aifred.sh                      # workspace at ~/interbotix_ws
#./install_aifred.sh /path/to/other_ws    # workspace somewhere else
```

Launch as usual:

```bash
roslaunch interbotix_xsarm_control xsarm_control.launch robot_model:=aifred
```

You don't need to rebuild with catkin_make, because only data files and Python files change.