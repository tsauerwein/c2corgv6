from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    String,
    ForeignKey,
    Enum
    )
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from . import Base, schema

quality_types = [
    'stub',
    'medium',
    'correct',
    'good',
    'excellent'
    ]


class _DocumentMixin(object):
    # move to metadata?
    protected = Column(Boolean)
    redirects_to = Column(Integer)
    quality = Column(
        Enum(name='quality_type', inherit_schema=True, *quality_types))

    type = Column(String(1))
    __mapper_args__ = {
        'polymorphic_identity': 'd',
        'polymorphic_on': type
    }


class Document(Base, _DocumentMixin):
    __tablename__ = 'documents'
    document_id = Column(Integer, primary_key=True)

    locales = relationship('DocumentLocale')


class ArchiveDocument(Base, _DocumentMixin):
    __tablename__ = 'documents_archives'
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, nullable=False)  # TODO as fk


# Locales for documents
class _DocumentLocaleMixin(object):
    id = Column(Integer, primary_key=True)

    @declared_attr
    def document_id(self):
        return Column(
            Integer, ForeignKey(schema + '.documents.document_id'),
            nullable=False)

    culture = Column(String(2), nullable=False)  # TODO as fk

    title = Column(String(150), nullable=False)
    description = Column(String)

    type = Column(String(1))
    __mapper_args__ = {
        'polymorphic_identity': 'd',
        'polymorphic_on': type
    }


class DocumentLocale(Base, _DocumentLocaleMixin):
    __tablename__ = 'documents_i18n'


class ArchiveDocumentLocale(Base, _DocumentLocaleMixin):
    __tablename__ = 'documents_i18n_archives'
