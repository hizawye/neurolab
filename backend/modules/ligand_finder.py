from collections import Counter
from statistics import median

from . import chembl_client
from ..schemas import ActivityEvidence, LigandResult, ResolvedTarget

# Binding affinities only. EC50 and other functional readouts measure a
# different quantity, so pooling them into one ranking would compare
# occupancy against downstream response.
BINDING_ASSAY_TYPES = ("Ki", "Kd", "IC50")

# Activity rows pulled per requested ligand. A molecule usually carries
# several measurements, so the window has to exceed the ligand count for
# per-molecule aggregation to have anything to aggregate.
RECORDS_PER_LIGAND = 20
MAX_RECORDS = 400


class LigandFinder:
    """Ligands with measured activity against a specific ChEMBL target."""

    def find_for_target(
        self,
        target: ResolvedTarget,
        limit: int = 8,
    ) -> list[tuple[LigandResult, ActivityEvidence]]:
        window = min(limit * RECORDS_PER_LIGAND, MAX_RECORDS)
        activities = chembl_client.activities_for_target(
            target.chembl_id,
            BINDING_ASSAY_TYPES,
            window,
        )

        grouped: dict[str, list[dict]] = {}
        for activity in activities:
            molecule_id = activity.get("molecule_chembl_id")
            smiles = activity.get("canonical_smiles")
            pchembl = activity.get("pchembl_value")
            if not molecule_id or not smiles or pchembl is None:
                continue
            grouped.setdefault(molecule_id, []).append(activity)

        candidates = [
            self._aggregate(molecule_id, records)
            for molecule_id, records in grouped.items()
        ]
        candidates.sort(key=lambda pair: pair[1].pchembl_value, reverse=True)
        return candidates[:limit]

    def _aggregate(
        self,
        molecule_id: str,
        records: list[dict],
    ) -> tuple[LigandResult, ActivityEvidence]:
        """Collapse repeat measurements of one molecule into a single value.

        Median rather than max: the same compound is often assayed many times
        across labs, and taking the best number would rank on the most
        favourable outlier instead of the consensus.
        """
        values = [float(record["pchembl_value"]) for record in records]
        assay_types = Counter(record.get("standard_type") or "unknown" for record in records)

        # Research compounds often have no registered name; fall back to the
        # accession so every row stays identifiable in the UI.
        ligand = LigandResult(
            chembl_id=molecule_id,
            name=records[0].get("molecule_pref_name") or molecule_id,
            smiles=records[0]["canonical_smiles"],
            source_url=f"https://www.ebi.ac.uk/chembl/compound_report_card/{molecule_id}/",
        )
        evidence = ActivityEvidence(
            pchembl_value=round(median(values), 2),
            standard_type=assay_types.most_common(1)[0][0],
            measurement_count=len(values),
        )
        return ligand, evidence
