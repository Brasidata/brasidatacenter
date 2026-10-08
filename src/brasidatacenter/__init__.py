from importlib.metadata import PackageNotFoundError, version

from .resources import ONTOLOGY_BASE_IRI, iter_ontology_files, ontology_path, ontology_path_for_iri, ontology_root

try:
    __version__ = version("brasidatacenter")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__all__ = [
    "__version__",
    "ontology_root",
    "ontology_path",
    "ontology_path_for_iri",
    "ONTOLOGY_BASE_IRI",
    "iter_ontology_files",
]
