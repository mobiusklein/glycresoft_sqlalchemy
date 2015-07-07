from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import AbstractConcreteBase, declared_attr
from sqlalchemy import Numeric, Unicode, Column, Integer, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property

from .base import Base


class MassShift(Base):
    __tablename__ = "MassShift"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(128), index=True)
    mass = Column(Numeric(10, 6, asdecimal=False))

    def __hash__(self):
        return hash(self.name)


class GlycanBase(AbstractConcreteBase, Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(128), index=True)
    mass = Column(Numeric(10, 6, asdecimal=False), index=True)
    derivatization = Column(Unicode(64), index=True)

    composition = Column(Unicode(128), index=True)

    @declared_attr
    def hypothesis_id(self):
        return Column(Integer, ForeignKey("Hypothesis.id"))

    @hybrid_method
    def from_hypothesis(self, hypothesis_id):
        return self.hypothesis_id == hypothesis_id


class TheoreticalGlycanComposition(GlycanBase):
    __tablename__ = "TheoreticalGlycanComposition"

    __mapper_args__ = {
        'polymorphic_identity': u'TheoreticalGlycan',
        "concrete": True
    }


class TheoreticalGlycanStructure(GlycanBase):
    __tablename__ = "TheoreticalGlycanStructure"
    composition_reference = Column(Integer, ForeignKey(TheoreticalGlycanComposition.id), index=True)
    glycoct = Column(Unicode(256), index=True)

    __mapper_args__ = {
        'polymorphic_identity': u'TheoreticalGlycan',
        "concrete": True
    }
