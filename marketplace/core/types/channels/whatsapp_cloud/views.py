import string
import requests


from typing import TYPE_CHECKING

from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import (
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.exceptions import APIException

from django.conf import settings
from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404

from marketplace.core.types import views
from marketplace.applications.models import App
from marketplace.celery import app as celery_app
from marketplace.connect.client import ConnectProjectClient
from marketplace.flows.client import FlowsClient
from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Catalog, ProductFeed, Product
from marketplace.wpp_products.parsers import ProductFeedParser

from ..whatsapp_base import mixins
from ..whatsapp_base.serializers import WhatsAppSerializer
from ..whatsapp_base.exceptions import FacebookApiException

from .facades import CloudProfileFacade, CloudProfileContactFacade
from .requests import PhoneNumbersRequest

from .serializers import WhatsAppCloudConfigureSerializer

from marketplace.wpp_products.serializers import (
    CatalogSerializer,
    ProductFeedSerializer,
    ProductSerializer,
)


if TYPE_CHECKING:
    from rest_framework.request import Request  # pragma: no cover


class WhatsAppCloudViewSet(
    views.BaseAppTypeViewSet,
    mixins.WhatsAppConversationsMixin,
    mixins.WhatsAppContactMixin,
    mixins.WhatsAppProfileMixin,
):
    serializer_class = WhatsAppSerializer

    business_profile_class = CloudProfileContactFacade
    profile_class = CloudProfileFacade

    @property
    def app_waba_id(self) -> dict:
        config = self.get_object().config
        waba_id = config.get("wa_waba_id", None)

        if waba_id is None:
            raise ValidationError(
                "This app does not have WABA (Whatsapp Business Account ID) configured"
            )

        return waba_id

    @property
    def profile_config_credentials(self) -> dict:
        config = self.get_object().config
        phone_numbrer_id = config.get("wa_phone_number_id", None)

        if phone_numbrer_id is None:
            raise ValidationError("The phone number is not configured")

        return dict(phone_number_id=phone_numbrer_id)

    @property
    def get_access_token(self) -> str:
        access_token = settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN

        if access_token is None:
            raise ValidationError("This app does not have fb_access_token in settings")

        return access_token

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def destroy(self, request, *args, **kwargs) -> Response:
        return Response(
            "This channel cannot be deleted", status=status.HTTP_403_FORBIDDEN
        )

    def create(self, request, *args, **kwargs):
        serializer = WhatsAppCloudConfigureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_uuid = request.data.get("project_uuid")

        input_token = serializer.validated_data.get("input_token")
        waba_id = serializer.validated_data.get("waba_id")
        phone_number_id = serializer.validated_data.get("phone_number_id")
        business_id = serializer.validated_data.get("business_id")
        waba_currency = "USD"

        base_url = settings.WHATSAPP_API_URL
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"
        }

        url = f"{base_url}/{waba_id}"
        params = dict(fields="message_template_namespace")
        response = requests.get(url, params=params, headers=headers)

        message_template_namespace = response.json().get("message_template_namespace")

        url = f"{base_url}/{waba_id}/assigned_users"
        params = dict(
            user=settings.WHATSAPP_CLOUD_SYSTEM_USER_ID,
            access_token=settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN,
            tasks="MANAGE",
        )
        response = requests.post(url, params=params, headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        url = f"{base_url}/{settings.WHATSAPP_CLOUD_EXTENDED_CREDIT_ID}/whatsapp_credit_sharing_and_attach"
        params = dict(waba_id=waba_id, waba_currency=waba_currency)
        response = requests.post(url, params=params, headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        allocation_config_id = response.json().get("allocation_config_id")

        url = f"{base_url}/{waba_id}/subscribed_apps"
        response = requests.post(url, headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        url = f"{base_url}/{phone_number_id}/register"
        pin = get_random_string(6, string.digits)
        data = dict(messaging_product="whatsapp", pin=pin)
        response = requests.post(url, headers=headers, data=data)

        if response.status_code != status.HTTP_200_OK:
            raise ValidationError(response.json())

        phone_number_request = PhoneNumbersRequest(input_token)
        phone_number = phone_number_request.get_phone_number(phone_number_id)

        config = dict(
            wa_number=phone_number.get("display_phone_number"),
            wa_verified_name=phone_number.get("verified_name"),
            wa_waba_id=waba_id,
            wa_currency=waba_currency,
            wa_business_id=business_id,
            wa_message_template_namespace=message_template_namespace,
            wa_pin=pin,
        )

        client = ConnectProjectClient()
        channel = client.create_wac_channel(
            request.user.email, project_uuid, phone_number_id, config
        )

        config["title"] = config.get("wa_number")
        config["wa_allocation_config_id"] = allocation_config_id
        config["wa_phone_number_id"] = phone_number_id

        App.objects.create(
            code=self.type_class.code,
            config=config,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=request.user,
            flow_object_uuid=channel.get("uuid"),
            configured=True,
        )

        celery_app.send_task(name="sync_whatsapp_cloud_wabas")
        celery_app.send_task(name="sync_whatsapp_cloud_phone_numbers")

        return Response(serializer.validated_data)

    @action(detail=False, methods=["GET"])
    def debug_token(self, request: "Request", **kwargs):
        """
        Returns the waba id for the input token.

            Query Parameters:
                - input_token (str): User Facebook Access Token

            Return body:
            "<WABA_ID"
        """
        input_token = request.query_params.get("input_token", None)

        if input_token is None:
            raise ValidationError("input_token is a required parameter!")

        url = f"{settings.WHATSAPP_API_URL}/debug_token"
        params = dict(input_token=input_token)
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            raise ValidationError(response.json())

        data = response.json().get("data")

        # TODO: This code snippet needs refactoring

        try:
            whatsapp_business_management = next(
                filter(
                    lambda scope: scope.get("scope") == "whatsapp_business_management",
                    data.get("granular_scopes"),
                )
            )
        except StopIteration:
            raise ValidationError("Invalid token permissions")

        try:
            business_management = next(
                filter(
                    lambda scope: scope.get("scope") == "business_management",
                    data.get("granular_scopes"),
                )
            )
        except StopIteration:
            business_management = dict()

        try:
            waba_id = whatsapp_business_management.get("target_ids")[0]
        except IndexError:
            raise ValidationError("Missing WhatsApp Business Accound Id")

        try:
            business_id = business_management.get("target_ids", [])[0]
        except IndexError:
            url = f"{settings.WHATSAPP_API_URL}/{waba_id}/"
            params = dict(
                access_token=settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN,
                fields="owner_business_info,on_behalf_of_business_info",
            )

            business_id = (
                requests.get(url, params=params, headers=headers)
                .json()
                .get("owner_business_info", {"id": None})
                .get("id")
            )

        return Response(dict(waba_id=waba_id, business_id=business_id))

    @action(detail=False, methods=["GET"])
    def phone_numbers(self, request: "Request", **kwargs):
        """
        Returns a list of phone numbers for a given WABA Id.

            Query Parameters:
                - input_token (str): User Facebook Access Token
                - waba_id (str): WhatsApp Business Account Id

            Return body:
            [
                {
                    "phone_number": "",
                    "phone_number_id": ""
                },
            ]
        """

        waba_id = request.query_params.get("waba_id", None)

        if waba_id is None:
            raise ValidationError("waba_id is a required parameter!")

        request = PhoneNumbersRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        try:
            return Response(request.get_phone_numbers(waba_id))
        except FacebookApiException as error:
            raise ValidationError(error)

    @action(detail=True, methods=["PATCH"])
    def update_webhook(self, request, uuid=None):
        """
        This method updates the flows config with the new  [webhook] information,
        if the update is successful, the webhook is updated in integrations,
        otherwise an exception will occur.
        """

        try:
            flows_client = FlowsClient()

            app = self.get_object()
            config = request.data["config"]

            detail_channel = flows_client.detail_channel(app.flow_object_uuid)

            flows_config = detail_channel["config"]
            updated_config = flows_config
            updated_config["webhook"] = config["webhook"]

            response = flows_client.update_config(
                data=updated_config, flow_object_uuid=app.flow_object_uuid
            )
            response.raise_for_status()

        except KeyError as exception:
            # Handle missing keys
            raise APIException(
                detail=f"Missing key: {str(exception)}", code=400
            ) from exception

        app.config["webhook"] = config["webhook"]
        app.save()

        serializer = self.get_serializer(app)
        return Response(serializer.data)

    @action(detail=True, methods=["GET"])
    def report_sent_messages(self, request: "Request", **kwargs):
        project_uuid = request.query_params.get("project_uuid", None)
        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)
        user = request.user.email

        if project_uuid is None:
            raise ValidationError("project_uuid is a required parameter")

        if start_date is None:
            raise ValidationError("start_date is a required parameter")

        if end_date is None:
            raise ValidationError("end_date is a required parameter")

        client = FlowsClient()
        response = client.get_sent_messagers(
            end_date=end_date,
            project_uuid=project_uuid,
            start_date=start_date,
            user=user,
        )

        return Response(status=response.status_code)


class CatalogViewSet(viewsets.ViewSet):
    serializer_class = CatalogSerializer

    def create(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        business_id = app.config.get("wa_business_id")
        category = request.data.get("category")

        if business_id is None:
            raise ValidationError(
                "The app does not have a business id on [config.wa_business_id]"
            )

        client = FacebookClient()
        response = client.create_catalog(business_id, name, category)

        if response:
            facebook_catalog_id = response.get("id")
            try:
                catalog = Catalog.objects.create(
                    app=app,
                    facebook_catalog_id=facebook_catalog_id,
                    name=name,
                    created_by=self.request.user,
                )
                if "catalogs" not in app.config:
                    app.config["catalogs"] = []

                app.config["catalogs"].append(
                    {"facebook_catalog_id": facebook_catalog_id}
                )
                app.save()

                flows_client = FlowsClient()
                detail_channel = flows_client.detail_channel(app.flow_object_uuid)

                flows_config = detail_channel["config"]
                flows_config["catalogs"] = app.config["catalogs"]

                response = flows_client.update_config(
                    data=flows_config, flow_object_uuid=app.flow_object_uuid
                )

                serializer = CatalogSerializer(catalog)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = get_object_or_404(Catalog, uuid=catalog_uuid, app__uuid=app_uuid)
        serializer = self.serializer_class(catalog)
        return Response(serializer.data)

    def list(self, request, app_uuid, *args, **kwargs):
        catalogs = Catalog.objects.filter(app__uuid=app_uuid)
        serializer = self.serializer_class(catalogs, many=True)
        return Response(serializer.data)

    def destroy(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = get_object_or_404(Catalog, uuid=catalog_uuid, app__uuid=app_uuid)

        client = FacebookClient()

        is_deleted = client.destroy_catalog(catalog.facebook_catalog_id)

        if is_deleted:
            if "catalogs" in catalog.app.config:
                catalogs_to_remove = []

                for idx, catalog_entry in enumerate(catalog.app.config["catalogs"]):
                    if (
                        catalog_entry.get("facebook_catalog_id")
                        == catalog.facebook_catalog_id
                    ):
                        catalogs_to_remove.append(idx)

                # Remove backwards to avoid indexing issues
                for idx in reversed(catalogs_to_remove):
                    del catalog.app.config["catalogs"][idx]
                catalog.app.save()

                # Update the Flows config after modifying the app config
                flows_client = FlowsClient()
                detail_channel = flows_client.detail_channel(
                    catalog.app.flow_object_uuid
                )
                flows_config = detail_channel["config"]
                flows_config["catalogs"] = catalog.app.config["catalogs"]

                flows_client.update_config(
                    data=flows_config, flow_object_uuid=catalog.app.flow_object_uuid
                )

            catalog.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"detail": "Failed to delete catalog on Facebook"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"])
    def list_products(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = get_object_or_404(Catalog, uuid=catalog_uuid, app__uuid=app_uuid)
        products = Product.objects.filter(catalog=catalog)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductFeedViewSet(viewsets.ViewSet):
    serializer_class = ProductFeedSerializer

    def create(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = get_object_or_404(Catalog, uuid=catalog_uuid, app__uuid=app_uuid)

        file_uploaded = request.FILES.get("file")
        name = request.data.get("name")

        if file_uploaded is None:
            return Response(
                {"error": "No file was uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        client = FacebookClient()
        response = client.create_product_feed(
            product_catalog_id=catalog.facebook_catalog_id, name=name
        )

        if "id" not in response:
            return Response(
                {"error": "Unexpected response from Facebook API", "details": response},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        product_feed = ProductFeed.objects.create(
            facebook_feed_id=response["id"],
            name=name,
            catalog=catalog,
            created_by=self.request.user,
        )
        response = client.upload_product_feed(
            feed_id=product_feed.facebook_feed_id, file=file_uploaded
        )
        serializer = ProductFeedSerializer(product_feed)
        data = serializer.data.copy()
        if "id" not in response:
            return Response(
                {"error": "The file couldn't be sent. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data["facebook_session_upload_id"] = response["id"]
        file_uploaded.seek(0)

        parser = ProductFeedParser(file_uploaded)
        file_products = parser.parse_as_dict()

        if file_products is {}:
            return Response(
                {"error": "Error on parse uploaded file to dict"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        kwargs = dict(
            product_feed_uuid=product_feed.uuid,
            file_products=file_products,
            user_email=self.request.user.email,
        )
        if file_products:
            celery_app.send_task(name="create_products_by_feed", kwargs=kwargs)

        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, app_uuid, catalog_uuid, feed_uuid, *args, **kwargs):
        product_feed = get_object_or_404(
            ProductFeed, uuid=feed_uuid, catalog__uuid=catalog_uuid
        )
        serializer = self.serializer_class(product_feed)
        return Response(serializer.data)

    def list(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        product_feeds = ProductFeed.objects.filter(catalog__uuid=catalog_uuid)
        serializer = self.serializer_class(product_feeds, many=True)
        return Response(serializer.data)

    def destroy(self, request, app_uuid, catalog_uuid, feed_uuid, *args, **kwargs):
        product_feed = get_object_or_404(
            ProductFeed, uuid=feed_uuid, catalog__uuid=catalog_uuid
        )

        client = FacebookClient()

        is_deleted = client.destroy_feed(product_feed.facebook_feed_id)

        if is_deleted:
            product_feed.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"detail": "Failed to delete feed on Facebook"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"])
    def list_products(
        self, request, app_uuid, catalog_uuid, feed_uuid, *args, **kwargs
    ):
        product_feed = get_object_or_404(
            ProductFeed, uuid=feed_uuid, catalog__uuid=catalog_uuid
        )
        products = Product.objects.filter(feed=product_feed, catalog__uuid=catalog_uuid)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
