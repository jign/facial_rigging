#include "facePoseDriver.h"
#include <maya/MArrayDataHandle.h>
#include <maya/MDataHandle.h>
#include <maya/MArrayDataBuilder.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnEnumAttribute.h>
#include <maya/MFnUnitAttribute.h>
#include <maya/MFnCompoundAttribute.h>
#include <utility>
#include <algorithm>
#include <unordered_map>


const MTypeId face_pose_driver::k_id(0x00000169);

MObject face_pose_driver::a_linear_outputs;
MObject face_pose_driver::a_angular_outputs;
MObject face_pose_driver::a_poses;
MObject face_pose_driver::a_linear_subposes;
MObject face_pose_driver::a_angular_subposes;
MObject face_pose_driver::a_pose_weight;

MObject face_pose_driver::a_blend_mode;

MObject face_pose_driver::a_corrective_outputs;
MObject face_pose_driver::a_corrective_output_high;
MObject face_pose_driver::a_corrective_output_low;
MObject face_pose_driver::a_corrective_inputs;
MObject face_pose_driver::a_corrective_input_poses;

face_pose_driver::face_pose_driver() = default;

face_pose_driver::~face_pose_driver() = default;

void* face_pose_driver::creator()
{
	return new face_pose_driver();
}

MStatus face_pose_driver::initialize()
{
	MStatus status = MStatus::kSuccess;

	create_numeric_attributes();
	create_unit_attributes();
	create_compound_attributes();
	create_enum_attributes();
	create_corrective_attributes();

	add_attributes();
	set_attribute_affects();

	return status;
}

MStatus face_pose_driver::compute(const MPlug& plug, MDataBlock& data)
{
	// Handle original linear/angular outputs
	if (plug == a_linear_outputs || plug == a_angular_outputs ||
		plug.parent() == a_linear_outputs || plug.parent() == a_angular_outputs) {
		return compute_poses(plug, data);
	}

	// Handle corrective blendshape outputs
	if (plug == a_corrective_outputs || plug.parent() == a_corrective_outputs) {
		return compute_correctives(plug, data);
	}

	return MS::kSuccess;
}

bool face_pose_driver::isPassiveOutput(const MPlug& plug) const
{
	if(plug == a_linear_outputs || plug == a_angular_outputs || plug.parent() == a_angular_outputs || plug.parent() == a_linear_outputs) {
		return true;
	}
	return MPxNode::isPassiveOutput(plug);
}

MStatus face_pose_driver::setDependentsDirty(const MPlug& plug, MPlugArray& plug_array)
{
    auto append_array_parent = [&](const MObject& arr_attr)
    {
        plug_array.append(MPlug(thisMObject(), arr_attr));
    };

    auto append_array_elem = [&](const MObject& arr_attr, const unsigned int logical_index)
    {
        MStatus s;
        MPlug arr_plug(thisMObject(), arr_attr);
        MPlug elem = arr_plug.elementByLogicalIndex(logical_index, &s);
        if (s) plug_array.append(elem);
    };

    const MObject attr = plug.attribute();

    // -------- Main pose driving (fine-grained) --------

    // If a single subpose changes, only that output index is affected.
    if (attr == a_linear_subposes)
    {
        append_array_elem(a_linear_outputs, plug.logicalIndex());
        return MS::kSuccess;
    }
    if (attr == a_angular_subposes)
    {
        append_array_elem(a_angular_outputs, plug.logicalIndex());
        return MS::kSuccess;
    }

    // Pose weight can affect multiple outputs (all subposes authored on that pose).
    // Use cached topology if available; otherwise fall back to dirtying all.
    if (attr == a_pose_weight)
    {
        const unsigned int pose_idx = plug.parent().logicalIndex();

        if (!m_topology_dirty)
        {
            const auto topo_it = m_pose_topology_cache.find(pose_idx);
            if (topo_it != m_pose_topology_cache.end())
            {
                for (const unsigned int out_idx : topo_it->second.linear_indices)
                    append_array_elem(a_linear_outputs, out_idx);

                for (const unsigned int out_idx : topo_it->second.angular_indices)
                    append_array_elem(a_angular_outputs, out_idx);

                return MS::kSuccess;
            }
        }

        // Conservative fallback
        append_array_parent(a_linear_outputs);
        append_array_parent(a_angular_outputs);
        return MS::kSuccess;
    }

    // Blend mode affects all outputs (global).
    if (plug == a_blend_mode)
    {
        append_array_parent(a_linear_outputs);
        append_array_parent(a_angular_outputs);
        return MS::kSuccess;
    }

    // Any other unknown edit under poses: conservative fallback.
    if (plug == a_poses || plug.parent() == a_poses)
    {
        append_array_parent(a_linear_outputs);
        append_array_parent(a_angular_outputs);
        // continue; don't return yet, could also be corrective
    }

    // -------- Correctives (fine-grained) --------

    // If a corrective input pose changes, only correctiveOutputs[correctiveIndex] is affected.
    if (attr == a_corrective_input_poses)
    {
        // plug is correctiveInputs[corrective_idx].correctiveInputPose[pose_idx]
        const MPlug corrective_elem = plug.array().parent(); // correctiveInputs[corrective_idx]
        const unsigned int corrective_idx = corrective_elem.logicalIndex();

        append_array_elem(a_corrective_outputs, corrective_idx);
        return MS::kSuccess;
    }

    // Conservative fallback for other corrective edits
    if (plug == a_corrective_inputs || plug.parent() == a_corrective_inputs)
    {
        append_array_parent(a_corrective_outputs);
        return MS::kSuccess;
    }

    return MS::kSuccess;
}

