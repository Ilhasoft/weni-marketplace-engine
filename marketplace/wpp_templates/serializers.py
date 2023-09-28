import requests
import re
import base64
from datetime import datetime

from django.core.exceptions import ValidationError

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import serializers

from marketplace.applications.models import App

from .models import TemplateMessage, TemplateTranslation, TemplateButton, TemplateHeader
from .requests import TemplateMessageRequest
from marketplace.core.types.channels.whatsapp_cloud.requests import PhotoAPIRequest
from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)

WHATSAPP_VERSION = settings.WHATSAPP_VERSION

User = get_user_model()


class HeaderSerializer(serializers.ModelSerializer):
    text = serializers.CharField(required=False)
    example = serializers.CharField(required=False)

    class Meta:
        model = TemplateHeader
        fields = ["header_type", "text", "example"]


class ButtonSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    url = serializers.CharField(required=False)

    otp_type = serializers.ChoiceField(
        choices=[("COPY_CODE", "COPY_CODE"), ("ONE_TAP", "ONE_TAP")], required=False
    )
    package_name = serializers.CharField(required=False)
    signature_hash = serializers.CharField(required=False)
    autofill_text = serializers.CharField(required=False)

    class Meta:
        model = TemplateButton
        fields = [
            "button_type",
            "text",
            "country_code",
            "phone_number",
            "url",
            "otp_type",
            "package_name",
            "signature_hash",
            "autofill_text",
        ]


class TemplateTranslationSerializer(serializers.Serializer):
    template_uuid = serializers.CharField(write_only=True)
    uuid = serializers.UUIDField(read_only=True)
    message_template_id = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    language = serializers.CharField()
    country = serializers.CharField(required=False)
    header = HeaderSerializer(required=False)
    body = serializers.JSONField(required=False)
    footer = serializers.JSONField(required=False)
    buttons = ButtonSerializer(many=True, required=False)
    variable_count = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.headers.first():
            data["header"] = instance.headers.first().to_dict()
        return data

    def append_to_components(self, components: list() = [], component=None):
        if component:
            components.append(dict(component))

        return components

    def create(self, validated_data: dict) -> None:
        template = TemplateMessage.objects.get(uuid=validated_data.get("template_uuid"))

        if template.app.code == "wpp":
            access_token = template.app.config.get("fb_access_token", None)

            if access_token is None:
                raise ValidationError(
                    f"This app: {template.app.uuid} does not have fb_access_token in config"
                )
        else:
            access_token = settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN

        template_message_request = TemplateMessageRequest(access_token=access_token)
        components = [validated_data.get("body", {})]
        header = validated_data.get("header")

        if header:
            header = dict(header)
            header["type"] = "HEADER"
            header["format"] = header.get("header_type", "TEXT")
            header.pop("header_type")

            if (
                header.get("format") == "IMAGE"
                or header.get("format") == "DOCUMENT"
                or header.get("format") == "VIDEO"
            ):
                photo_api_request = PhotoAPIRequest(
                    template.app.config.get("wa_waba_id")
                )
                photo = header.get("example")
                file_type = re.search("(?<=data:)(.*)(?=;base64)", photo).group(0)
                photo = photo.split(";base64,")[1]
                upload_session_id = photo_api_request.create_upload_session(
                    access_token,
                    len(base64.b64decode(photo)),
                    file_type=file_type,
                )

                url = (
                    f"https://graph.facebook.com/{WHATSAPP_VERSION}/{upload_session_id}"
                )
                headers = {
                    "Content-Type": file_type,
                    "Authorization": f"OAuth {access_token}",
                }
                headers["file_offset"] = "0"
                response = requests.post(
                    url, headers=headers, data=base64.b64decode(photo)
                )

                if response.status_code != 200:
                    raise FacebookApiException(response.json())

                upload_handle = response.json().get("h", "")
                header.pop("example")
                header["example"] = dict(header_handle=upload_handle)

        components = self.append_to_components(components, header)
        components = self.append_to_components(components, validated_data.get("footer"))
        buttons = validated_data.get("buttons", {})

        buttons_component = {
            "type": "BUTTONS",
            "buttons": [],
        }

        for button in buttons:
            button = dict(button)

            # Specific treatment for "OTP" type buttons in the "AUTHENTICATION" category
            if (
                template.category == "AUTHENTICATION"
                and button.get("button_type") == "OTP"
            ):
                button["type"] = "OTP"
                if button.get("otp_type") == "COPY_CODE":
                    button = {
                        "type": "OTP",
                        "otp_type": "COPY_CODE",
                    }

                elif button.get("otp_type") == "ONE_TAP":
                    if not all(k in button for k in ["package_name", "signature_hash"]):
                        raise ValidationError(
                            "For ONE_TAP buttons, 'package_name' and 'signature_hash' are required."
                        )

                    autofill = button.get("autofill_text")
                    button = {
                        "type": "OTP",
                        "otp_type": "ONE_TAP",
                        "package_name": button.get("package_name"),
                        "signature_hash": button.get("signature_hash"),
                    }

                    # Only add autofill_text if it's provided
                    if autofill:
                        button["autofill_text"] = autofill

            else:
                if button.get("phone_number"):
                    button[
                        "phone_number"
                    ] = f'+{button.get("country_code")} {button.get("phone_number")}'
                button["type"] = button.get("button_type")
                button.pop("button_type", None)
                if button.get("country_code"):
                    button.pop("country_code")

            buttons_component.get("buttons").append(button)

        if buttons_component.get("buttons"):
            components = self.append_to_components(components, buttons_component)

        waba_id = (
            template.app.config.get("wa_waba_id")
            if template.app.config.get("wa_waba_id")
            else template.app.config.get("waba").get("id")
        )

        new_template = template_message_request.create_template_message(
            waba_id=waba_id,
            name=template.name,
            category=template.category,
            components=components,
            language=validated_data.get("language"),
        )

        translation = TemplateTranslation.objects.create(
            template=template,
            status="PENDING",
            body=validated_data.get("body", {}).get("text", ""),
            footer=validated_data.get("footer", {}).get("text", ""),
            language=validated_data.get("language"),
            country=validated_data.get("country", "Brasil"),
            variable_count=0,
            message_template_id=new_template["id"],
        )

        for button in buttons:
            button = dict(button)
            TemplateButton.objects.create(translation=translation, **button)

        if validated_data.get("header"):
            hh = dict(validated_data.get("header"))
            if hh.get("example"):
                hh.pop("example")
            TemplateHeader.objects.create(translation=translation, **hh)

        return translation


class TemplateMessageSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    created_on = serializers.CharField(read_only=True)
    category = serializers.CharField()
    app_uuid = serializers.CharField(write_only=True)
    text_preview = serializers.CharField(required=False, read_only=True)
    translations = TemplateTranslationSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.translations.first():
            data["text_preview"] = instance.translations.first().body
        return data

    def create(self, validated_data: dict) -> TemplateMessage:
        app = App.objects.get(uuid=validated_data.get("app_uuid"))

        template_message = TemplateMessage(
            name=validated_data.get("name"),
            app=app,
            category=validated_data.get("category"),
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        try:
            template_message.full_clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        template_message.save()
        return template_message
