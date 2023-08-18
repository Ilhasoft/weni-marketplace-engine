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


class ProductFeed(BaseModel):
    facebook_feed_id = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="feeds")
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("error", "Error"), ("success", "Success")],
        default="pending",
    )

    def __str__(self):
        return self.name


class Product(BaseModel):
    AVAILABILITY_CHOICES = [("in stock", "in stock"), ("out of stock", "out of stock")]
    CONDITION_CHOICES = [
        ("new", "new"),
        ("refurbished", "refurbished"),
        ("used", "used"),
    ]
    facebook_product_id = models.CharField(max_length=30, unique=True)
    product_retailer_id = models.CharField(max_length=50)
    # facebook required fields
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=9999)
    availability = models.CharField(max_length=12, choices=AVAILABILITY_CHOICES)
    condition = models.CharField(max_length=11, choices=CONDITION_CHOICES)
    price = models.CharField(max_length=50)  # Example: "9.99 USD"
    link = models.URLField()
    image_link = models.URLField()
    brand = models.CharField(max_length=100)

    catalog = models.ForeignKey(
        Catalog, on_delete=models.CASCADE, related_name="products"
    )
    feed = models.ForeignKey(
        ProductFeed,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title
