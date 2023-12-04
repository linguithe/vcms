from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("api/", include(("vcmsapp.urls", "vcmsapp"), namespace="vcmsapp")),
    path('admin/', admin.site.urls)
]
