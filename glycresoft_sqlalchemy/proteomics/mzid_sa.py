import re
import logging

from pyteomics import mzid
from sqlalchemy import func
from glycresoft_sqlalchemy.data_model import DatabaseManager, Protein, InformedPeptide, Hypothesis
from glycresoft_sqlalchemy.structure import sequence, modification, residue
from glycresoft_sqlalchemy.utils.database_utils import get_or_create
logger = logging.getLogger("mzid")

Sequence = sequence.Sequence
Residue = residue.Residue
Modification = modification.Modification

MzIdentML = mzid.MzIdentML
_local_name = mzid.xml._local_name
peptide_evidence_ref = re.compile(r"(?P<evidence_id>PEPTIDEEVIDENCE_PEPTIDE_\d+_DBSEQUENCE_)(?P<parent_accession>.+)")

PROTEOMICS_SCORE = ["PEAKS:peptideScore", "mascot:score", "PEAKS:proteinScore"]


class MultipleProteinMatchesException(Exception):
    def __init__(self, message, evidence_id, db_sequences, key):
        Exception.__init__(self, message)
        self.evidence_id = evidence_id
        self.db_sequences = db_sequences
        self.key = key


class Parser(MzIdentML):
    def _retrieve_refs(self, info, **kwargs):
        """Retrieves and embeds the data for each attribute in `info` that
        ends in _ref. Removes the id attribute from `info`"""
        multi = None
        for k, v in dict(info).items():
            if k.endswith('_ref'):
                try:
                    info.update(self.get_by_id(v, retrieve_refs=True))
                    del info[k]
                    info.pop('id', None)
                except MultipleProteinMatchesException, e:
                    multi = e
                except:
                    is_multi_db_sequence = peptide_evidence_ref.match(info[k])
                    if is_multi_db_sequence:
                        groups = is_multi_db_sequence.groupdict()
                        evidence_id = groups['evidence_id']
                        db_sequences = groups['parent_accession'].split(':')
                        if len(db_sequences) > 1:
                            multi = MultipleProteinMatchesException(
                                "", evidence_id, db_sequences, k)
                            continue
                    # Fall through
                    logger.debug("%s not found", v)
                    info['skip'] = True
                    info[k] = v
        if multi is not None:
            raise multi

    def _get_info(self, element, **kwargs):
        """Extract info from element's attributes, possibly recursive.
        <cvParam> and <userParam> elements are treated in a special way."""
        name = _local_name(element)
        schema_info = self.schema_info
        if name in {'cvParam', 'userParam'}:
            return self._handle_param(element)

        info = dict(element.attrib)
        # process subelements
        if kwargs.get('recursive'):
            for child in element.iterchildren():
                cname = _local_name(child)
                if cname in {'cvParam', 'userParam'}:
                    newinfo = self._handle_param(child, **kwargs)
                    if not ('name' in info and 'name' in newinfo):
                        info.update(newinfo)
                    else:
                        if not isinstance(info['name'], list):
                            info['name'] = [info['name']]
                        info['name'].append(newinfo.pop('name'))
                else:
                    if cname not in schema_info['lists']:
                        info[cname] = self._get_info_smart(child, **kwargs)
                    else:
                        info.setdefault(cname, []).append(
                                self._get_info_smart(child, **kwargs))

        # process element text
        if element.text and element.text.strip():
            stext = element.text.strip()
            if stext:
                if info:
                    info[name] = stext
                else:
                    return stext

        # convert types
        converters = self._converters
        for k, v in info.items():
            for t, a in converters.items():
                if (_local_name(element), k) in schema_info[t]:
                    info[k] = a(v)
        infos = [info]
        try:
            # resolve refs
            if kwargs.get('retrieve_refs'):
                self._retrieve_refs(info, **kwargs)
        except MultipleProteinMatchesException, e:
            evidence_id = e.evidence_id
            db_sequences = e.db_sequences
            key = e.key
            infos = []
            for name in db_sequences:
                dup = info.copy()
                dup[key] = evidence_id + name
                self._retrieve_refs(dup, **kwargs)
                infos.append(dup)

        # flatten the excessive nesting
        for info in infos:
            for k, v in dict(info).items():
                if k in self._structures_to_flatten:
                    info.update(v)
                    del info[k]

            # another simplification
            for k, v in dict(info).items():
                if isinstance(v, dict) and 'name' in v and len(v) == 1:
                    info[k] = v['name']
        out = []
        for info in infos:
            if len(info) == 2 and 'name' in info and (
                    'value' in info or 'values' in info):
                name = info.pop('name')
                info = {name: info.popitem()[1]}
            out.append(info)
        if len(out) == 1:
            out = out[0]
        return out