MStatus face_pose_driver::connectionMade(const MPlug& plug, const MPlug& otherPlug, bool asSrc)
{
	if (!asSrc)
	{
		const MObject attr = plug.attribute();

		// Cache corrective input pose ranges so compute_correctives never has
		// to build MPlug paths or query the DG for connection info.
		if (attr == a_corrective_input_poses)
		{
			const unsigned int pose_idx       = plug.logicalIndex();
			const MPlug parent_element        = plug.array().parent();  // correctiveInputs[i]
			const unsigned int corrective_idx = parent_element.logicalIndex();

			pose_range range{.min = 0.0, .max = 1.0};
			MStatus status;
			const MFnNumericAttribute num_attr(otherPlug.attribute(), &status);
			if (status)
			{
				if (num_attr.hasMin()) num_attr.getMin(range.min);
				if (num_attr.hasMax()) num_attr.getMax(range.max);
				if (range.min == range.max) range = {.min = 0.0, .max = 1.0};
			}

			m_corrective_conn_ranges[pack_corrective_key(corrective_idx, pose_idx)] = range;
		}

		// Cache the source attribute's min/max so compute_poses can normalize
		// the weight without hard-coded assumptions about the driving range.
		if (attr == a_pose_weight)
		{
			const unsigned int pose_idx = plug.parent().logicalIndex();

			pose_range range{.min = 0.0, .max = 1.0};
			MStatus status;
			const MFnNumericAttribute num_attr(otherPlug.attribute(), &status);
			if (status)
			{
				if (num_attr.hasMin()) num_attr.getMin(range.min);
				if (num_attr.hasMax()) num_attr.getMax(range.max);
				if (range.min == range.max) range = {.min = 0.0, .max = 1.0};
			}

			m_pose_weight_ranges[pose_idx] = range;
		}

		// Invalidate subpose topology cache when connections change.
		// We use connectionMade/Broken rather than setDependentsDirty so that
		// value-only dirty propagation (every frame) does not trigger a rebuild.
		if (attr == a_linear_subposes || attr == a_angular_subposes)
		{
			m_topology_dirty = true;
		}
	}

	return MPxNode::connectionMade(plug, otherPlug, asSrc);
}

MStatus face_pose_driver::connectionBroken(const MPlug& plug, const MPlug& otherPlug, bool asSrc)
{
	if (!asSrc)
	{
		const MObject attr = plug.attribute();

		if (attr == a_corrective_input_poses)
		{
			const unsigned int pose_idx       = plug.logicalIndex();
			const MPlug parent_element        = plug.array().parent();
			const unsigned int corrective_idx = parent_element.logicalIndex();

			m_corrective_conn_ranges.erase(pack_corrective_key(corrective_idx, pose_idx));
		}

		if (attr == a_pose_weight)
		{
			m_pose_weight_ranges.erase(plug.parent().logicalIndex());
		}

		if (attr == a_linear_subposes || attr == a_angular_subposes)
		{
			m_topology_dirty = true;
		}
	}

	return MPxNode::connectionBroken(plug, otherPlug, asSrc);
}

