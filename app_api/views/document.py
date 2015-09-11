from app_api.models.document_history import HistoryMetaData, DocumentVersion
from app_api.models import DBSession


class DocumentRest(object):

    def __init__(self, request):
        self.request = request

    def _create_new_version(self, document):
        archive = document.to_archive()
        archive_locales = document.get_archive_locales()

        meta_data = HistoryMetaData(is_minor=False, comment='creation')
        versions = []
        for locale in archive_locales:
            version = DocumentVersion(
                document_id=document.document_id,
                culture=locale.culture,
                version=1,
                nature='ft',
                document_archive=archive,
                document_i18n_archive=locale,
                history_metadata=meta_data
            )
            versions.append(version)

        DBSession.add(archive)
        DBSession.add_all(archive_locales)
        DBSession.add(meta_data)
        DBSession.add_all(versions)
        DBSession.flush()