def convert_dict_to_sequence(sequence_dict, session):
    # logger.debug("Input: %r, Parent: %r", sequence_dict, parent_protein)
    base_sequence = sequence_dict["PeptideSequence"]
    peptide_sequence = Sequence(sequence_dict["PeptideSequence"])
    insert_sites = []
    counter = 0
    if "SubstitutionModification" in sequence_dict:
        subs = sequence_dict["SubstitutionModification"]
        for sub in subs:
            pos = sub['location'] - 1
            replace = Residue(sub["replacementResidue"])
            peptide_sequence[pos][0] = replace

    if "Modification" in sequence_dict:
        mods = sequence_dict["Modification"]
        for mod in mods:
            pos = mod["location"] - 1
            try:
                modification = Modification(mod["name"])
                if pos == -1:
                    peptide_sequence.n_term = modification
                elif pos == len(peptide_sequence):
                    peptide_sequence.c_term = modification
                else:
                    peptide_sequence.add_modification(pos, modification)
            except KeyError:
                if "unknown modification" in mod:
                    mod_description = mod["unknown modification"]
                    insertion = re.search(r"(\S{3})\sinsertion", mod_description)
                    if insertion:
                        insert_sites.append(mod['location'] - 1)
                    else:
                        raise
    insert_sites.sort()
    evidence_list = sequence_dict["PeptideEvidenceRef"]
    # Flatten the evidence list if it has extra nesting because of alternative
    # mzid parsing
    if isinstance(evidence_list[0], list):
        evidence_list = [x for sub in evidence_list for x in sub]
        # for ev in evidence_list:
        #     print ev['accession']
    score = score_type = None
    for k, v in sequence_dict.items():
        if k in PROTEOMICS_SCORE:
            score_type = k
            score = v
            break
    for evidence in evidence_list:
        if "skip" in evidence:
            continue
        parent_protein = session.query(Protein).filter(Protein.name == evidence['accession']).first()
        start = evidence["start"] - 1
        end = evidence["end"]
        sequence_copy = list(base_sequence)
        for i, position in enumerate(insert_sites):
            sequence_copy.pop(position - i)
        sequence_copy = ''.join(sequence_copy)
        found = parent_protein.protein_sequence.find(sequence_copy)
        if found == -1:
            raise ValueError("Peptide not found in Protein")
        if found != start:
            # logger.debug(
            #     "%r: %d <- %d, %s, %d", evidence["PeptideSequence"], found, start,
            #     parent_protein.accession, parent_protein.sequence.count(base_sequence))
            start = found
            end = start + len(base_sequence)
        try:
            glycosites = list(sequence.find_n_glycosylation_sequons(peptide_sequence))
            match = InformedPeptide(
                calculated_mass=peptide_sequence.mass,
                base_peptide_sequence=base_sequence,
                modified_peptide_sequence=str(peptide_sequence),
                count_glycosylation_sites=len(glycosites),
                start_position=start,
                end_position=end,
                peptide_score=score,
                peptide_score_type=score_type,
                sequence_length=end - start,
                protein_id=parent_protein.id,
                glycosylation_sites=glycosites,
                other={k: v for k, v in sequence_dict.items() if k not in
                       exclude_keys_from_sequence_dict})
            # logger.debug("Produce: %r", match)
            session.add(match)
            counter += 1
        except:
            print(evidence)
            raise
    return counter
exclude_keys_from_sequence_dict = set(("PeptideEvidenceRef",))


class Proteome(object):
    def __init__(self, database_path, mzid_path, hypothesis_id=None):
        self.manager = DatabaseManager(database_path)
        self.manager.initialize()
        self.mzid_path = mzid_path
        self.hypothesis_id = hypothesis_id
        self.parser = Parser(mzid_path, retrieve_refs=True, iterative=False, build_id_cache=True)
        self._load()

    def _load(self):
        self._load_proteins()
        self._load_spectrum_matches()

    def _load_proteins(self):
        session = self.manager.session()
        get_or_create(session, Hypothesis, id=self.hypothesis_id)
        for protein in self.parser.iterfind(
                "ProteinDetectionHypothesis", retrieve_refs=True, recursive=False, iterative=True):
            session.add(
                Protein(
                    name=protein['accession'],
                    protein_sequence=protein['Seq'],
                    hypothesis_id=self.hypothesis_id))
        session.commit()

    def _load_spectrum_matches(self):
        session = self.manager.session()
        counter = 0
        last = 0
        for spectrum_identification in self.parser.iterfind(
                "SpectrumIdentificationItem", retrieve_refs=True, iterative=True):
            counter += convert_dict_to_sequence(spectrum_identification, session)
            if (counter - last) > 1000:
                session.commit()
                last = counter
                logger.info("%d peptides saved.", counter)
        session.commit()

    def peptides(self):
        session = self.manager.session()
        proteins = session.query(Protein).filter(Protein.hypothesis_id == self.hypothesis_id)
        for protein in proteins:
            for informed in protein.informed_peptides:
                yield informed

    def unique_peptides(self):
        session = self.manager.session()
        query = session.query(InformedPeptide, func.count(InformedPeptide)).filter(
            InformedPeptide.protein_id == Protein.id,
            Protein.hypothesis_id == self.hypothesis_id).group_by(InformedPeptide.modified_peptide_sequence)
        return query