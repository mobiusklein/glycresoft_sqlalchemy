import os
import logging
logging.basicConfig(level=logging.DEBUG, filemode='w',
                    format="%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
                    datefmt="%H:%M:%S")

from glycresoft_sqlalchemy import data_model
from glycresoft_sqlalchemy.search_space_builder import naive_glycopeptide_hypothesis
from glycresoft_sqlalchemy.search_space_builder import pooling_search_space_builder, pooling_make_decoys
from glycresoft_sqlalchemy.matching import matching, peak_grouping
from glycresoft_sqlalchemy.scoring import target_decoy


def test_main():
    db_file_name = "./datafiles/naive_glycopeptide.db"
    try:
        os.remove(db_file_name)
    except:
        pass
    constant_mods, variable_mods = (["Carbamidomethyl (C)"], ["Deamidated (Q)", "Deamidated (N)"])
    enzyme = 'trypsin'
    job = naive_glycopeptide_hypothesis.NaiveGlycopeptideHypothesisBuilder(
        db_file_name, "test", "./datafiles/proteins_agp_only.fasta",
        None, "./datafiles/human_n_glycan.csv", 'csv', constant_mods,
        variable_mods, enzyme, n_processes=6)
    job.start()

    ec = os.system(
    r"glycresoft-database-search ms1 -n 6 -i datafiles\20140918_01_isos.db datafiles\naive_glycopeptide.db 1"
    r" -p db -g 2e-5 --skip-grouping")
    assert ec == 0
    job = pooling_search_space_builder.PoolingTheoreticalSearchSpaceBuilder.from_hypothesis(
        "datafiles/naive_glycopeptide.db", 1, 6)
    hypothesis_id = job.start()
    job = pooling_make_decoys.PoolingDecoySearchSpaceBuilder(db_file_name, hypothesis_ids=[hypothesis_id])
    decoy_hypothesis_id = job.start()[0]
    manager = data_model.DatabaseManager(db_file_name)
    session = manager.session()
    hsm = data_model.HypothesisSampleMatch(
        target_hypothesis_id=hypothesis_id,
        decoy_hypothesis_id=decoy_hypothesis_id,
        sample_run_name="20140918_01.yaml",
        name="End-to-End AGP @ 20140918_01")
    session.add(hsm)
    session.commit()

    hsm_id = hsm.id

    matcher = matching.IonMatching(db_file_name, hypothesis_id, r"datafiles\20140918_01.db",
                               "db", ms1_tolerance=1e-5, ms2_tolerance=2e-5,
                               hypothesis_sample_match_id=hsm_id, sample_run_id=1, n_processes=8)
    matcher.start()
    matcher = matching.IonMatching(db_file_name, decoy_hypothesis_id, r"datafiles\20140918_01.db",
                               "db", ms1_tolerance=1e-5, ms2_tolerance=2e-5,
                               hypothesis_sample_match_id=hsm_id, sample_run_id=1, n_processes=8)
    matcher.start()
    tda = target_decoy.TargetDecoyAnalyzer(db_file_name, hypothesis_id, decoy_hypothesis_id)
    tda.start()


if __name__ == '__main__':
    test_main()