from django.contrib import admin

from .models import Markdown, PolicySelection


@admin.register(Markdown)
class MarkdownAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "created_at")
    list_filter = ("status", "project")
    readonly_fields = ("status", "error")
    exclude = ("embedding",)


@admin.register(PolicySelection)
class PolicySelectionAdmin(admin.ModelAdmin):
    list_display = ("markdown", "policy", "created_at")
    list_filter = ("policy",)
    readonly_fields = ("markdown", "policy", "error", "created_at")
