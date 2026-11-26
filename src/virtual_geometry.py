"""Pure geometry for viewport virtualization (no Qt dependency)."""
from bisect import bisect_left, bisect_right


def offsets(heights):
    result = [0]
    for height in heights:
        result.append(result[-1] + max(1, int(height)))
    return result


def visible_range(edges, top, height, overscan=100):
    """Half-open indices of rows overlapping the viewport and its buffer."""
    n = len(edges) - 1
    if n <= 0 or height <= 0:
        return range(0)
    start = max(0, bisect_right(edges, max(0, top-overscan))-1)
    end = min(n, bisect_left(edges, top+height+overscan))
    return range(min(start,n), max(min(start,n),end))


def anchor_at(keys, edges, top):
    if not keys:
        return None, 0
    i = min(len(keys)-1, max(0, bisect_right(edges, top)-1))
    return keys[i], top-edges[i]


def restore_anchor(keys, edges, anchor, old_top, viewport_height):
    key, delta = anchor
    try:
        i = keys.index(key)
        top = edges[i]+min(max(0,delta),edges[i+1]-edges[i]-1)
    except ValueError:
        top = old_top
    return max(0,min(top,max(0,edges[-1]-viewport_height)))
