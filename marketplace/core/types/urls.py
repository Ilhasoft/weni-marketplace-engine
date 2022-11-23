from django.urls import path, include
from rest_framework_nested import routers

from marketplace.core import types
from marketplace.core.types.channels.generic.views import DetailChannels

urlpatterns = []


for apptype in types.APPTYPES.values():
    router = routers.SimpleRouter()
    if apptype.view_class is None:
        continue


    router.register("apps", apptype.view_class, basename=f"{apptype.code}-app")
    urlpatterns.append(path(f"apptypes/{apptype.code}/", include(router.urls)))

router.register("detail-channel", DetailChannels, basename="detail-channel" )
urlpatterns.append(path("apptypes/generic/", include(router.urls)))
