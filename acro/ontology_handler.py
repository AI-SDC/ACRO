"""Ontology_handler.py.

@author Jim Smith March 2026
Functionality to load semantic information from statbarnssdc ontology
and save in dicts/json to drive acro behaviour.
"""

import json

# import acro
import logging
from typing import Any

import rdflib

logger = logging.getLogger(__name__)

PREFIX = "https://www.w3id.org/statbarnsdc#"
SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
SUBCLASSTYPE = rdflib.term.URIRef(SUBCLASS)
SOMEVALUESFROM = "http://www.w3.org/2002/07/owl#someValuesFrom"
STATBARNSDC = "https://ai-sdc.github.io/statbarnsdc/statbarnsdc.ttl"


def is_uri(thing: Any) -> bool:
    """Test whether thing is an external defined uri."""
    return isinstance(thing, rdflib.term.URIRef)


def print_nested_dict(s: dict) -> None:
    """Pretty print nested dict. s is the nested dictionary to be printed."""
    for key, val in s.items():
        logger.warning("%s", key)
        for key2, val2 in val.items():
            logger.warning("   %s  :  %s", key2, val2)


def populate_useful_dicts(g: rdflib.Graph) -> tuple:
    """Create useful dicts to save time.

    Parameters
    ----------
    g : rdflib.Graph
        representation of the statbarnsdc ontology in RDF triples

    Returns
    -------
    tuple (dict,dict,dict) representing lookups for:
        definitions
       labels
       list of BNode immediate superclasses
       for each element of ontology
    """
    definitions: dict = {}
    pref_labels: dict = {}
    othersuperclasses: dict = {}

    for s, p, o in g:
        key = s.replace(PREFIX, "")
        oval = str(o)
        if str(p) == "http://www.w3.org/2004/02/skos/core#definition":
            definitions[key] = oval
        if str(p) == "http://www.w3.org/2004/02/skos/core#prefLabel":
            pref_labels[key] = oval
        if (
            str(p) == SUBCLASS
            and not oval.startswith("https://w3id.org")
            and not oval.startswith(PREFIX)
        ):
            if key in othersuperclasses:
                othersuperclasses[key].append(oval)
            else:
                othersuperclasses[key] = [oval]

    assert set(definitions.keys()) == set(pref_labels.keys())
    return definitions, pref_labels, othersuperclasses


def make_save_statbarns(
    g: rdflib.Graph, definitions: dict, pref_labels: dict, othersuperclasses: dict
) -> dict:
    """
    Create statbarn dicts/json from ontology.

    parse the rdf graph from the ontology
    create lookup dict of statbarns
    save to json file

    Returns
    -------
    nested dict one entry per statbarn
    Inner dicts contain for each statbarn
    - uri
    - string containing a definitions
    - prefix_label
    - list of risks associated the stat barn

        Parameter
    ---------
    g : rdflib.Graph
    representation of the statbarnsdc ontology in RDF triples
    definitions:dict,
    pref_labels:dict,
       lookup tables
    """
    statbarns: dict = {}
    for s, p, o in g:
        if str(p) == SUBCLASS and str(o) == PREFIX + "Statbarn":
            key = s.replace(PREFIX, "")
            statbarns[key] = {
                "uri": s,
                "risks": [],
                "definition": definitions[key],
                "prefix_label": pref_labels[key],
            }
            for superclass in othersuperclasses.get(key, []):
                for s1, p1, o1 in g:
                    if str(s1) == superclass and str(p1) == SOMEVALUESFROM:
                        statbarns[key]["risks"].append(str(o1))

    with open("statbarns.json", "w") as f:
        json.dump(statbarns, f, indent=4, sort_keys=True, ensure_ascii=False)
    return statbarns


def make_save_analyses(
    g: rdflib.Graph, definitions: dict, pref_labels: dict, statbarns: dict
) -> dict:
    """Create analysis dicts/json from ontology.

    parse the rdf graph from the ontology
    create lookup dict of analyses
    save to json file

    Parameters
    ----------
    g : rdflib.Graph
        representation of the statbarnsdc ontology in RDF triples
    definitions : dict
        lookup table of definitions from ontology
    pref_labels : dict
        lookup table of preferred labels from ontology
    statbarns : dict
        lookup table of statbarns

    Returns
    -------
    nested dict one entry per analysis
    Inner dicts contain for each analysis
    - statbarn it belongs to
    - uri
    - string containing a definitions
    - prefix_label
    """
    analyses: dict = {}

    for (
        s,
        p,
        o,
    ) in g:
        if str(p) == SUBCLASS and str(o).replace(PREFIX, "") in statbarns:
            key = str(s).replace(PREFIX, "")
            analyses[key] = {
                "name": key,
                "uri": s,
                "definition": definitions.get(key, ""),
                "prefix_label": pref_labels.get(key, ""),
                "statbarn": o.replace(PREFIX, ""),
            }

    with open("analyses.json", "w") as f:
        json.dump(analyses, f, indent=4, sort_keys=True, ensure_ascii=False)
    return analyses