MPxNode::SchedulingType face_pose_driver::schedulingType() const
{
    return MPxNode::SchedulingType::kParallel;
}


void face_pose_driver::rebuild_topology_cache(MDataBlock& data) const
{
	m_pose_topology_cache.clear();
	m_topology_dirty = false;

	MStatus status;
	MArrayDataHandle ah_poses = data.inputArrayValue(a_poses, &status);
	if (!status) return;

	const unsigned int num_poses = ah_poses.elementCount();
	for (unsigned int p = 0; p < num_poses; ++p)
	{
		const unsigned int pose_idx = ah_poses.elementIndex();
		MDataHandle h_pose = ah_poses.inputValue(&status);
		if (!status) { if (!ah_poses.next()) break; continue; }

		pose_topology topo;

		MArrayDataHandle ah_lin = h_pose.child(a_linear_subposes);
		const unsigned int n_lin = ah_lin.elementCount();
		topo.linear_indices.reserve(n_lin);
		for (unsigned int s = 0; s < n_lin; ++s)
		{
			topo.linear_indices.push_back(ah_lin.elementIndex());
			if (!ah_lin.next()) break;
		}

		MArrayDataHandle ah_ang = h_pose.child(a_angular_subposes);
		const unsigned int n_ang = ah_ang.elementCount();
		topo.angular_indices.reserve(n_ang);
		for (unsigned int s = 0; s < n_ang; ++s)
		{
			topo.angular_indices.push_back(ah_ang.elementIndex());
			if (!ah_ang.next()) break;
		}

		m_pose_topology_cache[pose_idx] = std::move(topo);
		if (!ah_poses.next()) break;
	}
}

