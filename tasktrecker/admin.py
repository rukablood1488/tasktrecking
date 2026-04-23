from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count

from .models import (
    Workspace, WorkspaceMember,
    Project, TaskList,
    Task, Comment, Tag, TaskActivity,
)




class WorkspaceMemberInline(admin.TabularInline):
    
    model = WorkspaceMember
    extra = 1          # кількість порожніх рядків для додавання нових учасників
    autocomplete_fields = ["user"] 


class TaskListInline(admin.TabularInline):
    
    model = TaskList
    extra = 1
    fields = ["name", "description", "position"]


class SubtaskInline(admin.TabularInline):
    
    model = Task
    fk_name = "parent_task"
    extra = 0
    fields = ["title", "status", "priority", "assignees"]
    readonly_fields = ["assignees"]
    verbose_name = "Підзавдання"
    verbose_name_plural = "Підзавдання"
    show_change_link = True  


class CommentInline(admin.StackedInline):

    model = Comment
    extra = 0
    readonly_fields = ["author", "created_at", "is_edited"]
    fields = ["author", "content", "is_edited", "created_at"]


class TaskActivityInline(admin.TabularInline):
    
    model = TaskActivity
    extra = 0
    readonly_fields = ["user", "activity_type", "old_value", "new_value", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False






@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "member_count", "project_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "owner__username", "owner__email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WorkspaceMemberInline]


    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            _member_count=Count("members", distinct=True),
            _project_count=Count("projects", distinct=True),
        )

    @admin.display(description="Учасників", ordering="_member_count")
    def member_count(self, obj):
        return obj._member_count

    @admin.display(description="Проектів", ordering="_project_count")
    def project_count(self, obj):
        return obj._project_count







@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "colored_name", "workspace", "created_by",
        "task_count", "is_archived", "created_at",
    ]
    list_filter = ["is_archived", "workspace", "color"]
    search_fields = ["name", "workspace__name"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["is_archived"]
    inlines = [TaskListInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _task_count=Count("task_lists__tasks", distinct=True)
        )

    @admin.display(description="Назва проекту")
    def colored_name(self, obj):
        return format_html(
            '<span style="color: {}; font-weight: 600;">{} {}</span>',
            obj.color,
            obj.icon,
            obj.name,
        )

    @admin.display(description="Завдань", ordering="_task_count")
    def task_count(self, obj):
        return obj._task_count







@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        "title", "status_badge", "priority_badge",
        "task_list", "assignees_list",
        "due_date", "is_overdue_display", "created_at",
    ]
    list_filter = ["status", "priority", "is_archived", "task_list__project__workspace"]
    search_fields = ["title", "description", "created_by__username"]
    readonly_fields = ["created_at", "updated_at", "completed_at"]
    filter_horizontal = ["assignees", "tags"] 
    date_hierarchy = "created_at"              # навігація по датах
    inlines = [SubtaskInline, CommentInline, TaskActivityInline]

    # групування полів у секції на сторінці редагування
    fieldsets = (
        ("Основне", {
            "fields": ("title", "description", "task_list", "parent_task")
        }),
        ("Статус та пріоритет", {
            "fields": ("status", "priority", "is_archived")
        }),
        ("Терміни", {
            "fields": ("start_date", "due_date", "estimated_hours", "completed_at")
        }),
        ("Учасники та теги", {
            "fields": ("assignees", "tags", "created_by")
        }),
        ("Мета-дані", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    
    STATUS_COLORS = {
        "todo":        ("#6c757d"),
        "in_progress": ("#0d6efd"),
        "in_review":   ("#fd7e14"),
        "done":        ("#198754"),
        "cancelled":   ("#dc3545"),
    }

    PRIORITY_COLORS = {
        "urgent":      "#dc3545",
        "high":        "#fd7e14",
        "normal":      "#0d6efd",
        "low":         "#6c757d",
        "no_priority": "#adb5bd",
    }

    @admin.display(description="Статус")
    def status_badge(self, obj):
        color, icon = self.STATUS_COLORS.get(obj.status, ("#000", ""))
        return format_html(
            '<span style="color: {}; font-weight: 500;">{} {}</span>',
            color, icon, obj.get_status_display(),
        )

    @admin.display(description="Пріоритет")
    def priority_badge(self, obj):
        color = self.PRIORITY_COLORS.get(obj.priority, "#000")
        return format_html(
            '<span style="color: {}; font-weight: 500;">● {}</span>',
            color, obj.get_priority_display(),
        )

    @admin.display(description="Виконавці")
    def assignees_list(self, obj):
        names = [u.get_full_name() or u.username for u in obj.assignees.all()]
        return ", ".join(names) if names else "—"

    @admin.display(description="Прострочено", boolean=True)
    def is_overdue_display(self, obj):
        return obj.is_overdue







@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["short_content", "author", "task", "is_edited", "created_at"]
    list_filter = ["is_edited", "created_at"]
    search_fields = ["content", "author__username", "task__title"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Коментар")
    def short_content(self, obj):
        return obj.content[:60] + "..." if len(obj.content) > 60 else obj.content







@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["colored_tag", "workspace", "task_count"]
    search_fields = ["name", "workspace__name"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _task_count=Count("tasks", distinct=True)
        )

    @admin.display(description="Тег")
    def colored_tag(self, obj):
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 10px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            obj.color, obj.name,
        )

    @admin.display(description="Завдань", ordering="_task_count")
    def task_count(self, obj):
        return obj._task_count





@admin.register(TaskActivity)
class TaskActivityAdmin(admin.ModelAdmin):
    list_display = ["task", "user", "activity_type", "old_value", "new_value", "created_at"]
    list_filter = ["activity_type", "created_at"]
    search_fields = ["task__title", "user__username"]
    readonly_fields = ["task", "user", "activity_type", "old_value", "new_value", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False