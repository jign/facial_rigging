# Face Rigging System Demo

For demo purposes only. Requires PyMel.

# Installing and Building

## Python Utils (guides and UI)

Add the following paths to maya

```
sys.path.append(r"D:\piper\_lib\maya")
sys.path.append(r"D:\vitruvian\prj\face_rigger\src\face_pose_ui")
sys.path.append(r"D:\vitruvian\prj\face_rigger\src\face_jnt_guides")
```

Open `startup.py` for the Face Pose UI and Joint Guides tools and change this line to wherever you saved the tools if you want hot reload to work.

```
smu.reset_session_for_tool(r"D:\vitruvian\prj\face_rigger\src\face_jnt_guides\FaceJointGuides")
```

## Driver Node

Build the code, or use provided .mll for maya 2024 (I think it should work).

You need to configure the project to work with your own machine, or create a new empty plugin project and copypaste the code. If you've got a clean maya plugin template this is the fastest way for sure. Otherwise open `FacePoseDriver.vcxproj` and manually change all the paths.

You need to download the devkit for your maya version and then patch these links for every build configuration. 

- `ClCompile.AdditionalIncludeDirectories` Path to `includes` inside the devkit folder
- `Link.AdditionalLibraryDirectories` Path to `lib` inside the devkit folder

Just search and replace `D:\third_party\lib\maya_devkit\2024_win\devkitBase` with your devkit root folder. 

```
<ClCompile>
    <PrecompiledHeader>NotUsing</PrecompiledHeader>
    <WarningLevel>Level3</WarningLevel>
    <SDLCheck>true</SDLCheck>
    <PreprocessorDefinitions>WIN32;_DEBUG;FACEPOSEDRIVER_EXPORTS;_WINDOWS;_USRDLL;%(PreprocessorDefinitions);WIN32;NDEBUG;_WINDOWS;NT_PLUGIN;REQUIRE_IOSTREAM</PreprocessorDefinitions>
    <ConformanceMode>true</ConformanceMode>
    <PrecompiledHeaderFile>pch.h</PrecompiledHeaderFile>
    <AdditionalIncludeDirectories>D:\third_party\lib\maya_devkit\2024_win\devkitBase\include;%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>
</ClCompile>
<Link>
    <SubSystem>Windows</SubSystem>
    <GenerateDebugInformation>true</GenerateDebugInformation>
    <EnableUAC>false</EnableUAC>
    <OutputFile>$(OutDir)\$(ProjectName)$(TargetExt)</OutputFile>
    <AdditionalLibraryDirectories>D:\third_party\lib\maya_devkit\2024_win\devkitBase\lib;%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>
    <AdditionalDependencies>Foundation.lib;OpenMaya.lib;OpenMayaUI.lib;OpenMayaAnim.lib;OpenMayaFX.lib;OpenMayaRender.lib;Image.lib;opengl32.lib;glu32.lib;%(AdditionalDependencies)</AdditionalDependencies>
    <AdditionalOptions>/export:initializePlugin /export:uninitializePlugin %(AdditionalOptions)</AdditionalOptions>
</Link>
```

The code is quite messy, don't judge me.

## Launching the tools

```
# Guides
from FaceJointGuides import startup as jntsu
jntsu.start_tool()

# Face Pose UI
import FacePoseUI.startup as fsu
fsu.start_tool()
```

# Architecture

A pose is a slider driving some number of controlled objects, generally locators but maya doesn't care. Poses live inside hosts and they're identified by `host_name.pose_name`.

A subpose is each driven attribute. They're identified by `target_obj_name.attr_name`.

Each subpose is driven by a blend of anim curves.

Poses are stored in an array attribute of the driver node. The driver keeps one output plug for each driven attribute (subpose). 

The driver node uses logical indices to match against incoming and outgoing subposes. So for example if the driven attribute `target_loc.tx` lives at logical index 5 of the driver's linear attributes, then the tool will wire up the anim curve for that subpose to the 5th logical index of the input pose array, regardless of what physical index maya gives the plug. If you don't know how maya handlex array plugs, the tl;dr is that you can use logical indices to identify each plug, but maya will use a physical index internally for performance.

Each subpose is blended according to its pose weight. There are three blending modes, but the linear blending mode is the only one working as intended, as the other two don't support rest poses of anything but 0 for now (for example, scale should have a rest pose of 1.0).

For example, if we have `mouth_corner_up_down` and `mouth_ourner_out_in` driving some `mouth_corner_jnt_ctrl.tx` and we have `mouth_corner_up_down` at 8 and `mouth_ourner_out_in` at 2 the final .tx location will be 80% and 20% of each pose respectively. Blending isn't additive so double transforms aren't a problem.

# Demo Rig and Tutorial

Add `chara_mesh.abc` to your scene, then load the `chara_body_guides.sgt` guide template.

Import the `face_guides.mb` file. I don't have a proper interchange format yet so just import them raw. Make sure to uncheck Use Namespaces in the import file dialogue, and set Resolve to Clashing nodes only, so that it won't append the name of the file to all the imported nodes.

Open the Face Guides tool. Double click on point locator. Rename it to whatever you want and save it under any group in the hierarchy. We'll use these groups to control different clusters of joints.

If your guide starts with `l_` you can try mirroring if you want.

Select the top hierarchy and click build from selection. Right now there's no "build from selection," the button lies. There's only "build" functionality and it requires that you have the hierarchy top group selected.

Scaling of joints/locators isn't working that well right now, so isolate `facial_rig_grp/jnts_grp` and select all joints and set a reasonable radius like 0.25. The eyelid joints won't be selected by default so you'll have to select them manually. This is obviously not ideal but I didn't have the time to think of how to properly set scaling on the guides.

Now select `facial_rig_grp/rig_grp`, isolate, drag select all locators and set the local scale (not the world scale) to a more reasonable value.

For this part please watch `parenting_joints_and_controllers` for a short video.

For each group of joints created in the facial rig folder, parent them as needed. For example, reparent the "head" hierarchy to the head joint in the mgear build. This keeps our joint hierarchy under one root without intermediate nodes.

For each intermediate rig group, create a parent constraint to the required joint so that they follow.

Do the same for the neck joints and controls, a goes to neck_01 and b goes to neck_02.

I'm sorry for having you do this manually. This should be automated of course, but it is what it is.

Now import `face_controls.abc`.

Open the Face Pose UI. Click Load Rig at the top and select `face_rig.json`. Wait and pray that everything works.

Select the head and load `head_skin.jSkin`.

Try playing around with the sliders in the face controls. Now it's a good time to inspect the node graph, etc.

Let's add a pose. Please watch `create_new_pose` and `mirror_pose` before proceeding.

Select `l_cheek_ctrl` and click on the + button. Then click on Load Driven Objects and select on the scene the locators that you want to drive. Click Load Driven and drag select all of them. Then drag select all attributes. The attributes are hardcoded for now. Click add.

Now drag the newly created slider all the way to the max and pose all locators as you want. Bear in mind that right now if there's other poses driving these locators you're going to get unexpected results, so make sure to zero them out if you are. Click Capture Pose. If you want you can click Capture Pose as many times as you want, it'll just update what you have.

You can try manually changing the keys if you want, and that's the gist of it. You can try clicking +/- on the pose to mirror it as long as the host object begins with `l_` (improving mirroring is a high priority task).


