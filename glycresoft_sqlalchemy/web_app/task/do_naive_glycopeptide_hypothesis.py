from glycresoft_sqlalchemy.data_model import DatabaseManager, Hypothesis
from glycresoft_sqlalchemy.search_space_builder import naive_glycopeptide_hypothesis
from .task_process import NullPipe, Message, Task


def taskmain(database_path, hypothesis_name, protein_file, site_list_file,
             glycan_file, glycan_file_type, constant_modifications,
             variable_modifications, enzyme, max_missed_cleavages=1,
             output_path=None, n_processes=4, comm=None):
    if comm is None:
        comm = NullPipe()
    manager = DatabaseManager(database_path)
    try:
        task = naive_glycopeptide_hypothesis.NaiveGlycopeptideHypothesisBuilder(
            database_path=database_path,
            hypothesis_name=hypothesis_name,
            protein_file=protein_file,
            site_list_file=site_list_file,
            glycan_file=glycan_file,
            glycan_file_type=glycan_file_type,
            constant_modifications=constant_modifications,
            variable_modifications=variable_modifications,
            enzyme=enzyme,
            max_missed_cleavages=max_missed_cleavages,
            n_processes=n_processes
            )
        hypothesis_id = task.start()
        if task.status != 0:
            raise task.error
        session = manager.session()
        hypothesis = session.query(Hypothesis).get(hypothesis_id)
        comm.send(Message(hypothesis.to_json(), "new-hypothesis"))
    except Exception, e:
        comm.send(Message(e, 'error'))
    return hypothesis_id


class NaiveGlycopeptideHypothesisBuilderTask(Task):
    def __init__(self, database_path, hypothesis_name, protein_file, site_list_file,
                 glycan_file, glycan_file_type, constant_modifications,
                 variable_modifications, enzyme, max_missed_cleavages,
                 output_path, n_processes, comm, callback, **kwargs):
        args = (database_path, hypothesis_name, protein_file, site_list_file,
                glycan_file, glycan_file_type, constant_modifications,
                variable_modifications, enzyme, max_missed_cleavages,
                output_path, n_processes)
        job_name = "Naive Glycopeptide Hypothesis Builder " + hypothesis_name
        kwargs.setdefault('name', job_name)
        super(NaiveGlycopeptideHypothesisBuilderTask, self).__init__(taskmain, args, callback, **kwargs)
