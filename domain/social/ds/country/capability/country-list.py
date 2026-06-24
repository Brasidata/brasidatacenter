
from typing import Any, Dict
from ontobdc.shared.domain.port.context import CliContextPort
from ontobdc.shared.adapter.ontology import get_ontology_by_prefix
from ontobdc.context.adapter.remote import RemoteDatasetCapability
from ontobdc.storage.domain.port.dataset import EntityQueryCapabilityVisitablePort
from ontobdc.shared.domain.resource.capability import CapabilityMetadata, QueryCapability

SCHEMA = get_ontology_by_prefix("schema")


class ListCountryCapability(QueryCapability, RemoteDatasetCapability, EntityQueryCapabilityVisitablePort):
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
        },
        supported_languages=["en"],
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

    def label(self, lang: str = "en") -> str:
        labels = {
            "en": "List Countries",
        }
        return labels.get(lang, labels["en"])

    def description(self, lang: str = "en") -> str:
        descriptions = {
            "en": "Reads the country dataset payload and returns a list of countries.",
        }
        return descriptions.get(lang, descriptions["en"])

    def execute(self, context: CliContextPort) -> Dict[str, Any]:
        """
        Execute the capability to list countries from the dataset payload.
        """
        for output_schema_key in self.METADATA.output_schema.get("properties").keys():
            if output_schema_key not in self.gifts:
                raise ValueError(f"Missing values for output schema key '{output_schema_key}'.")

        return self.gifts