MStatus face_pose_driver::compute_poses(const MPlug& plug, MDataBlock& data) const
{
    MStatus status = MS::kSuccess;

	// Rebuild topology cache if connections changed since last compute.
	if (m_topology_dirty) {
		rebuild_topology_cache(data);
	}

	const short blend_mode_raw = data.inputValue(a_blend_mode, &status).asShort();
	CHECK_MSTATUS_AND_RETURN_IT(status)
	const auto current_blend_mode = static_cast<blend_mode>(blend_mode_raw);
	
	// Convention (no extra plugs): poses[0] is treated as a per-output "rest pose"
	// for rest-based blend modes. If poses[0] is not authored, rest defaults to 0.
	// const bool use_rest_pose_index0 =
	// 	(current_blend_mode == blend_mode::k_rest_normalized_weighted) ||
	// 	(current_blend_mode == blend_mode::k_rest_additive_linear);
	const bool use_rest_pose_index0 = false; // temp testing
	
    // Reuse member vectors - clear() keeps heap capacity from previous frames,
    // so resize() inside the inner loops never allocates after the first evaluation.
    m_rest_linear.clear();
    m_rest_angular_rad.clear();
    m_linear_accums.clear();
    m_angular_accums.clear();

    // Aliases for readability (reference to member, zero cost)
    auto& rest_linear      = m_rest_linear;
    auto& rest_angular_rad = m_rest_angular_rad;
    auto& linear_accums    = m_linear_accums;
    auto& angular_accums   = m_angular_accums;

    // --- Pre-size accumulators to match output array extents ---
    // This eliminates NxM branch+resize checks per frame (N poses x M subposes).
    {
        MArrayDataHandle ah_lin_out = data.outputArrayValue(a_linear_outputs, &status);
        CHECK_MSTATUS_AND_RETURN_IT(status)
        const unsigned int n_lin = ah_lin_out.elementCount();
        if (n_lin > 0) {
            ah_lin_out.jumpToArrayElement(n_lin - 1);
            linear_accums.resize(ah_lin_out.elementIndex() + 1);
            rest_linear.resize(linear_accums.size(), 0.0);
        }
    }
    {
        MArrayDataHandle ah_ang_out = data.outputArrayValue(a_angular_outputs, &status);
        CHECK_MSTATUS_AND_RETURN_IT(status)
        const unsigned int n_ang = ah_ang_out.elementCount();
        if (n_ang > 0) {
            ah_ang_out.jumpToArrayElement(n_ang - 1);
            angular_accums.resize(ah_ang_out.elementIndex() + 1);
            rest_angular_rad.resize(angular_accums.size(), 0.0);
        }
    }

    // Choose weight transform once, before the pose loop.
    // blend_mode is invariant across the entire evaluation.
    auto weight_fn = [current_blend_mode](double pw) -> double {
        return (current_blend_mode == blend_mode::k_rest_additive_linear)
            ? pw
            : pw * pw;
    };

    MArrayDataHandle ah_poses = data.inputArrayValue(a_poses, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status)

    const unsigned int num_poses = ah_poses.elementCount();
    for (unsigned int p = 0; p < num_poses; ++p)
    {
    	const unsigned int pose_logical_index = ah_poses.elementIndex();
    	
        MDataHandle h_current_pose = ah_poses.inputValue(&status);
        CHECK_MSTATUS_AND_RETURN_IT(status)
    	
    	const bool is_rest_pose = use_rest_pose_index0 && (pose_logical_index == 0);

    	const double pose_weight_raw = h_current_pose.child(a_pose_weight).asDouble();
		// Normalize using cached source-attribute range, falling back to 0-1
		// clamp when the weight is not connected (no cached range available).
		// const auto pw_it = m_pose_weight_ranges.find(pose_logical_index);
		// const double pose_weight = (pw_it != m_pose_weight_ranges.end())
		// 	? normalize_pose_value(pose_weight_raw, pw_it->second)
		// 	: std::max(0.0, std::min(1.0, pose_weight_raw));
    	const double pose_weight_abs = std::abs(pose_weight_raw);
    	// for development assume poses are -10 to 10 or 0 to 10.
    	const double pose_weight = std::min(pose_weight_abs / 10.0, 1.0);

		// Early out: zero weight contributes nothing to any output.
		// In facial rigs most poses are inactive on any given frame, so this
		// typically skips the vast majority of inner-loop iterations.
		if (pose_weight == 0.0)
		{
			if (!ah_poses.next()) break;
			continue;
		}

    	const double w = weight_fn(pose_weight);

        // Look up cached topology for this pose
        const auto topo_it = m_pose_topology_cache.find(pose_logical_index);

        // Linear subposes — skip entirely if topology cache confirms this pose has none
        if (topo_it == m_pose_topology_cache.end() || !topo_it->second.linear_indices.empty())
        {
            MArrayDataHandle ah_linear_subposes = h_current_pose.child(a_linear_subposes);

            if (topo_it != m_pose_topology_cache.end())
            {
                // Cached path: jump directly to known element indices, avoiding
                // the per-element elementIndex() overhead of sequential iteration.
                for (const unsigned int out_idx : topo_it->second.linear_indices)
                {
                    status = ah_linear_subposes.jumpToElement(out_idx);
                    if (!status) continue;

                    MDataHandle h_sub = ah_linear_subposes.inputValue(&status);
                    CHECK_MSTATUS_AND_RETURN_IT(status)

                    const double v = h_sub.asDouble();

                    if (is_rest_pose)
                    {
                        rest_linear[out_idx] = v;
                    }
                    else
                    {
                        linear_accums[out_idx].sum_w += w;
                        linear_accums[out_idx].sum_vw += (v * w);
                    }
                }
            }
            else
            {
                // Fallback: sequential iteration (topology cache unavailable)
                const unsigned int num_linear = ah_linear_subposes.elementCount();
                for (unsigned int s = 0; s < num_linear; ++s)
                {
                    const unsigned int out_idx = ah_linear_subposes.elementIndex();

                    MDataHandle h_sub = ah_linear_subposes.inputValue(&status);
                    CHECK_MSTATUS_AND_RETURN_IT(status)

                    const double v = h_sub.asDouble();

                    if (is_rest_pose)
                    {
                        rest_linear[out_idx] = v;
                    }
                    else
                    {
                        linear_accums[out_idx].sum_w += w;
                        linear_accums[out_idx].sum_vw += (v * w);
                    }

                    if (!ah_linear_subposes.next())
                        break;
                }
            }
        }

        // Angular subposes — skip entirely if topology cache confirms this pose has none
        if (topo_it == m_pose_topology_cache.end() || !topo_it->second.angular_indices.empty())
        {
            MArrayDataHandle ah_angular_subposes = h_current_pose.child(a_angular_subposes);

            if (topo_it != m_pose_topology_cache.end())
            {
                for (const unsigned int out_idx : topo_it->second.angular_indices)
                {
                    status = ah_angular_subposes.jumpToElement(out_idx);
                    if (!status) continue;

                    MDataHandle h_sub = ah_angular_subposes.inputValue(&status);
                    CHECK_MSTATUS_AND_RETURN_IT(status)

                    const double rad = h_sub.asAngle().asRadians();

                    if (is_rest_pose)
                    {
                        rest_angular_rad[out_idx] = rad;
                    }
                    else
                    {
                        angular_accums[out_idx].sum_w += w;
                        angular_accums[out_idx].sum_v_wr += (rad * w);
                    }
                }
            }
            else
            {
                const unsigned int num_angular = ah_angular_subposes.elementCount();
                for (unsigned int s = 0; s < num_angular; ++s)
                {
                    const unsigned int out_idx = ah_angular_subposes.elementIndex();

                    MDataHandle h_sub = ah_angular_subposes.inputValue(&status);
                    CHECK_MSTATUS_AND_RETURN_IT(status)

                    const double rad = h_sub.asAngle().asRadians();

                    if (is_rest_pose)
                    {
                        rest_angular_rad[out_idx] = rad;
                    }
                    else
                    {
                        angular_accums[out_idx].sum_w += w;
                        angular_accums[out_idx].sum_v_wr += (rad * w);
                    }

                    if (!ah_angular_subposes.next())
                        break;
                }
            }
        }

        if (!ah_poses.next())
            break;
    }

	auto eval_linear_out = [&](const unsigned int out_idx) -> double {
		const double rest = (out_idx < rest_linear.size()) ? rest_linear[out_idx] : 0.0;

		if (out_idx >= linear_accums.size())
			return (current_blend_mode == blend_mode::k_legacy_normalized_weighted) ? 0.0 : rest;

		const auto& a = linear_accums[out_idx];

		switch (current_blend_mode)
		{
		case blend_mode::k_legacy_normalized_weighted:
			return (a.sum_w != 0.0) ? (a.sum_vw / a.sum_w) : 0.0;

		case blend_mode::k_rest_normalized_weighted:
			// (rest + sum(w^2 * v)) / (1 + sum(w^2))
			return (rest + a.sum_vw) / (1.0 + a.sum_w);

		case blend_mode::k_rest_additive_linear:
			// rest + sum(w * (v - rest)) = rest + sum(w*v) - rest*sum(w)
			return rest + a.sum_vw - (rest * a.sum_w);
		}

		return 0.0;
	};

	auto eval_angular_out_rad = [&](const unsigned int out_idx) -> double
	{
		const double rest = (out_idx < rest_angular_rad.size()) ? rest_angular_rad[out_idx] : 0.0;

		if (out_idx >= angular_accums.size())
			return (current_blend_mode == blend_mode::k_legacy_normalized_weighted) ? 0.0 : rest;

		const auto& a = angular_accums[out_idx];

		switch (current_blend_mode)
		{
		case blend_mode::k_legacy_normalized_weighted:
			return (a.sum_w != 0.0) ? (a.sum_v_wr / a.sum_w) : 0.0;

		case blend_mode::k_rest_normalized_weighted:
			return (rest + a.sum_v_wr) / (1.0 + a.sum_w);

		case blend_mode::k_rest_additive_linear:
			return rest + a.sum_v_wr - (rest * a.sum_w);
		}

		return 0.0;
	};
	
    // Write linear outputs
    {
        MArrayDataHandle ah_linear_outputs = data.outputArrayValue(a_linear_outputs, &status);
        CHECK_MSTATUS_AND_RETURN_IT(status)

        const unsigned int num_out = ah_linear_outputs.elementCount();
        for (unsigned int i = 0; i < num_out; ++i)
        {
            const unsigned int out_idx = ah_linear_outputs.elementIndex();

            MDataHandle h_out = ah_linear_outputs.outputValue(&status);
            CHECK_MSTATUS_AND_RETURN_IT(status)

        	const double out_val = eval_linear_out(out_idx);

            h_out.setDouble(out_val);
            h_out.setClean();

            if (!ah_linear_outputs.next())
                break;
        }

        // Important: mark the *parent* array clean to avoid recomputing per-element.
        data.setClean(MPlug(thisMObject(), a_linear_outputs));
    }

    // Write angular outputs
    {
        MArrayDataHandle ah_angular_outputs = data.outputArrayValue(a_angular_outputs, &status);
        CHECK_MSTATUS_AND_RETURN_IT(status)

        const unsigned int num_out = ah_angular_outputs.elementCount();
        for (unsigned int i = 0; i < num_out; ++i)
        {
            const unsigned int out_idx = ah_angular_outputs.elementIndex();

            MDataHandle h_out = ah_angular_outputs.outputValue(&status);
            CHECK_MSTATUS_AND_RETURN_IT(status)

        	const double out_rad = eval_angular_out_rad(out_idx);
        	const MAngle out_val(out_rad); // radians

            h_out.setMAngle(out_val);
            h_out.setClean();

            if (!ah_angular_outputs.next())
                break;
        }

        // Important: mark the *parent* array clean to avoid recomputing per-element.
        data.setClean(MPlug(thisMObject(), a_angular_outputs));
    }

    // Also clean the requested plug (safe even if Maya asked for an element)
    data.setClean(plug);

    return status;
}

