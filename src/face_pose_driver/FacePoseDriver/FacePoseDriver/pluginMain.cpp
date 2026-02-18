#include <maya/MFnPlugin.h>
#include <string>
#include "facePoseDriver.h"

static const std::string kVersion{"0.0.13"};

MStatus initializePlugin(MObject obj) {
	MStatus status = MStatus::kSuccess;

	MFnPlugin plugin(obj, "jignb", kVersion.c_str(), "Any");

	status = plugin.registerNode("facePoseDriver", face_pose_driver::k_id, &face_pose_driver::creator, &face_pose_driver::initialize);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	return status;
}

MStatus uninitializePlugin(MObject obj) {
	MStatus status = MStatus::kSuccess;

	MFnPlugin plugin(obj);

	status = plugin.deregisterNode(face_pose_driver::k_id);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	return status;
}