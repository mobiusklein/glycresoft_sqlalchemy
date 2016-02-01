import os
import logging
try:
    logging.basicConfig(level=logging.DEBUG, filemode='w',
                        format="%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
                        datefmt="%H:%M:%S")
except:
    pass

from glycresoft_sqlalchemy.search_space_builder import integrated_omics
from glycresoft_sqlalchemy.search_space_builder.glycan_builder import constrained_combinatorics
from glycresoft_sqlalchemy.search_space_builder import exact_search_space_builder, make_decoys
from glycresoft_sqlalchemy.matching.glycopeptide.pipeline import GlycopeptideFragmentMatchingPipeline
from glycresoft_sqlalchemy.scoring import pair_counting


def test_main():
    db_file_name = "./datafiles/integrated_omics_simple.db"
    # os.remove(db_file_name)

    # rules_table = {
    #     "Hex": (3, 8),
    #     "HexNAc": (2, 8),
    #     "Fuc": (0, 5),
    #     "NeuAc": (0, 4)
    # }

    # job = constrained_combinatorics.ConstrainedCombinatoricsGlycanHypothesisBuilder(
    #     db_file_name, rules_table=rules_table, constraints_list=[])
    # job.start()

    # n_processes = 6

    # complex_proteome = [
    #     "P02763|A1AG1_HUMAN",
    #     "P19652|A1AG2_HUMAN",
    #     "P00738|HPT_HUMAN"
    # ]

    # simple_proteome = [
    #     "P02763|A1AG1_HUMAN", "P19652|A1AG2_HUMAN"
    # ]

    # job = integrated_omics.IntegratedOmicsMS1SearchSpaceBuilder(
    #     db_file_name,
    #     protein_ids=simple_proteome,
    #     mzid_path="datafiles/AGP_Proteomics2.mzid",
    #     # glycomics_path='./datafiles/human_n_glycans.txt',
    #     # glycomics_format='txt',
    #     glycomics_path=db_file_name,
    #     glycomics_format='hypothesis',
    #     source_hypothesis_id=1,
    #     maximum_glycosylation_sites=1,
    #     include_all_baseline=True,
    #     n_processes=n_processes)
    # hypothesis_id = job.start()

    # # hypothesis_id = 2

    # ec = os.system(
    #     ("glycresoft-database-search ms1 -n 6 -i datafiles/20140918_01_isos.db -p db "
    #      "-g 2e-5 --skip-grouping {db_file_name} {hypothesis_id}").format(
    #         db_file_name=db_file_name, hypothesis_id=hypothesis_id))
    # assert ec == 0

    # hsm_id = 3

    # job = exact_search_space_builder.BatchingExactSearchSpaceBuilder.from_hypothesis_sample_match(
    #     db_file_name, 1, 6)
    # hypothesis_id = job.start()
    # job = make_decoys.BatchingDecoySearchSpaceBuilder(db_file_name, hypothesis_ids=[hypothesis_id], n_processes=6)
    # decoy_hypothesis_id = job.start()[0]

    hypothesis_id = 3
    decoy_hypothesis_id = 4

    job = GlycopeptideFragmentMatchingPipeline(
        db_file_name, "datafiles/20140918_01.db",
        target_hypothesis_id=hypothesis_id,
        decoy_hypothesis_id=decoy_hypothesis_id,
        sample_run_name="20140918_01.yaml",
        hypothesis_sample_match_name="End-to-End AGP @ 20140918_01 (Simple Scorer)",
        n_processes=6)
    job.start()

    # job = GlycopeptideFragmentMatchingPipeline(
    #     db_file_name, "datafiles/20140918_01.db",
    #     target_hypothesis_id=hypothesis_id,
    #     decoy_hypothesis_id=decoy_hypothesis_id,
    #     sample_run_name="20140918_01.yaml",
    #     scorer=scorer,
    #     hypothesis_sample_match_name="End-to-End AGP @ 20140918_01 (Frequency Scorer)",
    #     n_processes=6)
    # job.start()

if __name__ == '__main__':
    test_main()