MStatus face_pose_driver::compute_correctives(const MPlug& plug, MDataBlock& data) const
{
    MStatus status = MS::kSuccess;

    // Input/output handles
    MArrayDataHandle ah_corrective_inputs = data.inputArrayValue(a_corrective_inputs, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status)

    MArrayDataHandle ah_corrective_outputs = data.outputArrayValue(a_corrective_outputs, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status)

    // Iterate outputs sparsely (logical-index correct)
    const unsigned int num_out_elems = ah_corrective_outputs.elementCount();
    for (unsigned int out_pos = 0; out_pos < num_out_elems; ++out_pos)
    {
        const unsigned int out_logical_index = ah_corrective_outputs.elementIndex();

        MDataHandle h_out_compound = ah_corrective_outputs.outputValue(&status);
        CHECK_MSTATUS_AND_RETURN_IT(status)

        MDataHandle h_out_high = h_out_compound.child(a_corrective_output_high);
        MDataHandle h_out_low  = h_out_compound.child(a_corrective_output_low);

        double combined_high_value = 1.0;
        double combined_low_value  = 1.0;
        bool has_valid_poses_high = false;
        bool has_valid_poses_low  = false;

        // Match input element by logical index (sparse-safe)
        status = ah_corrective_inputs.jumpToElement(out_logical_index);
        if (!status) {
            // No input for this output => 0
            h_out_high.setDouble(0.0);
            h_out_low.setDouble(0.0);
            h_out_low.setClean();
            h_out_high.setClean();
            h_out_compound.setClean();

            if (!ah_corrective_outputs.next()) break;
            continue;
        }

        MDataHandle h_in_compound = ah_corrective_inputs.inputValue(&status);
        CHECK_MSTATUS_AND_RETURN_IT(status)

        MArrayDataHandle ah_poses = h_in_compound.child(a_corrective_input_poses);

        const unsigned int num_pose_elems = ah_poses.elementCount();
        for (unsigned int pose_pos = 0; pose_pos < num_pose_elems; ++pose_pos)
        {
            const unsigned int pose_logical_index = ah_poses.elementIndex();

            // O(1) cache lookup replaces 4-5 MPlug API calls + DG source() query per element.
            // The cache is maintained by connectionMade / connectionBroken.
            const uint64_t conn_key = pack_corrective_key(out_logical_index, pose_logical_index);
            const auto conn_it = m_corrective_conn_ranges.find(conn_key);
            if (conn_it == m_corrective_conn_ranges.end())
            {
                // Not connected – skip this element
                if (!ah_poses.next()) break;
                continue;
            }

            MDataHandle h_pose = ah_poses.inputValue(&status);
            CHECK_MSTATUS_AND_RETURN_IT(status)

            const double pose_value = h_pose.asDouble();
            if (pose_value == 0.0) {
                combined_high_value = 0.0;
                combined_low_value  = 0.0;
                has_valid_poses_high = true;
                has_valid_poses_low  = true;
                break;
            }

            const pose_range& range = conn_it->second;
            auto [highValue, lowValue] = normalize_ranged_pose_value(pose_value, range);

            combined_high_value *= highValue;
            combined_low_value  *= lowValue;

            if (highValue > 0.0) has_valid_poses_high = true;
            if (lowValue  > 0.0) has_valid_poses_low  = true;

            // Early out: multiplication can't recover from zero
            if (combined_high_value == 0.0 && combined_low_value == 0.0)
                break;

            if (!ah_poses.next()) break;
        }

        if (!has_valid_poses_high) combined_high_value = 0.0;
        if (!has_valid_poses_low)  combined_low_value  = 0.0;

        h_out_high.setDouble(combined_high_value);
        h_out_low.setDouble(combined_low_value);

        h_out_low.setClean();
        h_out_high.setClean();
        h_out_compound.setClean();

        if (!ah_corrective_outputs.next()) break;
    }

    // Mark parent array clean to prevent per-element recompute
    data.setClean(MPlug(thisMObject(), a_corrective_outputs));
    data.setClean(plug);

    return status;
}

