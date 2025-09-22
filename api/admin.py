from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.core.cache import cache
from django.contrib import messages

class GitlabAdminSite(admin.AdminSite):
    site_header = 'Gerador de Métricas GitLab - Administração'
    site_title = 'Administração GitLab'
    index_title = 'Painel de Controle'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('clear-cache/', self.admin_view(self.clear_cache_view), name='clear-cache'),
        ]
        return custom_urls + urls

    def clear_cache_view(self, request):
        """View para limpar o cache"""
        cache.clear()
        messages.success(request, 'Cache limpo com sucesso!')
        return HttpResponseRedirect('../')

# Adicionar um link para limpar cache no index do admin
admin.site.index_template = 'admin/custom_index.html'