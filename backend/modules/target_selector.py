import requests
import json
import os
from cachetools import cached, TTLCache

# Cache for 1 hour (3600 seconds)
cache = TTLCache(maxsize=100, ttl=3600)

class TargetSelector:
    def __init__(self):
        self.RCSB_API_BASE = "https://data.rcsb.org/rest/v1/core/query"
        self.CACHE_DIR = "./data/target_cache"
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    @cached(cache)
    def _fetch_from_rcsb(self, query_term: str):
        search_query = {
            "query": {
                "type": "group",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "rcsb_entry_container_identifiers.rcsb_id",
                            "operator": "contains_word",
                            "value": query_term
                        }
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct_keywords.pdbx_keywords",
                            "operator": "contains_word",
                            "value": query_term
                        }
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_word",
                            "value": query_term
                        }
                    }
                ],
                "logical_operator": "or"
            },
            "return_type": "entry"
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(self.RCSB_API_BASE, headers=headers, data=json.dumps(search_query))
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching from RCSB PDB: {e}")
            return None

    def find_targets(self, condition_or_disease: str):
        # For simplicity, let's just use the condition/disease as the query term for now.
        # In a real scenario, you'd map conditions to specific protein names/keywords.
        print(f"Searching for targets related to: {condition_or_disease}")
        results = self._fetch_from_rcsb(condition_or_disease)
        
        if results and "result_set" in results:
            target_ids = [item["rcsb_id"] for item in results["result_set"]]
            # Cache the results locally
            cache_file = os.path.join(self.CACHE_DIR, f"{condition_or_disease.replace(" ", "_")}.json")
            with open(cache_file, 'w') as f:
                json.dump(target_ids, f, indent=2)
            print(f"Found {len(target_ids)} targets. Cached to {cache_file}")
            return target_ids
        return []

# Example Usage (for testing purposes)
if __name__ == "__main__":
    selector = TargetSelector()
    targets = selector.find_targets("diabetes")
    print(f"Targets for diabetes: {targets[:5]}...") # Print first 5 for brevity

    targets = selector.find_targets("cancer")
    print(f"Targets for cancer: {targets[:5]}...") # Print first 5 for brevity
