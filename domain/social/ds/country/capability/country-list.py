
import os
import csv
from typing import Any, Dict, List
from ontobdc.shared.domain.port.context import CliContextPort
from ontobdc.shared.domain.resource.capability import CapabilityMetadata, QueryCapability
from ontobdc.storage.domain.port.dataset import RemoteDatasetRepositoryPort, RemoteDatasetCapabilityPort


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
        print(self.metadata.output_schema)
        # resource: RemoteResourcePort = self.remote_dataset_repo.get_resource()




        
        # Path to the CSV file relative to this script
        # This script is at: brasidatacenter/domain/social/ds/country/capability/country-list.py
        # CSV is at: brasidatacenter/domain/social/ds/country/payload/documents/country-identifier-iso3166-1-alpha-2-en.csv
        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # csv_path = os.path.join(
        #     current_dir, 
        #     "..",
        #     "payload",
        #     "documents",
        #     "country-identifier-iso3166-1-alpha-2-en.csv"
        # )

        countries: List[Dict[str, str]] = []
        
        # try:
        #     with open(csv_path, mode='r', encoding='utf-8') as f:
        #         reader = csv.DictReader(f)
        #         for row in reader:
        #             countries.append({
        #                 "name": row.get("Name", "").strip(),
        #                 "code": row.get("Code", "").strip()
        #             })
        # except FileNotFoundError:
        #     raise RuntimeError(f"Country payload file not found at {csv_path}")
        # except Exception as e:
        #     raise RuntimeError(f"Failed to read country list: {str(e)}")

        return {
            "org.ontobdc.domain.social.country.list": countries,
        }
