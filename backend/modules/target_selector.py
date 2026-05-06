from cachetools import cached, TTLCache
import requests

from ..schemas import TargetResult

cache = TTLCache(maxsize=100, ttl=3600)


class TargetSelector:
    def __init__(self):
        self.search_url = "https://search.rcsb.org/rcsbsearch/v2/query"
        self.timeout_seconds = 12

    @cached(cache)
    def _fetch_from_rcsb(self, query_term: str, limit: int):
        search_query = {
            "query": {
                "type": "group",
                "logical_operator": "or",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_words",
                            "value": query_term,
                        },
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct_keywords.pdbx_keywords",
                            "operator": "contains_words",
                            "value": query_term,
                        },
                    },
                ],
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": 0, "rows": limit},
                "results_content_type": ["experimental"],
            },
        }

        response = requests.post(self.search_url, json=search_query, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def find_targets(self, condition_or_disease: str, limit: int = 10) -> list[TargetResult]:
        results = self._fetch_from_rcsb(condition_or_disease.strip(), limit)
        target_ids = [item["identifier"] for item in results.get("result_set", []) if item.get("identifier")]

        return [
            TargetResult(
                rcsb_id=target_id,
                source_url=f"https://www.rcsb.org/structure/{target_id}",
            )
            for target_id in target_ids[:limit]
        ]
