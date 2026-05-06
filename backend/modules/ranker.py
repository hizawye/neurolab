from ..schemas import DescriptorSet


def score_descriptors(descriptors: DescriptorSet) -> tuple[float, list[str]]:
    score = 100.0
    notes: list[str] = []

    if descriptors.molecular_weight > 450:
        score -= 20
        notes.append("High molecular weight")
    elif descriptors.molecular_weight < 150:
        score -= 10
        notes.append("Low molecular weight")

    if descriptors.logp < 1:
        score -= 15
        notes.append("Low LogP may reduce membrane permeability")
    elif descriptors.logp > 5:
        score -= 20
        notes.append("High LogP may increase liability")

    if descriptors.tpsa > 90:
        score -= 25
        notes.append("TPSA above common BBB-friendly range")
    elif descriptors.tpsa <= 70:
        score += 8
        notes.append("TPSA is favorable for BBB-oriented screening")

    if descriptors.h_bond_donors > 3:
        score -= 10
        notes.append("Many hydrogen bond donors")
    if descriptors.h_bond_acceptors > 8:
        score -= 10
        notes.append("Many hydrogen bond acceptors")

    return round(max(score, 0.0), 2), notes
