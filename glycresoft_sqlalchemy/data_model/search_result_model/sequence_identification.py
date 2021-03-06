# -*- coding: utf-8 -*-
from collections import defaultdict

from sqlalchemy import and_
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (PickleType, Numeric, Unicode,
                        Column, Integer, ForeignKey, Boolean)
from sqlalchemy.orm.session import object_session


from ..base import Base, Bundle

from ..hypothesis import Hypothesis
from ..generic import MutableDict, MutableList

from ..glycomics import with_glycan_composition

from ..sequence_model.peptide import (
    GlycopeptideBase, HasMS1Information, TheoreticalGlycopeptide,
    Protein)

from ..sequence_model.fragment import (
    TheoreticalPeptideProductIon, TheoreticalGlycopeptideStubIon)

from ..observed_ions import TandemScan, SampleRun


from ...utils.database_utils import get_index


class SpectrumMatchBase(object):
    scan_time = Column(Integer, index=True)
    peak_match_map = Column(MutableDict.as_mutable(PickleType))
    peaks_explained = Column(Integer, index=True)
    peaks_unexplained = Column(Integer)
    best_match = Column(Boolean, index=True)
    precursor_charge_state = Column(Integer)
    precursor_ppm_error = Column(Numeric(10, 8, asdecimal=False))

    @declared_attr
    def hypothesis_sample_match_id(cls):
        return Column(Integer, ForeignKey("HypothesisSampleMatch.id", ondelete="CASCADE"), index=True)

    @declared_attr
    def hypothesis_id(cls):
        return Column(Integer, ForeignKey(Hypothesis.id, ondelete="CASCADE"), index=True)

    def __iter__(self):
        return iter(self.spectrum)

    @property
    def spectrum(self):
        from ..hypothesis_sample_match import HypothesisSampleMatchToSample, HypothesisSampleMatch
        session = object_session(self)
        s = session.query(TandemScan).join(
            HypothesisSampleMatchToSample,
            (TandemScan.sample_run_id == HypothesisSampleMatchToSample.sample_run_id)).filter(
            HypothesisSampleMatch.id == self.hypothesis_sample_match_id).filter(
            TandemScan.sample_run_id == SampleRun.id,
            SampleRun.name == HypothesisSampleMatch.sample_run_name,
            TandemScan.time == self.scan_time)
        return s.first()

    def peak_explained_by(self, peak_id):
        explained = set()
        try:
            matches = self.peak_match_map[peak_id]
            for match in matches:
                explained.add(match["key"])
        except KeyError:
            pass
        return explained

    def add_peak_explaination(self, peak, match_record):
        recs = self.peak_match_map.get(peak.id, [])
        recs.append(match_record)
        self.peak_match_map[peak.id] = recs

    def total_signal_explained(self):
        total = 0.
        for k, v in self.peak_match_map.items():
            ion = v[0]
            total += ion['intensity']
        return total

    def matches_for(self, key):
        for peak_index, matches in self.peak_match_map.items():
            for match in matches:
                if match['key'] == key:
                    yield match

    def ion_matches(self):
        for peak_index, annotations in self.peak_match_map.items():
            for match in annotations:
                yield match

    def ion_prefix_set(self, prefixes):
        series = defaultdict(list)
        for match in self.ion_matches():
            for prefix in prefixes:
                if prefix.is_member(match['key']):
                    series[prefix.name].append(match)
                    break
        return series

    def comatches(self, same_hypothesis=True):
        session = object_session(self)
        TYPE = self.__class__
        index = get_index(TYPE.__table__, "scan_time")
        comatches = session.query(TYPE)
        if same_hypothesis:
            comatches = comatches.filter(TYPE.hypothesis_id == self.hypothesis_id)
        comatches = comatches.filter(
            TYPE.id != self.id,
            TYPE.hypothesis_sample_match_id == self.hypothesis_sample_match_id,
            TYPE.scan_time == self.scan_time)
        comatches = comatches.with_hint(TYPE, "indexed by " + index.name, "sqlite")
        return comatches


