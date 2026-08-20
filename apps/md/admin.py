from django.contrib import admin

from .models import Markdown


@admin.register(Markdown)
class MarkdownAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "created_at")
    list_filter = ("status", "project")
    readonly_fields = ("status", "error")
    exclude = ("embedding",)
