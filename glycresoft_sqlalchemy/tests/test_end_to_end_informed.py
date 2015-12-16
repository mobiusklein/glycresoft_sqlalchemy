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
    try:
        os.remove(db_file_name)
        pass
    except:
        print "\n\nCould not remove database\n\n"

    rules_table = {
        "Hex": (3, 10),
        "HexNAc": (2, 8),
        "Fuc": (0, 5),
        "NeuAc": (0, 4)
    }

    job = constrained_combinatorics.ConstrainedCombinatoricsGlycanHypothesisBuilder(
        db_file_name, rules_table=rules_table, constraints_list=[])
    # job.start()

    job = integrated_omics.IntegratedOmicsMS1SearchSpaceBuilder(
        db_file_name,
        protein_ids=["P02763|A1AG1_HUMAN", "P19652|A1AG2_HUMAN"],  # "P19652|A1AG2_HUMAN",
        mzid_path="datafiles/AGP_Proteomics2.mzid",
        glycomics_path='./datafiles/human_n_glycans.txt',
        glycomics_format='txt',
        # glycomics_path=db_file_name,# './datafiles/human_n_glycans.txt',
        # glycomics_format='hypothesis',
        # source_hypothesis_id=1,
        maximum_glycosylation_sites=1,
        include_all_baseline=False,
        n_processes=6)
    hypothesis_id = job.start()

    ec = os.system(
        ("glycresoft-database-search ms1 -n 5 -i datafiles/20140918_01_isos.db -p db "
         "-g 2e-5 --skip-grouping {db_file_name} {hypothesis_id}").format(
            db_file_name=db_file_name, hypothesis_id=hypothesis_id))
    assert ec == 0

    job = exact_search_space_builder.BatchingExactSearchSpaceBuilder.from_hypothesis_sample_match(
        db_file_name, 1, 6)
    hypothesis_id = job.start()
    job = make_decoys.BatchingDecoySearchSpaceBuilder(db_file_name, hypothesis_ids=[hypothesis_id])
    decoy_hypothesis_id = job.start()[0]

    # hypothesis_id = 2
    # decoy_hypothesis_id = 3

    frequency_counter = pair_counting.pickle.load(open('datafiles/Phil-82-Training-Data/pair_counts.pkl'))
    scorer = pair_counting.FrequencyScorer(frequency_counter)

    job = GlycopeptideFragmentMatchingPipeline(
        db_file_name, "datafiles/20140918_01.db",
        target_hypothesis_id=hypothesis_id,
        decoy_hypothesis_id=decoy_hypothesis_id,
        sample_run_name="20140918_01.yaml",
        hypothesis_sample_match_name="End-to-End AGP @ 20140918_01")
    job.start()


if __name__ == '__main__':
    test_main()
