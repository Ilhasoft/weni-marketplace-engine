from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.wpp_products.models import Catalog, Product


# TODO: Remove unnecessary serializers
class WhatsAppCloudSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = (
            "code",
            "uuid",
            "project_uuid",
            "platform",
            "config",
            "created_by",
            "created_on",
            "modified_by",
        )
        read_only_fields = ("code", "uuid", "platform")

        # TODO: Validate fields


class WhatsAppCloudConfigureSerializer(serializers.Serializer):
    input_token = serializers.CharField(required=True)
    waba_id = serializers.CharField(required=True)
    phone_number_id = serializers.CharField(required=True)
    business_id = serializers.CharField(required=True)


class CatalogSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    facebook_catalog_id = serializers.CharField(read_only=True)

    class Meta:
        model = Catalog
        fields = ("uuid", "name", "facebook_catalog_id")


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "uuid",
            "title ",
            "facebook_product_id ",
            "product_retailer_id ",
            "catalog",
        )
