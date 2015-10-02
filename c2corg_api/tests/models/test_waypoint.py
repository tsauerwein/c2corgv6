from c2corg_api.models.waypoint import Waypoint, WaypointLocale
from c2corg_api.models.document import UpdateType

from c2corg_api.tests import BaseTestCase

from sqlalchemy.orm.exc import StaleDataError


class TestWaypoint(BaseTestCase):

    def test_to_archive(self):
        waypoint = Waypoint(
            document_id=1, waypoint_type='summit', elevation=2203,
            locales=[
                WaypointLocale(
                    id=2, culture='en', title='A', description='abc'),
                WaypointLocale(
                    id=3, culture='fr', title='B', description='bcd'),
            ]
        )

        waypoint_archive = waypoint.to_archive()

        self.assertIsNone(waypoint_archive.id)
        self.assertEqual(waypoint_archive.document_id, waypoint.document_id)
        self.assertEqual(
            waypoint_archive.waypoint_type, waypoint.waypoint_type)
        self.assertEqual(waypoint_archive.elevation, waypoint.elevation)

        archive_locals = waypoint.get_archive_locales()

        self.assertEqual(len(archive_locals), 2)
        locale = waypoint.locales[0]
        locale_archive = archive_locals[0]
        self.assertIsNot(locale_archive, locale)
        self.assertIsNone(locale_archive.id)
        self.assertEqual(locale_archive.culture, locale.culture)
        self.assertEqual(locale_archive.title, locale.title)
        self.assertEqual(locale_archive.description, locale.description)

    def test_version_is_incremented(self):
        waypoint = Waypoint(
            document_id=1, waypoint_type='summit', elevation=2203,
            locales=[
                WaypointLocale(
                    id=2, culture='en', title='A', description='abc')
            ]
        )
        self.session.add(waypoint)
        self.session.flush()

        version1 = waypoint.version_hash
        self.assertIsNotNone(version1)

        # make a change to the waypoint and check that the version changes
        # once the waypoint is persisted
        waypoint.elevation = 1234
        self.session.merge(waypoint)
        self.session.flush()
        version2 = waypoint.version_hash
        self.assertNotEqual(version1, version2)

    def test_version_concurrent_edit(self):
        """Test that a `StaleDataError` is thrown when trying to update a
        waypoint with an old version number.
        """
        waypoint1 = Waypoint(
            document_id=1, waypoint_type='summit', elevation=2203,
            locales=[
                WaypointLocale(
                    id=2, culture='en', title='A', description='abc')
            ]
        )

        # add the initial waypoint
        self.session.add(waypoint1)
        self.session.flush()
        self.session.expunge(waypoint1)
        version1 = waypoint1.version_hash
        self.assertIsNotNone(version1)

        # change the waypoint
        waypoint2 = self.session.query(Waypoint).get(waypoint1.document_id)
        waypoint2.elevation = 1234
        self.session.merge(waypoint2)
        self.session.flush()
        version2 = waypoint2.version_hash
        self.assertNotEqual(version1, version2)

        self.assertNotEqual(waypoint1.version_hash, waypoint2.version_hash)
        self.assertNotEqual(waypoint1.elevation, waypoint2.elevation)

        # then try to update the waypoint again with the old version
        waypoint1.elevation = 2345
        self.assertRaises(StaleDataError, self.session.merge, waypoint1)

    def test_update(self):
        waypoint_db = Waypoint(
            document_id=1, waypoint_type='summit', elevation=2203,
            version_hash='123',
            locales=[
                WaypointLocale(
                    id=2, culture='en', title='A', description='abc',
                    version_hash='345'),
                WaypointLocale(
                    id=3, culture='fr', title='B', description='bcd',
                    version_hash='678'),
            ]
        )
        waypoint_in = Waypoint(
            document_id=1, waypoint_type='summit', elevation=1234,
            version_hash='123',
            locales=[
                WaypointLocale(
                    id=2, culture='en', title='C', description='abc',
                    version_hash='345'),
                WaypointLocale(
                    culture='es', title='D', description='efg'),
            ]
        )
        waypoint_db.update(waypoint_in)
        self.assertEqual(waypoint_db.elevation, waypoint_in.elevation)
        self.assertEqual(len(waypoint_db.locales), 3)

        locale_en = waypoint_db.get_locale('en')
        locale_fr = waypoint_db.get_locale('fr')
        locale_es = waypoint_db.get_locale('es')

        self.assertEqual(locale_en.title, 'C')
        self.assertEqual(locale_fr.title, 'B')
        self.assertEqual(locale_es.title, 'D')

    def test_get_update_type_figures_only(self):
        waypoint = self._get_waypoint()
        self.session.add(waypoint)
        self.session.flush()

        versions = waypoint.get_versions()

        waypoint.elevation = 1234
        self.session.merge(waypoint)
        self.session.flush()

        (type, changed_langs) = waypoint.get_update_type(versions)
        self.assertEqual(type, UpdateType.FIGURES_ONLY)
        self.assertEqual(changed_langs, [])

    def test_get_update_type_lang_only(self):
        waypoint = self._get_waypoint()
        self.session.add(waypoint)
        self.session.flush()

        versions = waypoint.get_versions()

        waypoint.get_locale('en').description = 'abcd'
        self.session.merge(waypoint)
        self.session.flush()

        (type, changed_langs) = waypoint.get_update_type(versions)
        self.assertEqual(type, UpdateType.LANG_ONLY)
        self.assertEqual(changed_langs, ['en'])

    def test_get_update_type_lang_only_new_lang(self):
        waypoint = self._get_waypoint()
        self.session.add(waypoint)
        self.session.flush()

        versions = waypoint.get_versions()

        waypoint.locales.append(WaypointLocale(
            culture='es', title='A', description='abc'))
        self.session.merge(waypoint)
        self.session.flush()

        (type, changed_langs) = waypoint.get_update_type(versions)
        self.assertEqual(type, UpdateType.LANG_ONLY)
        self.assertEqual(changed_langs, ['es'])

    def test_get_update_type_all(self):
        waypoint = self._get_waypoint()
        self.session.add(waypoint)
        self.session.flush()

        versions = waypoint.get_versions()

        waypoint.elevation = 1234
        waypoint.get_locale('en').description = 'abcd'
        waypoint.locales.append(WaypointLocale(
            culture='es', title='A', description='abc'))

        self.session.merge(waypoint)
        self.session.flush()

        (type, changed_langs) = waypoint.get_update_type(versions)
        self.assertEqual(type, UpdateType.ALL)
        self.assertEqual(changed_langs, ['en', 'es'])

    def test_get_update_type_none(self):
        waypoint = self._get_waypoint()
        self.session.add(waypoint)
        self.session.flush()

        versions = waypoint.get_versions()
        self.session.merge(waypoint)
        self.session.flush()

        (type, changed_langs) = waypoint.get_update_type(versions)
        self.assertEqual(type, UpdateType.NONE)
        self.assertEqual(changed_langs, [])

    def _get_waypoint(self):
        return Waypoint(
            waypoint_type='summit', elevation=2203,
            locales=[
                WaypointLocale(
                    culture='en', title='A', description='abc',
                    pedestrian_access='y'),
                WaypointLocale(
                    culture='fr', title='B', description='bcd',
                    pedestrian_access='y')
            ]
        )
