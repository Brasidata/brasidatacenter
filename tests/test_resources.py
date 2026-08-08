from brasidatacenter import iter_ontology_files, ontology_path, ontology_root


def test_ontology_root_exists():
    assert ontology_root().is_dir()


def test_known_ontology_is_available():
    resource = ontology_path("social", "entity", "ns.ttl")
    assert resource.is_file()


def test_iter_ontology_files_finds_ttl():
    files = list(iter_ontology_files())
    assert files
    assert any(item.name == "ns.ttl" for item in files)
