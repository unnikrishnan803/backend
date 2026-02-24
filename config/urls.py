from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse

def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/game/", include("apps.game.urls")),
    path("healthz", health_check),
]
