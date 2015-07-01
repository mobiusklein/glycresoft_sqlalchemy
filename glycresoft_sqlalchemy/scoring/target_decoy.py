import logging
try:
    logger = logging.getLogger("target_decoy")
except:
    pass
from itertools import chain
from collections import namedtuple, Counter, defaultdict

from sqlalchemy import func, distinct
from ..data_model import DatabaseManager, GlycopeptideMatch, Protein
from ..data_model import PipelineModule


Threshold = namedtuple("Threshold", ("score", "targets", "decoys", "fdr"))

ms2_score = GlycopeptideMatch.ms2_score
p_value = GlycopeptideMatch.p_value


class RangeCounter(Counter):
    def add_below(self, key, value):
        for pkey in list(self.keys()):
            if pkey <= key:
                self[pkey] += value

    def add_above(self, key, value):
        for pkey in list(self.keys()):
            if pkey > key:
                self[pkey] += value


class TargetDecoyAnalyzer(PipelineModule):
    manager_type = DatabaseManager

    def __init__(self, database_path, target_hypothesis_id=None, decoy_hypothesis_id=None):
        self.manager = self.manager_type(database_path)
        self.target_id = target_hypothesis_id
        self.decoy_id = decoy_hypothesis_id

        session = self.manager.session()

        self.target_count = session.query(
            GlycopeptideMatch.ms2_score).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.target_id).count()

        self.decoy_count = session.query(
            GlycopeptideMatch).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.decoy_id).count()

        session.close()
        self.n_targets_at = {}
        self.n_decoys_at = {}

    def calculate_n_decoys_at(self, threshold):
        if threshold in self.n_decoys_at:
            return self.n_decoys_at[threshold]
        else:
            session = self.manager.session()
            self.n_decoys_at[threshold] = session.query(
            GlycopeptideMatch).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.decoy_id).filter(
            GlycopeptideMatch.ms2_score >= threshold).count()
            return self.n_decoys_at[threshold]

    def calculate_n_targets_at(self, threshold):
        if threshold in self.n_targets_at:
            return self.n_targets_at[threshold]
        else:
            session = self.manager.session()
            self.n_targets_at[threshold] = session.query(
            GlycopeptideMatch).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.target_id).filter(
            GlycopeptideMatch.ms2_score >= threshold).count()
            return self.n_targets_at[threshold]


    def target_decoy_ratio(self, cutoff, score=ms2_score):
        session = self.manager.session()

        decoys_at = self.calculate_n_decoys_at(cutoff)
        targets_at = self.calculate_n_targets_at(cutoff)
        try:
            ratio = decoys_at / float(targets_at)
        except ZeroDivisionError:
            ratio = 1.
        return ratio, targets_at, decoys_at

    def global_thresholds(self):
        session = self.manager.session()

        thresholds = session.query(distinct(func.round(GlycopeptideMatch.ms2_score, 2)))

        results = {}

        for score in thresholds:
            score = score[0]
            ratio, targets_at, decoys_at = self.target_decoy_ratio(score)
            if ratio >= 0.5:
                continue
            result = Threshold(score, targets_at, decoys_at, ratio)
            results[score] = result

        session.close()
        return results

    def p_values(self):
        logger.info("Computing p-values")
        session = self.manager.session()

        tq = session.query(GlycopeptideMatch).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.target_id).order_by(
            GlycopeptideMatch.ms2_score.desc())
        dq = session.query(GlycopeptideMatch).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.decoy_id)

        total_decoys = float(dq.count())
        if total_decoys == 0:
            raise ValueError("No decoy matches found")
        last_score = 0
        last_p_value = 0
        for target in tq:
            if target.ms2_score == last_score:
                target.p_value = last_p_value
                session.add(target)
            else:
                session.commit()
                decoys_at = dq.filter(GlycopeptideMatch.ms2_score >= target.ms2_score).count()
                last_score = target.ms2_score
                
                last_p_value = decoys_at / total_decoys
                target.p_value = last_p_value
                session.add(target)
        session.commit()
        session.close()


    def estimate_percent_incorrect_targets(self, cutoff, score=ms2_score):
        session = self.manager.session()

        # target_cut = tq.filter(score >= 0, score < cutoff).count()
        target_cut = self.target_count - self.calculate_n_targets_at(cutoff)
        # decoy_cut = dq.filter(score >= 0, score < cutoff).count()
        decoy_cut = self.decoy_count - self.calculate_n_decoys_at(cutoff)
        percent_incorrect_targets = target_cut / float(decoy_cut)
        session.close()
        return percent_incorrect_targets

    def fdr_with_percent_incorrect_targets(self, cutoff):
        percent_incorrect_targets = self.estimate_percent_incorrect_targets(cutoff)
        return percent_incorrect_targets * self.target_decoy_ratio(cutoff)[0]

    def _calculate_q_values(self):
        session = self.manager.session()
        thresholds = chain.from_iterable(session.query(distinct(GlycopeptideMatch.ms2_score)).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.target_id).order_by(
            GlycopeptideMatch.ms2_score.asc()))

        mapping = {}
        last_score = 1
        last_q_value = 0
        for threshold in thresholds:
            try:
                q_value = self.fdr_with_percent_incorrect_targets(threshold)
                # If a worse score has a higher q-value than a better score, use that q-value
                # instead.
                if last_q_value < q_value and last_score < threshold:
                    q_value = last_q_value
                last_q_value = q_value
                last_score = threshold
                mapping[threshold] = q_value
            except ZeroDivisionError:
                mapping[threshold] = 1.
        session.close()
        return mapping

    def q_values(self):
        logger.info("Computing q-values")
        session = self.manager.session()

        tq = session.query(GlycopeptideMatch).filter(
            GlycopeptideMatch.protein_id == Protein.id,
            Protein.hypothesis_id == self.target_id)

        q_map = self._calculate_q_values()

        for target in tq:
            target.q_value = q_map[target.ms2_score]
            session.add(target)
        session.commit()
        session.close()

    def run(self):
        # thresholds = self.global_thresholds()
        # self.p_values()
        self.q_values()
        # return thresholds