face_pose_driver::pose_range face_pose_driver::get_pose_range(const MPlug& pose_plug)
{
	MStatus status;
	pose_range range = {.min = 0.0, .max = 1.0 }; // Default fallback values

	// Find the source plug if this is connected
	MPlug source_plug;
	if (pose_plug.isConnected()) {
		MPlugArray connections;
		pose_plug.connectedTo(connections, true, false); // true=asDst, false=asSrc
		if (connections.length() > 0) {
			source_plug = connections[0];
		}
	}
	else {
		// Not connected, use the current plug
		source_plug = pose_plug;
	}

	// Try to get min/max values from the attribute
	if (!source_plug.isNull()) {
		const MFnAttribute fn_attr(source_plug.attribute(), &status);
		if (!status) {
			return range;
		}
		const MFnNumericAttribute num_attr(fn_attr.object(), &status);
		if (!status) {
			return range;
		}

		// Check if min/max is available
		if (num_attr.hasMin()) {
			num_attr.getMin(range.min);
		}
		if (num_attr.hasMax()) {
			num_attr.getMax(range.max);
		}
	}

	// Make sure min != max to avoid division by zero
	if (range.min == range.max) {
		// TODO log warning
		return {.min = 0.0, .max = 1.0 };
	}

	return range;
}

