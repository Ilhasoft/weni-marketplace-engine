from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from .models import TemplateMessage
from .serializers import TemplateMessageSerializer, TemplateTranslationCreateSerializer, TemplateQuerySetSerializer
from .requests import TemplateMessageRequest
from .languages import LANGUAGES

User = get_user_model()


class CustomResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 500


class TemplateMessageViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    serializer_class = TemplateMessageSerializer
    pagination_class = CustomResultsPagination

    def get_queryset(self):
        serializer = TemplateQuerySetSerializer(self.request.query_params.dict())
        queryset = TemplateMessage.objects.filter(**serializer.data).order_by("created_by")

        return queryset

    def perform_destroy(self, instance):
        template_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        template_request.delete_template_message(waba_id=instance.config.get("waba_id"), name=instance.name)

        instance.delete()

    @action(detail=True, methods=["POST"])
    def translations(self, request, uuid):
        request.data["template_uuid"] = uuid

        serializer = TemplateTranslationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"])
    def languages(self, request):
        return Response(data=LANGUAGES, status=status.HTTP_200_OK)
