from django.urls import path, include
#from rest_framework import routers
from rest_framework_nested import routers

from marketplace.wpp_templates import views

router = routers.SimpleRouter()
router.register("apps", views.AppsViewSet, basename="apps")

templates_router = routers.NestedSimpleRouter(router, r"apps", lookup="app")
templates_router.register("templates", views.TemplateMessageViewSet, basename="app-template")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(templates_router.urls)),
]