double face_pose_driver::normalize_pose_value(const double value, const pose_range& range)
{
	if (range.max == range.min)
		return 0.0;

	const auto normalized = (value - range.min) / (range.max - range.min);

	// Clamp to 0-1 range
	return std::max(0.0, std::min(1.0, normalized));
}

std::pair<double, double> face_pose_driver::normalize_ranged_pose_value(const double value, const pose_range& range)
{
	double high_value = 0.0;
	double low_value = 0.0;
    
	// Determine if the pose range spans negative to positive values
	if (const bool has_negative_range = range.min < 0 && range.max > 0) {
		// Handle poses with both negative and positive ranges
		if (value > 0) {
			// Normalize positive values from 0 to max
			high_value = value / range.max;
			high_value = std::max(0.0, std::min(1.0, high_value));
		} 
		else if (value < 0) {
			// Normalize negative values from min to 0
			low_value = value / range.min;  // Will give positive result since both are negative
			low_value = std::max(0.0, std::min(1.0, low_value));
		}
	} else {
		// For purely positive or purely negative ranges, use the old normalization method
		double normalized = (value - range.min) / (range.max - range.min);
		normalized = std::max(0.0, std::min(1.0, normalized));
        
		// For purely positive ranges, only use highValue
		// For purely negative ranges, only use lowValue
		if (range.min >= 0) {
			high_value = normalized;
		} else {
			low_value = normalized;
		}
	}
    
	return {high_value, low_value};
}

void face_pose_driver::create_numeric_attributes()
{
	MFnNumericAttribute n_attr;

	a_linear_subposes = n_attr.create("linearSubposes", "linearSubposes", MFnNumericData::kDouble);
	n_attr.setWritable(true);
	n_attr.setKeyable(true);
	n_attr.setArray(true);

	a_pose_weight = n_attr.create("poseWeight", "poseWeight", MFnNumericData::kDouble);
	n_attr.setWritable(true);
	n_attr.setKeyable(true);

	a_linear_outputs = n_attr.create("linearOutputs", "linearOut", MFnNumericData::kDouble);
	n_attr.setWritable(false);
	n_attr.setStorable(true);
	n_attr.setArray(true);
	//nAttr.setUsesArrayDataBuilder(true);
}

