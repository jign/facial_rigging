#pragma once

#include <maya/MGlobal.h>
#include <maya/MPxNode.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MAngle.h>
#include <vector>
#include <string>
#include <unordered_map>


class face_pose_driver final : public MPxNode
{
public:

	face_pose_driver();
	~face_pose_driver() override;
	// Add these to satisfy the Rule of Five by disabling copies/moves
	face_pose_driver(const face_pose_driver&) = delete;
	face_pose_driver& operator=(const face_pose_driver&) = delete;
	face_pose_driver(face_pose_driver&&) = delete;
	face_pose_driver& operator=(face_pose_driver&&) = delete;
	
	static void* creator();
	static MStatus initialize();

	MStatus compute(const MPlug& plug, MDataBlock& data) override;

	bool isPassiveOutput(const MPlug&) const override;
	MStatus setDependentsDirty(const MPlug& plug, MPlugArray& plug_array) override;
	MStatus connectionMade(const MPlug& plug, const MPlug& otherPlug, bool asSrc) override;
	MStatus connectionBroken(const MPlug& plug, const MPlug& otherPlug, bool asSrc) override;
	SchedulingType schedulingType() const override;

	static const MTypeId k_id;

	// Main pose driving

	static MObject a_linear_outputs;
	static MObject a_angular_outputs;

	static MObject a_poses; 
	static MObject a_linear_subposes;
	static MObject a_angular_subposes;
	static MObject a_pose_weight;
	
	// Blending
	
	static MObject a_blend_mode;

	// Corrective blendshapes

	static MObject a_corrective_outputs;  // Array of output values (0-1) for blendshapes
	static MObject a_corrective_output_high;   // High (positive) output values
	static MObject a_corrective_output_low;    // Low (negative) output values

	static MObject a_corrective_inputs;  // Array of corrective input sets
	static MObject a_corrective_input_poses;  // Array of input poses for a corrective

private:
	
	enum class blend_mode : short  // NOLINT(performance-enum-size)
	{
		k_legacy_normalized_weighted = 0,   // current behavior: sum(w^2*v)/sum(w^2), outputs 0 if sumW==0
		k_rest_normalized_weighted   = 1,   // (rest + sum(w^2*v)) / (1 + sum(w^2))  -> smooth to rest at 0
		k_rest_additive_linear       = 2    // rest + sum(w*(v-rest)) -> "literal ratio" feel, supports any rest (scale=1)
	};

	// A subpose is a structure that contains a weight and a value for a single output
	template<class T>
	requires (std::is_same_v<T, double> || std::is_same_v<T, MAngle>)
	using subpose = std::pair<double, T>;

	// For normalizing pose values between min and max
	struct pose_range {
		double min;
		double max;
	};

	// Per-output accumulators used by compute_poses.
	// Defined here so the member vectors below can reuse them across frames.
	struct linear_accum  { double sum_w = 0.0; double sum_vw   = 0.0; };
	struct angular_accum { double sum_w = 0.0; double sum_v_wr = 0.0; };

	// Pack two sparse array indices into a single 64-bit hash key
	static uint64_t pack_corrective_key(unsigned int corrective_idx, unsigned int pose_idx)
	{
		return (static_cast<uint64_t>(corrective_idx) << 32) | static_cast<uint64_t>(pose_idx);
	}

	// Cached corrective connection topology, maintained by connectionMade/Broken.
	// Maps (corrective_index, pose_index) -> source attribute's pose_range.
	// Eliminates all MPlug construction and DG queries from compute_correctives.
	std::unordered_map<uint64_t, pose_range> m_corrective_conn_ranges;

	// Cached pose weight ranges.  Key: pose logical index.
	// Maintained by connectionMade / connectionBroken.
	std::unordered_map<unsigned int, pose_range> m_pose_weight_ranges;

	// Cached per-pose subpose topology: which logical output indices exist
	// for each pose.  Rebuilt lazily on first compute after a connection change.
	struct pose_topology {
		std::vector<unsigned int> linear_indices;
		std::vector<unsigned int> angular_indices;
	};
	mutable std::unordered_map<unsigned int, pose_topology> m_pose_topology_cache;
	mutable bool m_topology_dirty = true;

	// Reusable scratch buffers for compute_poses().  Declared mutable so the
	// const compute method can clear()/resize() them without heap churn -
	// capacity survives across frames after the first evaluation.
	mutable std::vector<linear_accum>  m_linear_accums;
	mutable std::vector<angular_accum> m_angular_accums;
	mutable std::vector<double>        m_rest_linear;
	mutable std::vector<double>        m_rest_angular_rad;

	template<typename ... Args>
	static MString string_format(const std::string& format, Args ... args)
	{
		const int size_s = std::snprintf(nullptr, 0, format.c_str(), args ...) + 1; // Extra space for '\0'
		if (size_s <= 0) throw std::runtime_error("Error during formatting.");
		const auto size = static_cast<size_t>(size_s);
		const auto buf = std::make_unique<char[]>(size);
		const auto res = std::snprintf(buf.get(), size, format.c_str(), args ...);
		return std::string(buf.get(), buf.get() + size - 1).c_str(); // We don't want the '\0' inside
	}

	MStatus compute_poses(const MPlug& plug, MDataBlock& data) const;
	MStatus compute_correctives(const MPlug& plug, MDataBlock& data) const;
	void rebuild_topology_cache(MDataBlock& data) const;

	// Helper function to get min/max range from an attribute.
	// Plugin assumes the pose must have its min and max values set (part of the contract)
	static pose_range get_pose_range(const MPlug& pose_plug);
	// Helper function to normalize a pose value
	static double normalize_pose_value(double value, const pose_range& range);
	static std::pair<double, double> normalize_ranged_pose_value(double value, const pose_range& range);

	static void create_numeric_attributes();
	static void create_unit_attributes();
	static void create_compound_attributes();
	static void create_enum_attributes();
	static void create_corrective_attributes();
	static void add_attributes();
	static void set_attribute_affects();
};