import json
import math

def match_minutiae_templates(template_q_str: str, template_d_str: str, dist_threshold: float = 15.0, angle_threshold: float = 0.35) -> float:
    """
    Compares two minutiae templates and returns a similarity score from 0.0 to 100.0.
    Minutiae templates are JSON strings representing a list of dicts:
    [{"x": float, "y": float, "type": str, "angle": float}, ...]
    """
    if not template_q_str or not template_d_str:
        return 0.0
    
    try:
        q_points = json.loads(template_q_str)
        d_points = json.loads(template_d_str)
    except Exception:
        return 0.0

    if not isinstance(q_points, list) or not isinstance(d_points, list):
        return 0.0

    if not q_points or not d_points:
        return 0.0

    match_count = 0
    matched_d_indices = set()

    for q in q_points:
        qx = q.get('x')
        qy = q.get('y')
        qtype = q.get('type')
        qangle = q.get('angle', 0.0)

        if qx is None or qy is None:
            continue

        best_match_idx = None
        min_dist = float('inf')

        for idx, d in enumerate(d_points):
            if idx in matched_d_indices:
                continue

            dx = d.get('x')
            dy = d.get('y')
            dtype = d.get('type')
            dangle = d.get('angle', 0.0)

            if dx is None or dy is None:
                continue

            # Optional type matching: bifurcation vs ridge ending
            if qtype and dtype and qtype != dtype:
                continue

            # Calculate Euclidean distance
            dist = math.sqrt((qx - dx)**2 + (qy - dy)**2)
            if dist > dist_threshold:
                continue

            # Calculate angle difference (modulus 2*pi)
            angle_diff = abs(qangle - dangle) % (2 * math.pi)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff

            if angle_diff > angle_threshold:
                continue

            # Candidate match found
            if dist < min_dist:
                min_dist = dist
                best_match_idx = idx

        if best_match_idx is not None:
            matched_d_indices.add(best_match_idx)
            match_count += 1

    # Similarity score: Dice coefficient
    score = (2.0 * match_count) / (len(q_points) + len(d_points))
    return round(score * 100.0, 2)
