
from typing import Any, Dict, List
from ontobdc.shared.domain.port.context import CliContextPort
from ontobdc.shared.adapter.ontology import get_ontology_by_prefix
from ontobdc.context.adapter.remote import RemoteDatasetCapability
from ontobdc.shared.domain.resource.capability import CapabilityMetadata, QueryCapability
from ontobdc.storage.domain.port.dataset import RemoteDatasetRepositoryPort

SCHEMA = get_ontology_by_prefix("schema")


class ListCountryCapability(QueryCapability, RemoteDatasetCapability):
    """
    Capability to list countries from the dataset payload.
    """
    METADATA = CapabilityMetadata(
        id="org.ontobdc.domain.social.country.capability.query.list",
        version="0.1.0",
        name="List Countries",
        description="Reads the country dataset payload and returns a list of countries with their codes and names.",
        author=["http://kb.elias.eng.br/nid/elias.ttl#Elias"],
        tags={
            "en": ["social", "country", "list", "query"],
            "pt": ["social", "país", "lista", "consulta"],
        },
        supported_languages=["en", "pt"],
        input_schema={
            "type": "object",
            "properties": {},
        },
        output_schema={
            "type": "object",
            "properties": {
                "org.ontobdc.domain.social.country.list": {
                    "type": "array",
                    "entity": SCHEMA.Country,
                    "description": "A list of dictionaries containing 'name' and 'code' for each country.",
                },
            },
        },
    )

    def __init__(self):
        self._gifts: Dict[str, List[Dict[str, Any]]] = {}
        self._remote_dataset_repo: RemoteDatasetRepositoryPort = None

    @property
    def remote_dataset_repo(self) -> RemoteDatasetRepositoryPort:
        return self._remote_dataset_repo

    def label(self, lang: str = "en") -> str:
        labels = {
            "en": "List Countries",
            "pt": "Listar Países",
        }
        return labels.get(lang, labels["en"])

    def description(self, lang: str = "en") -> str:
        descriptions = {
            "en": "Reads the country dataset payload and returns a list of countries.",
            "pt": "Lê o payload do dataset de países e retorna uma lista de países.",
        }
        return descriptions.get(lang, descriptions["en"])

    def accept_gift(self, name: str, data: List[Dict[str, Any]]):
        self._gifts[name] = data

    def execute(self, context: CliContextPort) -> Dict[str, Any]:
        """
        Execute the capability to list countries from the dataset payload.
        """
        for output_schema_key in self.METADATA.output_schema.get("properties").keys():
            if output_schema_key not in self._gifts:
                raise ValueError(f"Missing values for output schema key '{output_schema_key}'.")

        return self._gifts