void face_pose_driver::create_unit_attributes()
{
	MFnUnitAttribute u_attr;

	a_angular_subposes = u_attr.create("angularSubposes", "angularSubposes", MFnUnitAttribute::kAngle);
	u_attr.setWritable(true);
	u_attr.setKeyable(true);
	u_attr.setArray(true);

	a_angular_outputs = u_attr.create("angularOutputs", "angularOutputs", MFnUnitAttribute::kAngle);
	u_attr.setWritable(false);
	u_attr.setStorable(true);
	u_attr.setArray(true);
	//uAttr.setUsesArrayDataBuilder(true);
}

void face_pose_driver::create_compound_attributes()
{
	MFnCompoundAttribute c_attr;

	a_poses = c_attr.create("poses", "poses");
	c_attr.setArray(true);
	c_attr.addChild(a_pose_weight);
	c_attr.addChild(a_linear_subposes);
	c_attr.addChild(a_angular_subposes);
}

void face_pose_driver::create_enum_attributes()
{
	MFnEnumAttribute e_attr;

	a_blend_mode = e_attr.create("blendMode", "blendMode", 2); // default to RestAdditiveLinear
	e_attr.addField("LegacyNormalizedWeighted", 0);
	e_attr.addField("RestNormalizedWeighted", 1);
	e_attr.addField("RestAdditiveLinear", 2);
	e_attr.setKeyable(true);
	e_attr.setStorable(true);
	e_attr.setWritable(true);
}

void face_pose_driver::create_corrective_attributes()
{
	MFnNumericAttribute n_attr;
	MFnCompoundAttribute c_attr;

	// Create individual pose inputs for correctives
	a_corrective_input_poses = n_attr.create("correctiveInputPose", "correctiveInputPose", MFnNumericData::kDouble);
	n_attr.setWritable(true);
	n_attr.setKeyable(true);
	n_attr.setArray(true);

	// Create the compound attribute for a set of poses that control a corrective
	a_corrective_inputs = c_attr.create("correctiveInputs", "correctiveInputs");
	c_attr.setArray(true);
	c_attr.addChild(a_corrective_input_poses);

	a_corrective_output_high = n_attr.create("correctiveOutputHigh", "correctiveOutputHigh", MFnNumericData::kDouble);
	n_attr.setWritable(false);
	n_attr.setStorable(true);
	n_attr.setMin(0.0);
	n_attr.setMax(1.0);
	
	a_corrective_output_low = n_attr.create("correctiveOutputLow", "correctiveOutLow", MFnNumericData::kDouble);
	n_attr.setWritable(false);
	n_attr.setStorable(true);
	n_attr.setMin(0.0);
	n_attr.setMax(1.0);

	// Create the compound output attribute
	a_corrective_outputs = c_attr.create("correctiveOutputs", "correctiveOutputs");
	c_attr.setArray(true);
	c_attr.addChild(a_corrective_output_high);
	c_attr.addChild(a_corrective_output_low);
	// cAttr.setWritable(false);
	// cAttr.setStorable(true);
}

void face_pose_driver::add_attributes()
{
	// Main attributes
	
	addAttribute(a_pose_weight);

	addAttribute(a_linear_subposes);
	addAttribute(a_angular_subposes);

	addAttribute(a_poses);

	addAttribute(a_linear_outputs);
	addAttribute(a_angular_outputs);

	// Blend modes
	
	addAttribute(a_blend_mode);
	
	// Corrective blendshape attributes
	
	addAttribute(a_corrective_input_poses);
	addAttribute(a_corrective_inputs);
	addAttribute(a_corrective_outputs);
}

void face_pose_driver::set_attribute_affects()
{
 	// attributeAffects(a_poses, a_linear_outputs);
	// attributeAffects(a_poses, a_angular_outputs);
	
	// attributeAffects(a_pose_weight, a_linear_outputs);
	// attributeAffects(a_pose_weight, a_angular_outputs);
	
	attributeAffects(a_blend_mode, a_linear_outputs);
	attributeAffects(a_blend_mode, a_angular_outputs);
	
	// attributeAffects(a_corrective_inputs, a_corrective_outputs);
	// attributeAffects(a_corrective_input_poses, a_corrective_outputs);
}
