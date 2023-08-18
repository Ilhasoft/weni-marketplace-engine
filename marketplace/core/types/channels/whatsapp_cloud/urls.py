from django.urls import path

from .views import CatalogViewSet


urlpatterns = [
    path(
        "<uuid:app_uuid>/catalogs/",
        CatalogViewSet.as_view({"post": "create", "get": "list"}),
        name="catalog-list-create",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/",
        CatalogViewSet.as_view({"get": "retrieve"}),
        name="catalog-detail",
    ),
]
