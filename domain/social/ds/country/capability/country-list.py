
from typing import Any, Dict, List, Optional
from ontobdc.shared.domain.port.context import CliContextPort
from ontobdc.context.adapter.loader import RemoteResourceLoader
from ontobdc.shared.adapter.ontology import get_ontology_by_prefix
from ontobdc.shared.domain.resource.capability import CapabilityMetadata, QueryCapability
from ontobdc.storage.domain.port.dataset import RemoteDatasetRepositoryPort, RemoteDatasetCapabilityPort
from ontobdc.context.domain.port.remote import LinksetDatapackageResourcePort, RemoteResourceLoaderPort

SCHEMA = get_ontology_by_prefix("schema")


class ListCountryCapability(QueryCapability, RemoteDatasetCapabilityPort):
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
                    "description": "A list of dictionaries containing 'name' and 'code' for each country.",
                },
            },
        },
    )

    def __init__(self, repo: RemoteDatasetRepositoryPort):
        super().__init__()
        self._remote_dataset_repo: RemoteDatasetRepositoryPort = repo

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

    def execute(self, context: CliContextPort) -> Dict[str, Any]:
        """
        Execute the capability to list countries from the dataset payload.
        """
        linkset: LinksetDatapackageResourcePort = self.remote_dataset_repo.linkset_datapackage
        output_schema_keys: List[str] = list(self.metadata.output_schema.get("properties", {}).keys())

        # Find the exact resource by name from output schema
        schema_resource: Optional[Dict[str, Any]] = None
        for schema_id in output_schema_keys:
            schema_resource = linkset.get_resource_by_name(schema_id)
            if schema_resource and schema_resource.get("schema"):
                break

        if not schema_resource:
            raise ValueError(f"No valid schema resource found with name '{output_schema_keys[0]}' in the dataset payload.")

        load_strategy: RemoteResourceLoaderPort = RemoteResourceLoader.make(schema_resource)
        data_list: List[Dict[str, Any]] = list(load_strategy.get_entity_instances(self.remote_dataset_repo, SCHEMA.Country).values())

        # Create full response with output schema structure
        response: Dict[str, Any] = {}
        output_key = output_schema_keys[0]
        response[output_key] = data_list

        return response