class GlycopeptideSpectrumMatch(Base, SpectrumMatchBase):
    __tablename__ = "GlycopeptideSpectrumMatch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    glycopeptide_match_id = Column(Integer, ForeignKey("GlycopeptideMatch.id"), index=True)

    theoretical_glycopeptide_id = Column(
        Integer, ForeignKey("TheoreticalGlycopeptide.id", ondelete='CASCADE'), index=True)

    theoretical_glycopeptide = relationship("TheoreticalGlycopeptide")

    def __repr__(self):
        try:
            return "<GlycopeptideSpectrumMatch {} -> Spectrum {} | {} Peaks Matched>".format(
                self.glycopeptide_sequence, self.scan_time, len(self.peak_match_map))
        except:
            return "<GlycopeptideSpectrumMatch (No Sequence Error) {}>".format(self.id)

    def as_match_like(self):
        from glycresoft_sqlalchemy.scoring import simple_scoring_algorithm
        b = Bundle(**simple_scoring_algorithm.split_ion_list(self.ion_matches()))
        b.glycopeptide_sequence = self.glycopeptide_sequence
        b.id = self.id
        return b

    @property
    def glycopeptide_sequence(self):
        try:
            try:
                return self.theoretical_glycopeptide.glycopeptide_sequence
            except:
                return self.glycopeptide_match.glycopeptide_sequence
        except:
            return "(No Sequence Error)"

    scores = association_proxy(
        "_scores", "value", creator=lambda k, v: GlycopeptideSpectrumMatchScore(name=k, value=v))

    # def __getattr__(self, name):
    #     try:
    #         return self.scores[name]
    #     except:
    #         raise AttributeError("%s has no attribute named %s" % (self.__class__.__name__, name))


class GlycopeptideSpectrumMatchScore(Base):
    __tablename__ = "GlycopeptideSpectrumMatchScore"

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), index=True)
    value = Column(Numeric(10, 6, asdecimal=False), index=True)

    spectrum_match_id = Column(Integer, ForeignKey(
        "GlycopeptideSpectrumMatch.id", ondelete="CASCADE"), index=True)

    spectrum_match = relationship(GlycopeptideSpectrumMatch, backref=backref(
        "_scores", collection_class=attribute_mapped_collection("name"),
        cascade="all, delete-orphan"))

    def __repr__(self):
        return "GlycopeptideSpectrumMatchScore(%s=%r)" % (self.name, self.value)


@with_glycan_composition("glycan_composition_str")
class GlycopeptideMatch(GlycopeptideBase, Base, HasMS1Information):
    __tablename__ = "GlycopeptideMatch"
    __collection_name__ = "glycopeptide_matches"

    id = Column(Integer, primary_key=True)
    theoretical_glycopeptide_id = Column(Integer, ForeignKey(
        TheoreticalGlycopeptide.id, ondelete='CASCADE'), index=True)
    theoretical_reference = relationship(TheoreticalGlycopeptide)
    hypothesis_sample_match_id = Column(Integer, ForeignKey(
        "HypothesisSampleMatch.id", ondelete='CASCADE'), index=True)
    hypothesis_sample_match = relationship(
        "HypothesisSampleMatch", backref=backref("glycopeptide_matches", lazy='dynamic'))

    ms2_score = Column(Numeric(10, 6, asdecimal=False), index=True)

    @declared_attr
    def spectrum_matches(self):
        return relationship(
            GlycopeptideSpectrumMatch, backref=backref('glycopeptide_match'), lazy='dynamic')

    p_value = Column(Numeric(10, 6, asdecimal=False))
    q_value = Column(Numeric(10, 6, asdecimal=False))

    scan_id_range = Column(MutableList.as_mutable(PickleType))
    first_scan = Column(Integer)
    last_scan = Column(Integer)

    mean_coverage = Column(Numeric(10, 6, asdecimal=False))
    mean_hexnac_coverage = Column(Numeric(10, 6, asdecimal=False))

    oxonium_ions = Column(MutableList.as_mutable(PickleType))
    stub_ions = Column(MutableList.as_mutable(PickleType))

    bare_b_ions = Column(MutableList.as_mutable(PickleType))
    glycosylated_b_ions = Column(MutableList.as_mutable(PickleType))

    bare_y_ions = Column(MutableList.as_mutable(PickleType))
    glycosylated_y_ions = Column(MutableList.as_mutable(PickleType))

    @classmethod
    def is_not_decoy(cls):
        return ((cls.protein_id == Protein.id) & (Protein.hypothesis_id == Hypothesis.id) & (~Hypothesis.is_decoy))

    @classmethod
    def is_decoy(cls):
        return ((cls.protein_id == Protein.id) & (Protein.hypothesis_id == Hypothesis.id) & (Hypothesis.is_decoy))

    def __repr__(self):
        rep = "<GlycopeptideMatch {} {} {}>".format(self.glycopeptide_sequence, self.ms2_score, self.calculated_mass)
        return rep

    def fragments(self, kind=('ox', 'b', 'y', 'gb', 'gy', 'stub')):
        '''
        A unified API for accessing lazy sequences of molecular fragments

        Parameters
        ----------
        kind: sequence of str
            A sequence of sigil strings for the different types of fragments
            to generate. These sigils follow the standard nomenclature of bc-yz for peptides
            and the BC-YZ nomenclature for glycans, as well as special combinations for oxonium
            ions and stub glycopeptide ions.

        Yields
        ------
        dict: A simple mapping object that defines a fragment
        '''
        kind = set(kind)
        if 'ox' in kind:
            for ox in self.oxonium_ions:
                yield ox
        if 'b' in kind:
            for b in self.bare_b_ions:
                yield b
        if 'y' in kind:
            for y in self.bare_y_ions:
                yield y
        if 'gb' in kind:
            for bg in self.glycosylated_b_ions:
                yield bg
        if 'gy' in kind:
            for yg in self.glycosylated_y_ions:
                yield yg
        if 'stub' in kind:
            for stub in self.stub_ions:
                yield stub


