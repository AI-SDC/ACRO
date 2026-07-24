"""Tests for ontology handling."""

import logging
import os

import rdflib

from acro.ontology_handler import (
    PREFIX,
    is_uri,
    make_ischeckedby,
    make_ismitigatedby,
    make_save_analyses,
    make_save_risks,
    make_save_statbarns,
    populate_useful_dicts,
    print_nested_dict,
)


def _build_minimal_graph() -> rdflib.Graph:
    """Build a minimal RDF graph that satisfies ontology_handler expectations."""
    g = rdflib.Graph()
    p = rdflib.Namespace(PREFIX)
    skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    rdfs = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")
    dpv_owl = rdflib.Namespace("https://w3id.org/dpv/owl#")

    risk_uri = p.LowCount
    g.add((risk_uri, rdfs.subClassOf, dpv_owl.Risk))
    g.add((risk_uri, skos.definition, rdflib.Literal("Low count risk")))
    g.add((risk_uri, skos.prefLabel, rdflib.Literal("LowCount")))

    barn_uri = p.Frequencies
    g.add((barn_uri, rdfs.subClassOf, p.Statbarn))
    g.add((barn_uri, skos.definition, rdflib.Literal("Frequency statbarn")))
    g.add((barn_uri, skos.prefLabel, rdflib.Literal("Frequencies")))

    analysis_uri = p.FrequencyTable
    g.add((analysis_uri, rdfs.subClassOf, barn_uri))
    g.add((analysis_uri, skos.definition, rdflib.Literal("Frequency table analysis")))
    g.add((analysis_uri, skos.prefLabel, rdflib.Literal("FrequencyTable")))

    check_uri = p.MinimumThresholdCheck
    g.add(
        (
            check_uri,
            rdfs.subClassOf,
            rdflib.URIRef("https://w3id.org/dpv/risk/owl#RiskEvaluation"),
        )
    )
    g.add((check_uri, skos.definition, rdflib.Literal("Minimum threshold check def")))
    g.add((check_uri, skos.prefLabel, rdflib.Literal("MinimumThresholdCheck")))

    return g


def _add_full_risks_and_checks(g: rdflib.Graph) -> None:
    """Add all 7 risks and 8 checks required by make_ismitigatedby/make_ischeckedby."""
    rdfs = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")
    dpv_owl = rdflib.Namespace("https://w3id.org/dpv/owl#")
    skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    p = rdflib.Namespace(PREFIX)
    for r in [
        "ClassDisclosure",
        "LowCount",
        "LowDOF",
        "AuxiliaryInformation",
        "ImplicitTables",
        "Dominance",
        "Differencing",
    ]:
        uri = p[r]
        g.add((uri, rdfs.subClassOf, dpv_owl.Risk))
        g.add((uri, skos.definition, rdflib.Literal(f"{r} def")))
        g.add((uri, skos.prefLabel, rdflib.Literal(r)))
    for c in [
        "RequiredZeroCheck",
        "PresenceOfZeroCheck",
        "MinimumThresholdCheck",
        "MinimumDoFCheck",
        "StatbarnDataCheck",
        "NKCheck",
        "PQCheck",
        "PresenceOfLinkedTableCheck",
    ]:
        g.add(
            (
                p[c],
                rdfs.subClassOf,
                rdflib.URIRef("https://w3id.org/dpv/risk/owl#RiskEvaluation"),
            )
        )


FULL_RISKS = [
    "ClassDisclosure",
    "LowCount",
    "LowDOF",
    "AuxiliaryInformation",
    "ImplicitTables",
    "Dominance",
    "Differencing",
]


def test_is_uri_ref_is_uri():
    """URI references are recognized as URIs."""
    assert is_uri(rdflib.term.URIRef("http://example.org/foo")) is True


def test_is_uri_literal_is_not_uri():
    """Literal values are not treated as URIs."""
    assert is_uri(rdflib.Literal("hello")) is False


def test_is_uri_string_is_not_uri():
    """Plain strings are not treated as URIs."""
    assert is_uri("http://example.org") is False


def test_print_nested_dict_prints_without_error(caplog):
    """Nested dictionaries are logged without error."""
    d = {"key1": {"a": 1, "b": 2}, "key2": {"c": 3}}
    with caplog.at_level(logging.WARNING):
        print_nested_dict(d)
    assert "key1" in caplog.text
    assert "key2" in caplog.text


def test_populate_useful_dicts_returns_three_dicts():
    """The helper returns definitions, labels, and superclass mappings."""
    g = _build_minimal_graph()
    definitions, pref_labels, othersuperclasses = populate_useful_dicts(g)
    assert isinstance(definitions, dict)
    assert isinstance(pref_labels, dict)
    assert isinstance(othersuperclasses, dict)
    assert set(definitions.keys()) == set(pref_labels.keys())


def test_populate_useful_dicts_known_entries_present():
    """The expected ontology entries are present in the helper output."""
    g = _build_minimal_graph()
    definitions, pref_labels, _ = populate_useful_dicts(g)
    assert "LowCount" in definitions
    assert "Frequencies" in pref_labels


