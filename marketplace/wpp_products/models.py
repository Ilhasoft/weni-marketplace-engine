from django.db import models
from marketplace.core.models import BaseModel
from marketplace.applications.models import App
from django.core.exceptions import ValidationError


class Catalog(BaseModel):
    facebook_catalog_id = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="catalogs")

    def __str__(self):
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.app.code != "wpp-cloud":
            raise ValidationError("The App must be a 'WhatsApp Cloud' AppType.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Product(BaseModel):
    facebook_product_id = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=200)
    product_retailer_id = models.CharField(max_length=50)
    catalog = models.ForeignKey(
        Catalog, on_delete=models.CASCADE, related_name="products"
    )

    def __str__(self):
        return self.title
