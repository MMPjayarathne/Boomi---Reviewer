"""Smoke tests for the rule engine against the sample XML."""
from pathlib import Path
import asyncio
from backend.parser.boomi_parser import parse_xml
from backend.rules.registry import run_all_rules

SAMPLE_XML = Path(__file__).parent.parent / "samples" / "example_process.xml"


def test_rules_find_issues():
    xml_bytes = SAMPLE_XML.read_bytes()
    process = parse_xml(xml_bytes)
    findings = asyncio.run(run_all_rules(process))

    rule_ids = {f.rule_id for f in findings}
    print(f"\nFindings: {[(f.rule_id, f.severity.value) for f in findings]}")

    # These issues are present in the sample XML
    assert "HC001" in rule_ids, "Should detect hardcoded password"
    assert "HC003" in rule_ids, "Should detect hardcoded URL"
    assert "DEAD001" in rule_ids, "Should detect unreachable shape"
    assert "DEAD002" in rule_ids, "Should detect dead-end shape"
    assert "DUP001" in rule_ids, "Should detect duplicate connector"
    assert "EH001" in rule_ids, "Should detect missing error handling"


def test_no_false_positives_on_clean_xml():
    """A minimal valid process should produce no CRITICAL findings."""
    clean_xml = b"""<?xml version="1.0"?>
        <bns:Process xmlns:bns="http://www.boomi.com/connector/automation"
          processName="CleanProcess" processId="p1">
          <bns:Shapes>
            <bns:Shape id="s1" shapeType="Start" label="Start"/>
            <bns:Shape id="s_tc" shapeType="TryCatch" label="Errors"/>
            <bns:Shape id="s2" shapeType="Stop" label="Stop"/>
          </bns:Shapes>
          <bns:Connections>
            <bns:Connection id="c1" fromShape="s1" toShape="s_tc" label=""/>
            <bns:Connection id="c2" fromShape="s_tc" toShape="s2" label=""/>
          </bns:Connections>
        </bns:Process>"""
    process = parse_xml(clean_xml)
    findings = asyncio.run(run_all_rules(process))
    critical = [f for f in findings if f.severity.value == "CRITICAL"]
    assert not critical, f"Unexpected CRITICAL findings: {critical}"


def test_platform_export_start_not_flagged_dead002():
    """Dragpoint edges must be parsed so Start is not a false dead-end."""
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Component xmlns:bns="http://api.platform.boomi.com/" name="API Flow" componentId="c1" type="process">
  <bns:object>
    <process>
      <shapes>
        <shape name="shape1" shapetype="start" userlabel="">
          <dragpoints><dragpoint name="d1" toShape="shape2"/></dragpoints>
        </shape>
        <shape name="shape2" shapetype="stop">
          <dragpoints/>
        </shape>
      </shapes>
    </process>
  </bns:object>
</Component>"""
    process = parse_xml(xml)
    assert process.process_name == "API Flow"
    findings = asyncio.run(run_all_rules(process))
    dead002_on_start = [f for f in findings if f.rule_id == "DEAD002" and f.shape_id == "shape1"]
    assert not dead002_on_start, dead002_on_start


def test_flowcontrol_chunkstyle_not_perf004():
    """Flow Control with chunk/thread/forEach document modes is not PERF004 (see Boomi Flow Control docs)."""
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Component xmlns:bns="http://api.platform.boomi.com/" name="T" componentId="c" type="process">
  <bns:object>
    <process>
      <shapes>
        <shape name="shape8" shapetype="flowcontrol" userlabel="">
          <configuration>
            <flowcontrol chunkStyle="threadOnly" chunks="0" forEachCount="1"/>
          </configuration>
          <dragpoints><dragpoint name="d1" toShape="shape9"/></dragpoints>
        </shape>
        <shape name="shape9" shapetype="stop"><dragpoints/></shape>
      </shapes>
    </process>
  </bns:object>
</Component>"""
    process = parse_xml(xml)
    findings = asyncio.run(run_all_rules(process))
    perf004_shape8 = [f for f in findings if f.rule_id == "PERF004" and f.shape_id == "shape8"]
    assert not perf004_shape8, perf004_shape8