class GlycanStructureMatch(Base):
    __tablename__ = "GlycanStructureMatch"

    id = Column(Integer, primary_key=True, autoincrement=True)

    theoretical_reference_id = Column(
        Integer, ForeignKey("TheoreticalGlycanStructure.id", ondelete="CASCADE"), index=True)
    theoretical_reference = relationship("TheoreticalGlycanStructure")

    hypothesis_sample_match_id = Column(Integer, ForeignKey("HypothesisSampleMatch.id"), index=True)
    hypothesis_sample_match = relationship(
        "HypothesisSampleMatch", backref=backref("glycan_structure_matches", lazy='dynamic'))

    ms1_score = Column(Numeric(10, 6, asdecimal=False), index=True)
    ms2_score = Column(Numeric(10, 6, asdecimal=False), index=True)

    observed_mass = Column(Numeric(12, 6, asdecimal=False))
    ppm_error = Column(Numeric(12, 6, asdecimal=False))
    volume = Column(Numeric(12, 4, asdecimal=False))

    fragment_matches = Column(MutableList.as_mutable(PickleType))

    scan_id_range = Column(MutableList.as_mutable(PickleType))
    first_scan = Column(Integer)
    last_scan = Column(Integer)

    spectrum_matches = relationship("GlycanSpectrumMatch", backref='glycan_structure_match', lazy='dynamic')

    def structure(self):
        return self.theoretical_reference.structure()

    @property
    def name(self):
        return self.theoretical_reference.name

    @property
    def glycoct(self):
        return self.theoretical_reference.glycoct

    @property
    def calculated_mass(self):
        return self.theoretical_reference.calculated_mass

    @property
    def composition(self):
        return self.theoretical_reference.composition

    @property
    def glycan_composition(self):
        return self.theoretical_reference.glycan_composition

    @property
    def reduction(self):
        return self.theoretical_reference.reduction

    @property
    def derivatization(self):
        return self.theoretical_reference.derivatization

    def __repr__(self):
        rep = "<{self.__class__.__name__} {self.ms2_score}\n{self.theoretical_reference.glycoct}>".format(self=self)
        return rep


class GlycanSpectrumMatch(Base, SpectrumMatchBase):
    __tablename__ = "GlycanSpectrumMatch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    glycan_structure_match_id = Column(Integer, ForeignKey(GlycanStructureMatch.id), index=True)

    def __repr__(self):
        return "<GlycanSpectrumMatch {} -> Spectrum {} | {} Peaks Matched>".format(
            self.glycan_structure_match.name or self.glycan_structure_match.id,
            self.scan_time, len(self.peak_match_map))


class GlycopeptideIonMatchBase(object):

    id = Column(Integer, primary_key=True)

    @declared_attr
    def glycopeptide_match_id(self):
        return Column(Integer, ForeignKey(
            GlycopeptideSpectrumMatch.id, ondelete="CASCADE"), index=True)

    peak_index = Column(Integer)
    charge = Column(Integer)

    intensity = Column(Numeric(12, 4, asdecimal=False))
    ppm_error = Column(Numeric(10, 8, asdecimal=False))

    @declared_attr
    def spectrum_match(self):
        return relationship(GlycopeptideSpectrumMatch)


class PeptideProductIonMatch(GlycopeptideIonMatchBase, Base):
    __tablename__ = "PeptideProductIonMatch"

    matched_ion_id = Column(Integer, ForeignKey(
        TheoreticalPeptideProductIon.id, ondelete="CASCADE"), index=True)
    matched_ion = relationship(TheoreticalPeptideProductIon)

    @property
    def name(self):
        return self.matched_ion.name


class GlycopeptideStubIonMatch(GlycopeptideIonMatchBase, Base):
    __tablename__ = "GlycopeptideStubIonMatch"

    matched_ion_id = Column(Integer, ForeignKey(
        TheoreticalGlycopeptideStubIon.id, ondelete="CASCADE"), index=True)
    matched_ion = relationship(TheoreticalGlycopeptideStubIon)

    @property
    def name(self):
        return self.matched_ion.name


