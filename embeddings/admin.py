from django.contrib import admin

from .models import Chunk, Markdown, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Markdown)
class MarkdownAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "created_at")
    list_filter = ("status", "project")
    readonly_fields = ("status", "error")


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ("markdown", "index")
    exclude = ("embedding",)
