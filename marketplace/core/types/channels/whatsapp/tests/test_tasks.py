from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from ..tasks import sync_whatsapp_apps
from marketplace.applications.models import App

from unittest.mock import MagicMock

User = get_user_model()


class SyncWhatsAppAppsTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        lock_mock = MagicMock()
        lock_mock.__enter__.return_value = None
        lock_mock.__exit__.return_value = False
        self.redis_mock.lock.return_value = lock_mock

        wpp_type = APPTYPES.get("wpp")
        wpp_cloud_type = APPTYPES.get("wpp-cloud")

        self.wpp_app = wpp_type.create_app(
            config={"auth_token": "12345"},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        self.wpp_cloud_app = wpp_cloud_type.create_app(
            config={},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        return super().setUp()

    def _get_mock_value(self, project_uuid: str, flow_object_uuid: str, config: dict = {}) -> list:
        return [
            {
                "uuid": flow_object_uuid,
                "name": "teste",
                "config": config,
                "address": "f234234",
                "project_uuid": project_uuid,
                "is_active": True,
            }
        ]

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_create_new_whatsapp_app(self, list_channel_mock: "MagicMock", mock_redis) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        list_channel_mock.return_value = self._get_mock_value(project_uuid, flow_object_uuid)

        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()

        self.assertTrue(App.objects.filter(flow_object_uuid=flow_object_uuid).exists())
        self.assertTrue(App.objects.filter(project_uuid=project_uuid).exists())

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_update_app_auth_token(self, list_channel_mock: "MagicMock", mock_redis) -> None:
        list_channel_mock.return_value = self._get_mock_value(
            self.wpp_app.project_uuid, self.wpp_app.flow_object_uuid, config={"auth_token": "54321"}
        )
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_apps()

        app = App.objects.get(uuid=self.wpp_app.uuid)
        self.assertEqual(app.config.get("auth_token"), "54321")

    @patch("marketplace.core.types.channels.whatsapp.tasks.get_redis_connection")
    @patch("marketplace.connect.client.ConnectProjectClient.list_channels")
    def test_channel_migration_from_wpp_cloud_to_wpp(self, list_channel_mock: "MagicMock", mock_redis) -> None:
        list_channel_mock.return_value = self._get_mock_value(
            self.wpp_cloud_app.project_uuid, self.wpp_cloud_app.flow_object_uuid
        )
        mock_redis.return_value = self.redis_mock
        sync_whatsapp_apps()
