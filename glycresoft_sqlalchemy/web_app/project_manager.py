import os
from os import path
import shutil
import logging
from glycresoft_sqlalchemy.data_model import (
    DatabaseManager, Hypothesis, SampleRun, HypothesisSampleMatch,
    BUPIDDeconvolutedLCMSMSSampleRun, Decon2LSLCMSSampleRun,
    MS1GlycanHypothesis,
    MS1GlycopeptideHypothesis, MS2GlycopeptideHypothesis,
    PeakGroupMatch, MS1GlycopeptideHypothesisSampleMatch)

from task.task_process import TaskManager, pickle
from task.dummy import DummyTask
from glycresoft_sqlalchemy.web_app.common import logmethod

logger = logging.getLogger("project_manager")


class ProjectManager(DatabaseManager, TaskManager):
    def __init__(self, database_path, sample_dir=None, results_dir=None, temp_dir=None, task_dir=None):
        DatabaseManager.__init__(self, database_path)
        if sample_dir is None:
            sample_dir = path.join(path.dirname(database_path), 'sample_dir')
        if results_dir is None:
            results_dir = path.join(path.dirname(database_path), 'results_dir')
        if temp_dir is None:
            temp_dir = path.join(path.dirname(database_path), 'temp_dir')
        if task_dir is None:
            task_dir = path.join(path.dirname(database_path), 'task_dir')
        self.sample_dir = sample_dir
        self.results_dir = results_dir
        self.temp_dir = temp_dir
        self.task_dir = task_dir
        self._ensure_paths_exist()
        self.sample_submanagers = []
        for sample in os.listdir(self.sample_dir):
            manager = DatabaseManager(path.join(self.sample_dir, sample))
            try:
                manager.connect()
                self.sample_submanagers.append(manager)
            except:
                pass
        TaskManager.__init__(self, task_dir)

    def _ensure_paths_exist(self):
        try:
            os.makedirs(self.sample_dir)
        except:
            pass
        try:
            os.makedirs(self.results_dir)
        except:
            pass
        try:
            os.makedirs(self.temp_dir)
        except:
            pass
        try:
            os.makedirs(self.task_dir)
        except:
            pass

    @logmethod
    def find_sample(self, name):
        for manager in self.sample_submanagers:
            match = manager.session().query(SampleRun).filter(SampleRun.name == name).first()
            if match is None:
                continue
            else:
                return match, manager
        raise KeyError(name)

    @logmethod
    def add_sample_path(self, fname):
        name = path.basename(fname)
        dest = path.join(self.sample_dir, name)
        shutil.copy(fname, dest)
        self.sample_submanagers.append(DatabaseManager(dest))

    def get_sample_path(self, name):
        return path.join(self.sample_dir, name)

    def get_temp_path(self, name):
        return path.join(self.temp_dir, name)

    def get_task_path(self, name):
        return path.join(self.task_dir, name)

    @logmethod
    def hypotheses(self):
        session = self.session()
        return session.query(Hypothesis).filter(~Hypothesis.is_decoy)

    @logmethod
    def ms1_glycan_hypotheses(self):
        session = self.session()
        return session.query(MS1GlycanHypothesis).filter(~Hypothesis.is_decoy)

    @logmethod
    def ms1_glycopeptide_hypotheses(self):
        session = self.session()
        return session.query(MS1GlycopeptideHypothesis).filter(~Hypothesis.is_decoy)

    @logmethod
    def ms2_glycopeptide_hypotheses(self):
        session = self.session()
        return session.query(MS2GlycopeptideHypothesis).filter(~Hypothesis.is_decoy)

    @logmethod
    def ms1_glycopeptide_peak_group_matches(self):
        session = self.session()
        return session.query(MS1GlycopeptideHypothesisSampleMatch)

    @logmethod
    def samples(self):
        results = []
        for manager in self.sample_submanagers:
            results.extend(manager.session().query(SampleRun).all())
        return results

    @logmethod
    def ms1_samples(self):
        results = []
        for manager in self.sample_submanagers:
            results.extend(manager.session().query(Decon2LSLCMSSampleRun).all())
        return results

    @logmethod
    def ms2_samples(self):
        results = []
        for manager in self.sample_submanagers:
            results.extend(manager.session().query(BUPIDDeconvolutedLCMSMSSampleRun).all())
        return results

    @logmethod
    def add_sample(self, path):
        self.sample_submanagers.append(DatabaseManager(path))

    @logmethod
    def add_task(self, task):
        TaskManager.add_task(self, task)
        path = self.get_task_path(task.name)
        pickle.dump(task.args[:-1], open(path, 'wb'))
