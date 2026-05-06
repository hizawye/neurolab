from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors

from ..schemas import DescriptorSet


def calculate_descriptors(smiles: str) -> DescriptorSet | None:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return None

    return DescriptorSet(
        molecular_weight=round(float(Descriptors.MolWt(molecule)), 2),
        logp=round(float(Crippen.MolLogP(molecule)), 2),
        tpsa=round(float(rdMolDescriptors.CalcTPSA(molecule)), 2),
        h_bond_donors=int(Lipinski.NumHDonors(molecule)),
        h_bond_acceptors=int(Lipinski.NumHAcceptors(molecule)),
    )
