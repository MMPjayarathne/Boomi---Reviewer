"""Basic parser tests."""
from pathlib import Path
from backend.parser.boomi_parser import parse_xml

SAMPLE_XML = Path(__file__).parent.parent / "samples" / "example_process.xml"


def test_parse_sample():
    xml_bytes = SAMPLE_XML.read_bytes()
    process = parse_xml(xml_bytes)

    assert process.process_name == "test process 1"
    assert len(process.shapes) == 8
    assert len(process.connections) == 6
    assert process.start_shape_id == "shape-start"


def test_shapes_have_ids():
    xml_bytes = SAMPLE_XML.read_bytes()
    process = parse_xml(xml_bytes)
    for shape in process.shapes:
        assert shape.id, f"Shape missing id: {shape}"


def test_invalid_xml_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_xml(b"<not valid xml")


def test_parse_boomi_platform_component_export():
    """Boomi platform export: Component root, shape name/shapetype, edges via dragpoint."""
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Component xmlns:bns="http://api.platform.boomi.com/"
  name="Get Data from API" componentId="979eec6e-881d-4b22-b6c7-bb388b46950e" type="process">
  <bns:object>
    <process>
      <shapes>
        <shape name="shape1" shapetype="start" userlabel="">
          <configuration><noaction/></configuration>
          <dragpoints>
            <dragpoint name="shape1.dragpoint1" toShape="shape2" x="224.0" y="56.0"/>
          </dragpoints>
        </shape>
        <shape name="shape2" shapetype="documentproperties" userlabel="Set URL">
          <configuration/>
          <dragpoints>
            <dragpoint name="shape2.dragpoint1" toShape="shape3" x="416.0" y="56.0"/>
          </dragpoints>
        </shape>
        <shape name="shape3" shapetype="stop" x="1200.0" y="208.0">
          <configuration><stop continue="true"/></configuration>
          <dragpoints/>
        </shape>
      </shapes>
    </process>
  </bns:object>
</Component>"""
    p = parse_xml(xml)
    assert p.process_name == "Get Data from API"
    assert p.process_id == "979eec6e-881d-4b22-b6c7-bb388b46950e"
    assert len(p.shapes) == 3
    assert len(p.connections) == 2
    by_from = {c.from_shape: c.to_shape for c in p.connections}
    assert by_from["shape1"] == "shape2"
    assert by_from["shape2"] == "shape3"
    s1 = next(s for s in p.shapes if s.id == "shape1")
    assert s1.type.lower() == "start"
    assert p.start_shape_id == "shape1"
    s2 = next(s for s in p.shapes if s.id == "shape2")
    assert "Set URL" in (s2.label or "")
