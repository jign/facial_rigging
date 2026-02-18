# How to use

Ensure FacePoseDriver is available.

```
from FacePoseUI import startup
startup.start_tool()
```

## Features

### Pose Driving

### Pose Fixes
The TD will rig the face to create controls for all expressions, but suppose an animator wants to do some manual tweaks.
The rig should drive locators, not joints. Then the animator should be able to move either controls parented to those locators which in turn drive the joints, or the joints themselves.

Rig -> Master Locator -> Offset Locator -> Joint.

Because this feels like the best approach, then pose fixes are not handled by this system at all.

## Future TODOs

### Pose Blending
Different pose blending methods in the plugin (linear, exponential weighted, etc.) so that the animator can choose.

### Blendshapes (almost done)
The .mll plugin computes blendshape values either for simple poses or for combinations.

It uses a multiplication computation, so that if two poses are required, then

blendshape_value = norm(pose_a) * norm(pose_b)

If either pose is 0 (after normalization) then blendshape_val = 0.
When both poses are 1 then blendshape_val = 1.

The normalization is calculated from the min and max value of the connected pose.

The plugin has a compound array attribute called correctiveInputs. Each element of this array has an array of poses that controls that specific corrective blendshape.
It has an array output plug of floats, from 0 to 1, which drive each corrective blendshape for each combination of input attributes, called correctiveOutputs.
correctiveInputs[n] drives correctiveOutputs[n] from the array of pose weights connected to correctiveInputs[n]

Corrective outputs have a low and high output, for poses that span negative and positive values. When driving a blendshape from two poses, one of which has negative and positive values, and the other doesn't, only the side (high / low) where both driving poses overlap will get triggered.

If we absolutely need to drive a pose with cross-weights, we could still do it via the UI outside of the plugin. The python side could simply show a cross-weight button and then create via pymel a multiply divide node by -1, and feed that to the plugin.

The backend side on the C++ plugin code is done, but now I need to hook it up with the UI.

### Undo/Redo
I don't even want to think about that one.