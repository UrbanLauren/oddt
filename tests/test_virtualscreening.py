import os

from nose.tools import assert_in, assert_equal
from sklearn.utils.testing import (assert_array_equal,
                                   assert_array_almost_equal,
                                   assert_raises)

import oddt
from oddt.spatial import rmsd
from oddt.virtualscreening import virtualscreening

test_data_dir = os.path.dirname(os.path.abspath(__file__))


def test_vs_scoring_vina():
    """VS scoring (Vina) tests"""
    vs = virtualscreening(n_cpu=1)
    vs.load_ligands('sdf', os.path.join(test_data_dir, 'data/dude/xiap/crystal_ligand.sdf'))
    vs.score(function='autodock_vina',
             protein=os.path.join(test_data_dir, 'data/dude/xiap/receptor_rdkit.pdb'))
    mols = list(vs.fetch())
    assert_equal(len(mols), 1)
    mol_data = mols[0].data
    assert_in('vina_affinity', mol_data)
    assert_in('vina_gauss1', mol_data)
    assert_in('vina_gauss2', mol_data)
    assert_in('vina_hydrogen', mol_data)
    assert_in('vina_hydrophobic', mol_data)
    assert_in('vina_repulsion', mol_data)
    assert_equal(mol_data['vina_affinity'], '-3.57594')
    assert_equal(mol_data['vina_gauss1'], '63.01213')
    assert_equal(mol_data['vina_gauss2'], '999.07625')
    assert_equal(mol_data['vina_hydrogen'], '0.0')
    assert_equal(mol_data['vina_hydrophobic'], '26.12648')
    assert_equal(mol_data['vina_repulsion'], '3.63178')


def test_vs_docking():
    """VS docking (Vina) tests"""
    vs = virtualscreening(n_cpu=1)
    vs.load_ligands('sdf', os.path.join(test_data_dir, 'data/dude/xiap/crystal_ligand.sdf'))
    vs.dock(engine='autodock_vina',
            protein=os.path.join(test_data_dir, 'data/dude/xiap/receptor_rdkit.pdb'),
            auto_ligand=os.path.join(test_data_dir, 'data/dude/xiap/crystal_ligand.sdf'),
            exhaustiveness=1,
            energy_range=5,
            num_modes=9,
            size=(20, 20, 20),
            seed=0)
    mols = list(vs.fetch())
    assert_equal(len(mols), 9)
    mol_data = mols[0].data
    assert_in('vina_affinity', mol_data)
    assert_in('vina_rmsd_lb', mol_data)
    assert_in('vina_rmsd_ub', mol_data)
    if oddt.toolkit.backend == 'ob' and oddt.toolkit.__version__ < '2.4.0':
        vina_scores = [-6.3, -6.0, -6.0, -5.9, -5.9, -5.8, -5.2, -4.2, -3.9]
    else:
        vina_scores = [-6.3, -6.0, -5.1, -3.9, -3.5, -3.5, -3.5, -3.3, -2.5]
    assert_array_equal([float(m.data['vina_affinity']) for m in mols], vina_scores)

    # verify the SMILES of molecules
    ref_mol = next(
        oddt.toolkit.readfile('sdf',
                              os.path.join(test_data_dir,
                                           'data/dude/xiap/crystal_ligand.sdf')))

    if oddt.toolkit.backend == 'ob' and oddt.toolkit.__version__ < '2.4.0':
        # OB 2.3.2 will fail the following, since Hs are removed, etc.
        pass
    else:
        vina_rmsd = [8.247347, 5.316951, 7.964107, 7.445350, 8.127984, 7.465065,
                     8.486132, 7.943340, 7.762220]
        assert_array_equal([mol.smiles for mol in mols],
                           [ref_mol.smiles] * len(mols))

        assert_array_almost_equal([rmsd(ref_mol, mol, method='min_symmetry')
                                   for mol in mols], vina_rmsd)


if oddt.toolkit.backend == 'ob':  # RDKit rewrite needed
    def test_vs_filtering():
        """VS preset filtering tests"""
        vs = virtualscreening(n_cpu=-1)

        vs.load_ligands('sdf', os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))
        vs.apply_filter('ro5', soft_fail=1)
        assert_equal(len(list(vs.fetch())), 49)

        vs.load_ligands('sdf', os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))
        vs.apply_filter('ro3', soft_fail=2)
        assert_equal(len(list(vs.fetch())), 9)


def test_vs_pains():
    """VS PAINS filter tests"""
    vs = virtualscreening(n_cpu=-1)
    # TODO: add some failing molecules
    vs.load_ligands('sdf', os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))
    vs.apply_filter('pains', soft_fail=0)
    assert_equal(len(list(vs.fetch())), 100)


def test_vs_similarity():
    """VS similarity filter (USRs, IFPs) tests"""
    ref_mol = next(oddt.toolkit.readfile(
        'sdf', os.path.join(test_data_dir, 'data/dude/xiap/crystal_ligand.sdf')))
    receptor = next(oddt.toolkit.readfile(
        'pdb', os.path.join(test_data_dir, 'data/dude/xiap/receptor_rdkit.pdb')))
    lig_dir = os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf')

    # following toolkit differences is due to different Hs treatment
    vs = virtualscreening(n_cpu=-1)
    vs.load_ligands('sdf', lig_dir)
    vs.similarity('usr', cutoff=0.4, query=ref_mol)
    if oddt.toolkit.backend == 'ob':
        assert_equal(len(list(vs.fetch())), 11)
    else:
        assert_equal(len(list(vs.fetch())), 6)

    vs = virtualscreening(n_cpu=-1)
    vs.load_ligands('sdf', lig_dir)
    vs.similarity('usr_cat', cutoff=0.3, query=ref_mol)
    if oddt.toolkit.backend == 'ob':
        assert_equal(len(list(vs.fetch())), 16)
    else:
        assert_equal(len(list(vs.fetch())), 11)

    vs = virtualscreening(n_cpu=-1)
    vs.load_ligands('sdf', lig_dir)
    vs.similarity('electroshape', cutoff=0.45, query=ref_mol)
    if oddt.toolkit.backend == 'ob':
        assert_equal(len(list(vs.fetch())), 55)
    else:
        assert_equal(len(list(vs.fetch())), 89)

    vs = virtualscreening(n_cpu=-1)
    vs.load_ligands('sdf', lig_dir)
    vs.similarity('ifp', cutoff=0.95, query=ref_mol, protein=receptor)
    if oddt.toolkit.backend == 'ob':
        assert_equal(len(list(vs.fetch())), 3)
    else:
        assert_equal(len(list(vs.fetch())), 6)

    vs = virtualscreening(n_cpu=-1)
    vs.load_ligands('sdf', lig_dir)
    vs.similarity('sifp', cutoff=0.9, query=ref_mol, protein=receptor)
    if oddt.toolkit.backend == 'ob':
        assert_equal(len(list(vs.fetch())), 14)
    else:
        assert_equal(len(list(vs.fetch())), 21)

    # test wrong method error
    assert_raises(ValueError, vs.similarity, 'sift', query=ref_mol)
