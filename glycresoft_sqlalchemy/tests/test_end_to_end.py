import os
import logging
try:
    logging.basicConfig(level=logging.DEBUG, filemode='w',
                        format="%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
                        datefmt="%H:%M:%S")
except:
    pass

from glycresoft_sqlalchemy.search_space_builder import naive_glycopeptide_hypothesis
from glycresoft_sqlalchemy.search_space_builder import search_space_builder
from glycresoft_sqlalchemy.search_space_builder import make_decoys
from glycresoft_sqlalchemy.search_space_builder.glycan_builder import constrained_combinatorics
from glycresoft_sqlalchemy.matching.glycopeptide.pipeline import GlycopeptideFragmentMatchingPipeline


def test_main():
    db_file_name = "./datafiles/naive_glycopeptide-2.db"
    os.remove(db_file_name)

    rules_table = {
        "Hex": (3, 10),
        "HexNAc": (2, 10),
        "Fuc": (0, 5),
        "NeuAc": (0, 4)
    }

    constraints_list = [
        ["Fuc", "<", "HexNAc"],
        ["NeuAc",  "<", "HexNAc - 1"]
    ]

    job = constrained_combinatorics.ConstrainedCombinatoricsGlycanHypothesisBuilder(
        db_file_name, rules_table=rules_table, constraints_list=constraints_list)

    combn_glycan_hypothesis_id = job.start()

    constant_mods, variable_mods = (["Carbamidomethyl (C)"], ["Deamidated (N)", "Pyro-glu from Q (Q@N-term)"])
    enzyme = 'trypsin'

    ms1_data = r"./datafiles/sample_dir/AGP-MS1"
    ms2_data = r"./datafiles/sample_dir/AGP-MS2"

    job = naive_glycopeptide_hypothesis.NaiveGlycopeptideHypothesisBuilder(
        database_path=db_file_name,
        hypothesis_name="End-to-End Combinatorial",
        protein_file="./datafiles/proteins_agp_only.fasta",
        site_list_file=None,
        constant_modifications=constant_mods,
        variable_modifications=variable_mods,
        enzyme=enzyme,
        glycomics_path=db_file_name,
        glycomics_format='hypothesis',
        source_hypothesis_id=combn_glycan_hypothesis_id,
        # glycomics_path='./datafiles/human_n_glycans.txt',
        # glycomics_format='txt',
        maximum_glycosylation_sites=1,
        max_missed_cleavages=1,
        n_processes=6)
    glycopeptide_hypothesis_id = job.start()
    #glycopeptide_hypothesis_id = 2
    ec = os.system(
        ("glycresoft-database-search ms1 -n 6 -i %s %s %d "
         "-p db -g 2e-5 --skip-grouping") % (ms1_data, db_file_name, glycopeptide_hypothesis_id))

    assert ec == 0

    job = search_space_builder.BatchingTheoreticalSearchSpaceBuilder.from_hypothesis_sample_match(
        db_file_name, 1, 6)
    hypothesis_id = job.start()
    job = make_decoys.BatchingDecoySearchSpaceBuilder(
        db_file_name, hypothesis_ids=[hypothesis_id], n_processes=6)
    decoy_hypothesis_id = job.start()[0]
    # hypothesis_id = 3
    # decoy_hypothesis_id = 4

    job = GlycopeptideFragmentMatchingPipeline(
        db_file_name, ms2_data,
        target_hypothesis_id=hypothesis_id,
        decoy_hypothesis_id=decoy_hypothesis_id,
        sample_run_name="20140918_01.yaml",
        hypothesis_sample_match_name="End-to-End AGP @ 20140918_01",
        n_processes=6)
    job.start()

if __name__ == '__main__':
    test_main()
