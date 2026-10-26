#!/bin/bash
# Installs the AIfred robot model into an existing Interbotix workspace.
# Usage: ./install_aifred.sh [workspace]   (default workspace: ~/interbotix_ws)
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
WS="${1:-$HOME/interbotix_ws}"
XSARMS="$WS/src/interbotix_ros_manipulators/interbotix_ros_xsarms"
MODULES="$WS/src/interbotix_ros_toolboxes/interbotix_xs_toolbox/interbotix_xs_modules/src/interbotix_xs_modules"
SDK_SIM="$WS/src/interbotix_ros_core/interbotix_ros_xseries/interbotix_xs_sdk/scripts/xs_sdk_sim"

[ -d "$XSARMS" ] || { echo "Interbotix workspace not found at $WS"; exit 1; }

# 1. URDF, meshes and motor config
cp "$SRC"/urdf/aifred.urdf.xacro "$XSARMS/interbotix_xsarm_descriptions/urdf/"
mkdir -p "$XSARMS/interbotix_xsarm_descriptions/meshes/aifred_meshes"
cp "$SRC"/meshes/* "$XSARMS/interbotix_xsarm_descriptions/meshes/aifred_meshes/"
cp "$SRC"/config/aifred.yaml "$XSARMS/interbotix_xsarm_control/config/"

# 2. Kinematics for the Python API (added only once)
if ! grep -q "^class aifred:" "$MODULES/mr_descriptions.py"; then
cat >> "$MODULES/mr_descriptions.py" <<'EOF'

class aifred:
    Slist = np.array([[0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                      [0.0, 1.0, 0.0, -0.11065, 0.0, 0.0],
                      [0.0, 1.0, 0.0, -0.36065, 0.0, 0.04975],
                      [1.0, 0.0, 0.0, 0.0, 0.36065, 0.0],
                      [0.0, 1.0, 0.0, -0.36065, 0.0, 0.29975]]).T

    M = np.array([[1.0, 0.0, 0.0, 0.36775],
                  [0.0, 1.0, 0.0, 0.0],
                  [0.0, 0.0, 1.0, 0.36065],
                  [0.0, 0.0, 0.0, 1.0]])
EOF
fi

# 3. Simulator: warn instead of crash on the gripper entry in modes.yaml
sed -i 's/self.robot_set_joint_operating_mode(sgl, /self.robot_set_operating_modes("single", sgl, /' "$SDK_SIM"

echo "AIfred installed in $WS"
echo "Run: roslaunch interbotix_xsarm_control xsarm_control.launch robot_model:=aifred"