def make_ismitigatedby(g: rdflib.Graph, risks: list) -> dict:
    """Create lookup of mitigations for risks dicts/json from ontology.

    parse the rdf graph from the ontology
    create lookup dict of mitigations for each risk
    save to json file

    Parameters
    ----------
    g : rdflib.Graph
        representation of the statbarnsdc ontology in RDF triples
    risks : list(str)
        list of risks to consider

    Returns
    -------
    dict, one key per risk, list of potential  mitigations
    """
    risklist = [
        subject.replace(PREFIX, "")
        for subject in g.subjects(
            predicate=rdflib.URIRef(SUBCLASS),
            object=rdflib.URIRef("https://w3id.org/dpv/owl#Risk"),
        )
    ]
    assert set(risks).issubset(risklist)

    # hard coded for now
    ismitigatedby: dict = {
        "ClassDisclosure": [PREFIX + "Noise", PREFIX + "Suppression"],
        "LowCount": [PREFIX + "Noise", PREFIX + "Rounding", PREFIX + "Suppression"],
        "LowDOF": [
            PREFIX + "Aggregation",
            PREFIX + "Noise",
            PREFIX + "OutlierRemoval",
            PREFIX + "Suppression",
        ],
        "AuxiliaryInformation": [],
        "ImplicitTables": [],
        "Dominance": [
            PREFIX + "Noise",
            PREFIX + "OutlierRemoval",
            PREFIX + "Rounding",
            PREFIX + "Suppression",
        ],
        "Differencing": [PREFIX + "Noise", PREFIX + "Suppression"],
    }
    assert set(ismitigatedby.keys()) == set(risks)
    return ismitigatedby


def make_ischeckedby(g: rdflib.Graph, risks: list) -> dict:
    """
    Create lookup of checks for risks dicts/json from ontology.

    parse the rdf graph from the ontology
    create lookup dict of checks for each risk
    save to json file

    Parameters
    ----------
    g : rdflib.Graph
        representation of the statbarnsdc ontology in RDF triples
    risks : list(str)
        list of risks to consider

    Returns
    -------
    dict, one key per risk, list of potential  checks to run
    """
    checks_in_graph = [
        subject.replace(PREFIX, "")
        for subject in g.subjects(
            SUBCLASSTYPE,
            rdflib.term.URIRef("https://w3id.org/dpv/risk/owl#RiskEvaluation"),
        )
    ]
    # hard-coded for now
    ischeckedby: dict = {
        "ClassDisclosure": ["RequiredZeroCheck", "PresenceOfZeroCheck"],
        "LowCount": ["MinimumThresholdCheck"],
        "LowDOF": ["MinimumDoFCheck"],
        "AuxiliaryInformation": ["StatbarnDataCheck"],
        "ImplicitTables": ["StatbarnDataCheck"],
        "Dominance": ["NKCheck", "PQCheck"],
        "Differencing": ["PresenceOfLinkedTableCheck"],
    }

    for check in ischeckedby.values():
        if not isinstance(check, str):
            for c in check:
                assert c in checks_in_graph, f"{check} not in {checks_in_graph}"
        else:  # pragma: no cover
            assert check in checks_in_graph, f"{check} not in {checks_in_graph}"

    assert set(ischeckedby.keys()) == set(risks)

    return ischeckedby


def make_save_risks(
    g: rdflib.Graph,
    definitions: dict,
    pref_labels: dict,
    ischeckedby: dict,
    ismitigatedby: dict,
) -> dict:
    """
    Create risks dicts/json from ontology.

    parse the rdf graph from the ontology
    create lookup dict of risks
    save to json file

    Parameters
    ----------
    g : rdflib.Graph
        representation of the statbarnsdc ontology in RDF triples
    definitions : dict
        lookup table of definitions from ontology
    pref_labels : dict
        lookup table of preferred labels from ontology
    ischeckedby : dict
        lookup table mapping risks to checks
    ismitigatedby : dict
        lookup table mapping risks to mitigations

    Returns
    -------
    nested dict one entry per risk
    Inner dicts contain for each risk
    - uri
    - string containing a definitions
    - prefix_label
    - list of checks that should be run
    - list of potential mitigations
    """
    risks: dict = {}
    for s, p, o in g:
        if str(p) == SUBCLASS and str(o) == "https://w3id.org/dpv/owl#Risk":
            risk = str(s).replace(PREFIX, "")
            risks[risk] = {
                "uri": s,
                "definition": definitions[risk],
                "prefix_label": pref_labels.get(risk, ""),
                "checks": ischeckedby[risk],
                "mitigations": ismitigatedby[risk],
            }

    with open("risks.json", "w") as f:
        json.dump(risks, f, indent=4, sort_keys=True, ensure_ascii=False)
    return risks


def main() -> None:  # pragma: no cover
    """Generate json files."""
    g = rdflib.Graph()
    g.parse(STATBARNSDC)

    definitions, pref_labels, othersuperclasses = populate_useful_dicts(g)

    statbarns = make_save_statbarns(g, definitions, pref_labels, othersuperclasses)
    print_nested_dict(statbarns)

    analyses = make_save_analyses(g, definitions, pref_labels, statbarns)
    print_nested_dict(analyses)

    risklist = [
        subject.replace(PREFIX, "")
        for subject in g.subjects(
            predicate=rdflib.URIRef(SUBCLASS),
            object=rdflib.URIRef("https://w3id.org/dpv/owl#Risk"),
        )
    ]
    logger.warning("risklist: %s", risklist)
    ischeckedby = make_ischeckedby(g, risklist)
    ismitigatedby = make_ismitigatedby(g, risklist)

    risks = make_save_risks(g, definitions, pref_labels, ischeckedby, ismitigatedby)

    print_nested_dict(risks)


if __name__ == "__main__":  # pragma: no cover
    main()
