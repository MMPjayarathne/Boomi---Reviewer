"""
Parse Boomi process XML into a BoomiProcess model.

Supported shapes:
  • Legacy process.xml (connector/automation): Process, Shape, Connection
  • Platform export (api.platform.boomi.com): Component, shape, dragpoint → edges
"""

from __future__ import annotations

import uuid
from lxml import etree
from .models import BoomiProcess, Shape, Connection

NS_BOOMI = "http://www.boomi.com/connector/automation"


def _ns(tag: str) -> str:
    return f"{{{NS_BOOMI}}}{tag}"


def _local_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _iter_elements(root: etree._Element, local_name: str):
    """All descendants whose local tag matches (case-insensitive)."""
    want = local_name.lower()
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if _local_tag(el.tag).lower() == want:
            yield el


def _ancestor_with_local_name(el: etree._Element, local: str) -> etree._Element | None:
    want = local.lower()
    p = el.getparent()
    while p is not None:
        if isinstance(p.tag, str) and _local_tag(p.tag).lower() == want:
            return p
        p = p.getparent()
    return None


def _get_attr(el: etree._Element, *names: str, default: str = "") -> str:
    """First matching attribute (exact). XML attribute names are case-sensitive."""
    for name in names:
        val = el.get(name) or el.get(_ns(name))
        if val is not None and val != "":
            return val
    return default


def _shape_identity(shape_el: etree._Element) -> str:
    """Legacy uses id; platform export uses name as the shape key."""
    return _get_attr(shape_el, "id", "shapeId", "name")


def _shape_type(shape_el: etree._Element) -> str:
    return _get_attr(shape_el, "shapeType", "shapetype", "type")


def _shape_label(shape_el: etree._Element) -> str:
    """Prefer user-facing labels; avoid using name= when it is the internal shape id."""
    return _get_attr(shape_el, "userlabel", "label")


def _attribs(el: etree._Element) -> dict:
    """Recursively collect all attributes in an element subtree."""
    result: dict = dict(el.attrib)
    for child in el:
        child_key = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        result[child_key] = {**dict(child.attrib), **_attribs(child)}
    return result


def _resolve_process_meta(root: etree._Element, proc_el: etree._Element) -> tuple[str, str]:
    """
    process_id and process_name from Component wrapper or inner process element.
    """
    process_id = _get_attr(proc_el, "processId", "id")
    process_name = _get_attr(proc_el, "processName", "name", "label")

    if _local_tag(root.tag).lower() == "component":
        process_id = process_id or _get_attr(root, "componentId", "componentid", "id")
        process_name = process_name or _get_attr(root, "name")

    return process_id, process_name


def _find_process_element(root: etree._Element) -> etree._Element:
    if _local_tag(root.tag).lower() == "process":
        return root
    for el in root.iter():
        if isinstance(el.tag, str) and _local_tag(el.tag).lower() == "process":
            return el
    return root


def parse_xml(xml_bytes: bytes) -> BoomiProcess:
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    proc_el = _find_process_element(root)
    process_id, process_name = _resolve_process_meta(root, proc_el)

    shapes: list[Shape] = []
    for shape_el in _iter_elements(root, "shape"):
        sid = _shape_identity(shape_el)
        if not sid:
            sid = f"shape_{uuid.uuid4().hex[:8]}"
        stype = _shape_type(shape_el)
        slabel = _shape_label(shape_el)
        props = _attribs(shape_el)
        shapes.append(Shape(id=sid, type=stype, label=slabel, properties=props))

    connections: list[Connection] = []
    seen_edges: set[tuple[str, str, str]] = set()

    # Legacy: explicit Connection elements
    for conn_el in _iter_elements(root, "connection"):
        cid = _get_attr(conn_el, "id", "connectionId") or str(uuid.uuid4())
        from_s = _get_attr(conn_el, "fromShape", "from", "source")
        to_s = _get_attr(conn_el, "toShape", "to", "target")
        if from_s and to_s:
            key = (from_s, to_s, cid)
            if key not in seen_edges:
                seen_edges.add(key)
                clabel = _get_attr(conn_el, "label", "name")
                connections.append(
                    Connection(id=cid, from_shape=from_s, to_shape=to_s, label=clabel)
                )

    # Platform / dragpoint wiring (parent shape → toShape)
    for drag_el in _iter_elements(root, "dragpoint"):
        to_s = _get_attr(drag_el, "toShape", "toshape")
        if not to_s:
            continue
        parent_shape = _ancestor_with_local_name(drag_el, "shape")
        if parent_shape is None:
            continue
        from_s = _shape_identity(parent_shape)
        if not from_s:
            continue
        cid = _get_attr(drag_el, "name", "id") or f"{from_s}->{to_s}"
        clabel = _get_attr(drag_el, "text", "label")
        key = (from_s, to_s, cid)
        if key not in seen_edges:
            seen_edges.add(key)
            connections.append(
                Connection(id=cid, from_shape=from_s, to_shape=to_s, label=clabel)
            )

    start_id = ""
    for s in shapes:
        t = (s.type or "").lower()
        if t in ("start", "startshape"):
            start_id = s.id
            break

    return BoomiProcess(
        process_id=process_id,
        process_name=process_name or "UnnamedProcess",
        shapes=shapes,
        connections=connections,
        start_shape_id=start_id,
    )
