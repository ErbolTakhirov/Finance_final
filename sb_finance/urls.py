from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from finance import web_views as finance_web
from goals import web_views as goals_web

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('api/finance/', include('finance.urls')),
    path('api/goals/', include('goals.urls')),
    path('api/ai/', include('ai.urls')),
    path('accounts/', include('accounts.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