def test_make_save_statbarns_creates_json_and_returns_dict(tmp_path):
    """The statbarn export helper creates a JSON-compatible dictionary."""
    g = _build_minimal_graph()
    definitions, pref_labels, othersuperclasses = populate_useful_dicts(g)
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = make_save_statbarns(g, definitions, pref_labels, othersuperclasses)
    finally:
        os.chdir(orig_dir)
    assert isinstance(result, dict)
    assert "Frequencies" in result
    assert "uri" in result["Frequencies"]


def test_make_save_analyses_creates_analyses_dict(tmp_path):
    """Make_save_analyses creates expected analysis records."""
    g = _build_minimal_graph()
    definitions, pref_labels, othersuperclasses = populate_useful_dicts(g)
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        statbarns = make_save_statbarns(g, definitions, pref_labels, othersuperclasses)
        result = make_save_analyses(g, definitions, pref_labels, statbarns)
    finally:
        os.chdir(orig_dir)
    assert isinstance(result, dict)
    assert "FrequencyTable" in result
    assert result["FrequencyTable"]["statbarn"] == "Frequencies"


def test_make_ismitigatedby_returns_dict_with_all_risks():
    """All requested risks are mapped to mitigation entries."""
    g = _build_minimal_graph()
    _add_full_risks_and_checks(g)
    result = make_ismitigatedby(g, FULL_RISKS)
    assert set(result.keys()) == set(FULL_RISKS)
    assert isinstance(result["LowCount"], list)


def test_make_ischeckedby_returns_dict_with_all_risks():
    """All requested risks are mapped to check entries."""
    g = _build_minimal_graph()
    _add_full_risks_and_checks(g)
    result = make_ischeckedby(g, FULL_RISKS)
    assert set(result.keys()) == set(FULL_RISKS)


def test_make_save_risks_creates_risks_dict(tmp_path):
    """The risks export helper writes a dictionary containing the expected entries."""
    g = _build_minimal_graph()
    _add_full_risks_and_checks(g)
    definitions, pref_labels, _ = populate_useful_dicts(g)
    ischeckedby = make_ischeckedby(g, FULL_RISKS)
    ismitigatedby = make_ismitigatedby(g, FULL_RISKS)
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = make_save_risks(
            g, definitions, pref_labels, ischeckedby, ismitigatedby
        )
    finally:
        os.chdir(orig_dir)
    assert isinstance(result, dict)
    assert "LowCount" in result


def test_populate_useful_dicts_othersuperclasses_branch() -> None:
    """Populate_useful_dicts() appends to existing list when key already in othersuperclasses (lines 74-77)."""
    g = rdflib.Graph()
    subclass_ref = rdflib.URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    definition_ref = rdflib.URIRef("http://www.w3.org/2004/02/skos/core#definition")
    preflabel_ref = rdflib.URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")

    subject = rdflib.URIRef(PREFIX + "TestClass")
    g.add((subject, definition_ref, rdflib.Literal("a test class")))
    g.add((subject, preflabel_ref, rdflib.Literal("Test Class")))

    parent1 = rdflib.URIRef("http://example.com/parent1")
    parent2 = rdflib.URIRef("http://example.com/parent2")
    g.add((subject, subclass_ref, parent1))
    g.add((subject, subclass_ref, parent2))

    _, _, othersuperclasses = populate_useful_dicts(g)

    key = "TestClass"
    assert key in othersuperclasses
    # Both parents should be present
    assert len(othersuperclasses[key]) >= 2


def test_make_save_statbarns_with_somevaluesfrom_risks(tmp_path):
    """Statbarns include risks via someValuesFrom relationship with superclasses."""
    g = rdflib.Graph()
    p = rdflib.Namespace(PREFIX)
    skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    rdfs = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")
    dpv_owl = rdflib.Namespace("https://w3id.org/dpv/owl#")
    owl = rdflib.Namespace("http://www.w3.org/2002/07/owl#")

    # Add a risk
    risk_uri = p.TestRisk
    g.add((risk_uri, rdfs.subClassOf, dpv_owl.Risk))
    g.add((risk_uri, skos.definition, rdflib.Literal("Test risk definition")))
    g.add((risk_uri, skos.prefLabel, rdflib.Literal("TestRisk")))

    # Add a statbarn
    barn_uri = p.TestStatbarn
    g.add((barn_uri, rdfs.subClassOf, p.Statbarn))
    g.add((barn_uri, skos.definition, rdflib.Literal("Test statbarn")))
    g.add((barn_uri, skos.prefLabel, rdflib.Literal("TestStatbarn")))

    # Add a superclass as an external (non-PREFIX) URI
    # This will be captured in othersuperclasses
    superclass_uri = rdflib.URIRef("http://example.com/TestSuperclass")
    g.add((barn_uri, rdfs.subClassOf, superclass_uri))

    # Connect superclass to risk via owl:someValuesFrom
    g.add((superclass_uri, owl.someValuesFrom, risk_uri))

    definitions, pref_labels, othersuperclasses = populate_useful_dicts(g)
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = make_save_statbarns(g, definitions, pref_labels, othersuperclasses)
    finally:
        os.chdir(orig_dir)

    assert isinstance(result, dict)
    assert "TestStatbarn" in result
    # Verify that the risk was added via the someValuesFrom relationship
    assert "risks" in result["TestStatbarn"]
    assert str(risk_uri) in result["TestStatbarn"]["risks"]