class HasTheoreticalGlycopeptideProductIonMatches(object):

    @declared_attr
    def matched_glycopeptide_stub_ions(cls):
        return relationship(GlycopeptideStubIonMatch, lazy="dynamic")

    @declared_attr
    def matched_peptide_product_ions(cls):
        return relationship(TheoreticalPeptideProductIon, lazy="dynamic")

    # Specialized Series Queries For Stub Glycopeptides / Oxonium Ions

    @hybrid_property
    def oxonium_ions(self):
        return self.matched_glycopeptide_stub_ions.join(
            TheoreticalGlycopeptideStubIon).filter(
            TheoreticalGlycopeptideStubIon.ion_series == "oxonium_ion")

    @oxonium_ions.expression
    def oxonium_ions(cls):
        return and_((cls.id == GlycopeptideStubIonMatch.glycopeptide_match_id),
                    (GlycopeptideStubIonMatch.matched_ion_id == TheoreticalGlycopeptideStubIon.id),
                    (TheoreticalGlycopeptideStubIon.ion_series == "oxonium_ion"))

    @hybrid_property
    def stub_glycopeptides(self):
        return self.matched_glycopeptide_stub_ions.join(
            TheoreticalGlycopeptideStubIon).filter(
            TheoreticalGlycopeptideStubIon.ion_series == "stub_glycopeptide")

    @stub_glycopeptides.expression
    def stub_glycopeptides(cls):
        return and_((cls.id == GlycopeptideStubIonMatch.glycopeptide_match_id),
                    (GlycopeptideStubIonMatch.matched_ion_id == TheoreticalGlycopeptideStubIon.id),
                    (TheoreticalGlycopeptideStubIon.ion_series == "stub_glycopeptide"))

    # Specialized Series Queries For b/y ions
    @hybrid_property
    def bare_b_ions(self):
        return self.matched_peptide_product_ions.join(
            TheoreticalPeptideProductIon).filter(
            TheoreticalPeptideProductIon.ion_series == "b",
            ~TheoreticalPeptideProductIon.glycosylated)

    @bare_b_ions.expression
    def bare_b_ions(cls):
        return and_((cls.id == PeptideProductIonMatch.glycopeptide_match_id),
                    (PeptideProductIonMatch.matched_ion_id == TheoreticalPeptideProductIon.id),
                    (TheoreticalPeptideProductIon.ion_series == "b"),
                    (~TheoreticalPeptideProductIon.glycosylated))

    @hybrid_property
    def bare_y_ions(self):
        return self.matched_peptide_product_ions.join(
            TheoreticalPeptideProductIon).filter(
            TheoreticalPeptideProductIon.ion_series == "y",
            ~TheoreticalPeptideProductIon.glycosylated)

    @bare_y_ions.expression
    def bare_y_ions(cls):
        return and_((cls.id == PeptideProductIonMatch.glycopeptide_match_id),
                    (PeptideProductIonMatch.matched_ion_id == TheoreticalPeptideProductIon.id),
                    (TheoreticalPeptideProductIon.ion_series == "y"),
                    (~TheoreticalPeptideProductIon.glycosylated))

    @hybrid_property
    def glycosylated_b_ions(self):
        return self.matched_peptide_product_ions.join(
            TheoreticalPeptideProductIon).filter(
            TheoreticalPeptideProductIon.ion_series == "b",
            TheoreticalPeptideProductIon.glycosylated)

    @glycosylated_b_ions.expression
    def glycosylated_b_ions(cls):
        return and_((cls.id == PeptideProductIonMatch.glycopeptide_match_id),
                    (PeptideProductIonMatch.matched_ion_id == TheoreticalPeptideProductIon.id),
                    (TheoreticalPeptideProductIon.ion_series == "b"),
                    (TheoreticalPeptideProductIon.glycosylated))

    @hybrid_property
    def glycosylated_y_ions(self):
        return self.matched_peptide_product_ions.join(
            TheoreticalPeptideProductIon).filter(
            TheoreticalPeptideProductIon.ion_series == "y",
            TheoreticalPeptideProductIon.glycosylated)

    @glycosylated_y_ions.expression
    def glycosylated_y_ions(cls):
        return and_((cls.id == PeptideProductIonMatch.glycopeptide_match_id),
                    (PeptideProductIonMatch.matched_ion_id == TheoreticalPeptideProductIon.id),
                    (TheoreticalPeptideProductIon.ion_series == "y"),
                    (TheoreticalPeptideProductIon.glycosylated))
