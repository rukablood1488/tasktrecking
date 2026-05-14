from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q, Count, OuterRef, Subquery
from django.utils import timezone
from django.contrib import messages
from django.views.generic import TemplateView

from .models import Workspace, WorkspaceMember, Project, TaskList, Task, Comment, Tag, TaskActivity
from . import notifications as notif

from .mixins import (
    WorkspaceMemberMixin,
    WorkspaceAdminMixin,
    TaskOwnerOrAdminMixin,
    CommentAuthorOrAdminMixin,
)

# Auth ──────────────────────────────────────────────────────


class RegisterView(View):
    template_name = "auth/register.html"

    def get(self, request):
        from django.shortcuts import render
        from .forms import RegisterForm
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        from django.shortcuts import render
        from .forms import RegisterForm
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Ласкаво просимо, {user.username}!")
            return redirect("workspace-list")
        return render(request, self.template_name, {"form": form})


class CustomLoginView(LoginView):
    template_name = "auth/login.html"
    redirect_authenticated_user = True

    def get_form_class(self):
        from .forms import CustomLoginForm
        return CustomLoginForm

    def get_success_url(self):
        return reverse_lazy("workspace-list")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("login")


# Workspace ─────────────────────────────────────────────────


class WorkspaceListView(LoginRequiredMixin, ListView):
    model = Workspace
    template_name = "workspaces/list.html"
    context_object_name = "workspaces"

    def get_queryset(self):
        member_count_sq = WorkspaceMember.objects.filter(
            workspace=OuterRef("pk")
        ).values("workspace").annotate(cnt=Count("pk")).values("cnt")

        return Workspace.objects.filter(
            members=self.request.user
        ).annotate(
            project_count=Count("projects", distinct=True),
            member_count=Subquery(member_count_sq),
        ).order_by("-created_at")


class WorkspaceCreateView(LoginRequiredMixin, CreateView):
    model = Workspace
    template_name = "workspaces/form.html"

    def get_form_class(self):
        from .forms import WorkspaceForm
        return WorkspaceForm

    def form_valid(self, form):
        workspace = form.save(commit=False)
        workspace.owner = self.request.user
        workspace.save()
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.request.user,
            role=WorkspaceMember.Role.OWNER
        )
        messages.success(self.request, f"Простір «{workspace.name}» створено!")
        return redirect(workspace.get_absolute_url())


class WorkspaceDetailView(WorkspaceMemberMixin, DetailView):
    model = Workspace
    template_name = "workspaces/detail.html"
    context_object_name = "workspace"

    def get_workspace(self):
        self.kwargs.setdefault("workspace_pk", self.kwargs.get("pk"))
        return get_object_or_404(Workspace, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = self.object.projects.filter(
            is_archived=False
        ).annotate(task_count=Count("task_lists__tasks"))
        ctx["members"] = WorkspaceMember.objects.filter(
            workspace=self.object
        ).select_related("user")
        try:
            member = WorkspaceMember.objects.get(
                workspace=self.object, user=self.request.user
            )
            ctx["user_role"] = member.role
        except WorkspaceMember.DoesNotExist:
            if self.object.owner == self.request.user:
                WorkspaceMember.objects.create(
                    workspace=self.object,
                    user=self.request.user,
                    role=WorkspaceMember.Role.OWNER,
                )
                ctx["user_role"] = WorkspaceMember.Role.OWNER
            else:
                ctx["user_role"] = None
        return ctx


class WorkspaceUpdateView(WorkspaceAdminMixin, UpdateView):
    model = Workspace
    template_name = "workspaces/form.html"

    def get_form_class(self):
        from .forms import WorkspaceForm
        return WorkspaceForm

    def get_workspace(self):
        self.kwargs.setdefault("workspace_pk", self.kwargs.get("pk"))
        return get_object_or_404(Workspace, pk=self.kwargs["pk"])


class WorkspaceDeleteView(LoginRequiredMixin, DeleteView):
    model = Workspace
    template_name = "workspaces/confirm_delete.html"
    success_url = reverse_lazy("workspace-list")

    def dispatch(self, request, *args, **kwargs):
        workspace = self.get_object()
        if workspace.owner != request.user:
            messages.error(request, "Видалити простір може лише його власник.")
            return redirect(reverse("workspace-detail", kwargs={"pk": workspace.pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Простір видалено.")
        return super().form_valid(form)


# Project ───────────────────────────────────────────────────


class ProjectCreateView(WorkspaceMemberMixin, CreateView):
    model = Project
    template_name = "projects/form.html"

    def get_form_class(self):
        from .forms import ProjectForm
        return ProjectForm

    def form_valid(self, form):
        project = form.save(commit=False)
        project.workspace = self.get_workspace()
        project.created_by = self.request.user
        project.save()
        TaskList.objects.create(project=project, name="Загальний", position=0)
        messages.success(self.request, f"Проект «{project.name}» створено!")
        return redirect(project.get_absolute_url())


class ProjectDetailView(WorkspaceMemberMixin, DetailView):
    model = Project
    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_workspace(self):
        project = get_object_or_404(Project, pk=self.kwargs["pk"])
        self.kwargs["workspace_pk"] = project.workspace.pk
        return project.workspace

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        task_lists = self.object.task_lists.prefetch_related(
            "tasks__assignees", "tasks__tags"
        ).all()
        ctx["task_lists"] = task_lists
        ctx["status_choices"] = Task.Status.choices
        ctx["priority_choices"] = Task.Priority.choices
        all_tasks = Task.objects.filter(task_list__project=self.object)
        ctx["stats"] = {
            "total": all_tasks.count(),
            "done": all_tasks.filter(status=Task.Status.DONE).count(),
            "in_progress": all_tasks.filter(status=Task.Status.IN_PROGRESS).count(),
            "overdue": sum(1 for t in all_tasks if t.is_overdue),
        }
        return ctx


class ProjectUpdateView(WorkspaceAdminMixin, UpdateView):
    model = Project
    template_name = "projects/form.html"

    def get_form_class(self):
        from .forms import ProjectForm
        return ProjectForm

    def get_workspace(self):
        project = get_object_or_404(Project, pk=self.kwargs["pk"])
        self.kwargs["workspace_pk"] = project.workspace.pk
        return project.workspace

    def form_valid(self, form):
        project = self.get_object()
        response = super().form_valid(form)
        notif.notify_project_edited(self.object, self.request.user)
        return response


class ProjectDeleteView(WorkspaceAdminMixin, DeleteView):
    model = Project
    template_name = "projects/confirm_delete.html"

    def get_workspace(self):
        project = get_object_or_404(Project, pk=self.kwargs["pk"])
        self.kwargs["workspace_pk"] = project.workspace.pk
        return project.workspace

    def get_success_url(self):
        return reverse("workspace-detail", kwargs={"pk": self.object.workspace.pk})

    def form_valid(self, form):
        notif.notify_project_deleted(self.object, self.request.user)
        return super().form_valid(form)


# Task ──────────────────────────────────────────────────────


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/list.html"
    context_object_name = "tasks"
    paginate_by = 25

    def get_queryset(self):
        search     = self.request.GET.get("q", "").strip()
        status     = self.request.GET.get("status")
        priority   = self.request.GET.get("priority")
        assignee   = self.request.GET.get("assignee")
        due_date   = self.request.GET.get("due_date")
        project_id = self.request.GET.get("project")


        base_qs = Task.objects.filter(
            task_list__project__workspace__members=self.request.user,
            is_archived=False,
        ).filter(
            Q(created_by=self.request.user) | Q(assignees=self.request.user)
        ).distinct().select_related(
            "task_list__project", "created_by"
        ).prefetch_related("assignees", "tags")

        if search:
            return base_qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            ).order_by("parent_task_id", "position", "-created_at")


        qs = base_qs.filter(parent_task__isnull=True)

        if status:     qs = qs.filter(status=status)
        if priority:   qs = qs.filter(priority=priority)
        if assignee:   qs = qs.filter(assignees__id=assignee)
        if project_id: qs = qs.filter(task_list__project__id=project_id)

        if due_date == "overdue":
            qs = qs.filter(due_date__lt=timezone.now()).exclude(
                status__in=[Task.Status.DONE, Task.Status.CANCELLED]
            )
        elif due_date == "today":
            qs = qs.filter(due_date__date=timezone.now().date())
        elif due_date == "week":
            week_end = timezone.now() + timezone.timedelta(days=7)
            qs = qs.filter(due_date__lte=week_end, due_date__gte=timezone.now())

        return qs.order_by("position", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"]   = Task.Status.choices
        ctx["priority_choices"] = Task.Priority.choices
        ctx["current_filters"]  = self.request.GET
        search = self.request.GET.get("q", "").strip()
        ctx["is_search"] = bool(search)

        
        if not search:
            task_ids = [t.pk for t in ctx["tasks"]]
            subtasks = Task.objects.filter(
                parent_task_id__in=task_ids,
                is_archived=False,
            ).filter(
                Q(created_by=self.request.user) | Q(assignees=self.request.user)
            ).distinct().select_related(
                "task_list__project", "created_by"
            ).prefetch_related("assignees", "tags").order_by("position", "-created_at")

            subtasks_map = {}
            for subtask in subtasks:
                subtasks_map.setdefault(subtask.parent_task_id, []).append(subtask)
            ctx["subtasks_map"] = subtasks_map
        else:
            ctx["subtasks_map"] = {}

        return ctx


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.filter(
            task_list__project__workspace__members=self.request.user
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["comments"] = self.object.comments.filter(
            parent_comment__isnull=True
        ).select_related("author").prefetch_related("replies__author")
        ctx["subtasks"]         = self.object.subtasks.all().select_related("created_by")
        ctx["activities"]       = self.object.activities.select_related("user")[:20]
        ctx["status_choices"]   = Task.Status.choices
        ctx["priority_choices"] = Task.Priority.choices
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    template_name = "tasks/form.html"

    def get_task_list(self):
        return get_object_or_404(
            TaskList,
            pk=self.kwargs["list_pk"],
            project__workspace__members=self.request.user,
        )

    def get_form_class(self):
        from .forms import TaskForm
        return TaskForm

    def get_form(self, form_class=None):
        from .forms import TaskForm
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        return TaskForm(task_list=self.get_task_list(), **kwargs)

    def form_valid(self, form):
        task = form.save(commit=False)
        task.task_list   = self.get_task_list()
        task.created_by  = self.request.user
        task.save()
        form.save_m2m()
        TaskActivity.objects.create(
            task=task, user=self.request.user,
            activity_type=TaskActivity.ActivityType.CREATED,
            new_value=task.title,
        )
        messages.success(self.request, f"Завдання «{task.title}» створено!")
        return redirect(task.get_absolute_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["task_list"] = self.get_task_list()
        return ctx


class TaskUpdateView(TaskOwnerOrAdminMixin, UpdateView):
    model = Task
    form_class = None
    template_name = "tasks/form.html"

    def get_form_class(self):
        from .forms import TaskForm
        return TaskForm

    def get_form(self, form_class=None):
        from .forms import TaskForm
        task = self.get_object()
        form = TaskForm(
            task_list=task.task_list,
            instance=task,
            **( {"data": self.request.POST} if self.request.method == "POST" else {} )
        )
        if task.start_date:
            form.fields["start_date"].widget.attrs["value"] = \
                task.start_date.strftime("%Y-%m-%dT%H:%M")
        if task.due_date:
            form.fields["due_date"].widget.attrs["value"] = \
                task.due_date.strftime("%Y-%m-%dT%H:%M")
        return form

    def form_valid(self, form):
        old_task = Task.objects.get(pk=self.object.pk)
        response = super().form_valid(form)
        task = self.object

        if old_task.status != task.status:
            TaskActivity.objects.create(
                task=task, user=self.request.user,
                activity_type=TaskActivity.ActivityType.STATUS_CHANGED,
                old_value=old_task.get_status_display(),
                new_value=task.get_status_display(),
            )
            if task.status == Task.Status.DONE:
                task.completed_at = timezone.now()
                task.save(update_fields=["completed_at"])
            notif.notify_task_status_changed(
                task, self.request.user,
                old_task.get_status_display(),
                task.get_status_display(),
            )

        if old_task.priority != task.priority:
            TaskActivity.objects.create(
                task=task, user=self.request.user,
                activity_type=TaskActivity.ActivityType.PRIORITY_CHANGED,
                old_value=old_task.get_priority_display(),
                new_value=task.get_priority_display(),
            )

        notif.notify_task_edited(task, self.request.user)
        messages.success(self.request, "Завдання оновлено.")
        return response


class TaskDeleteView(TaskOwnerOrAdminMixin, DeleteView):
    model = Task
    template_name = "tasks/confirm_delete.html"

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.task_list.project.pk})

    def form_valid(self, form):
        notif.notify_task_deleted(self.object, self.request.user)
        messages.success(self.request, f"Завдання «{self.object.title}» видалено.")
        return super().form_valid(form)


class TaskStatusUpdateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        task = get_object_or_404(
            Task, pk=pk,
            task_list__project__workspace__members=request.user
        )
        new_status = request.POST.get("status")
        if new_status not in dict(Task.Status.choices):
            return JsonResponse({"error": "Невірний статус"}, status=400)

        old_status = task.status
        task.status = new_status
        if new_status == Task.Status.DONE:
            task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at", "updated_at"])

        TaskActivity.objects.create(
            task=task, user=request.user,
            activity_type=TaskActivity.ActivityType.STATUS_CHANGED,
            old_value=old_status,
            new_value=new_status,
        )
        notif.notify_task_status_changed(
            task, request.user,
            dict(Task.Status.choices).get(old_status, old_status),
            task.get_status_display(),
        )
        return JsonResponse({
            "success": True,
            "status": task.status,
            "status_display": task.get_status_display(),
        })
    
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True, 
                "status": task.status, 
                "status_display": task.get_status_display()
            })
    
   
        return redirect(request.META.get('HTTP_REFERER', '/'))


# Comments ──────────────────────────────────────────────────


# views.py

class CommentCreateView(LoginRequiredMixin, View):

    def post(self, request, task_pk):
        task = get_object_or_404(
            Task, pk=task_pk,
            task_list__project__workspace__members=request.user
        )
        content  = request.POST.get("content", "").strip()
        parent_id = request.POST.get("parent_comment")
        image = request.FILES.get("image")

        if not content and not image:
            messages.error(request, "Коментар не може бути порожнім (додайте текст або зображення).")
            return redirect(task.get_absolute_url() + "#comments")

        parent_comment = None
        if parent_id:
            parent_comment = get_object_or_404(Comment, pk=parent_id, task=task)

        comment = Comment.objects.create(
            task=task, author=request.user,
            content=content, parent_comment=parent_comment,
            image=image
        )
        
        TaskActivity.objects.create(
            task=task, user=request.user,
            activity_type=TaskActivity.ActivityType.COMMENTED,
        )
        # Сповіщення автору завдання про новий коментар
        notif.notify_task_commented(task, comment, request.user)
        # Сповіщення автору батьківського коментаря про відповідь
        if parent_comment:
            notif.notify_comment_replied(parent_comment, request.user, task)
        messages.success(request, "Коментар додано.")
        return redirect(task.get_absolute_url() + "#comments")


class CommentUpdateView(CommentAuthorOrAdminMixin, UpdateView):
    model = Comment
    template_name = "tasks/comment_form.html"

    def get_form_class(self):
        from .forms import CommentForm
        return CommentForm

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.is_edited = True
        comment.save()
        notif.notify_comment_edited(comment, self.request.user)
        return redirect(comment.task.get_absolute_url() + "#comments")


class CommentDeleteView(CommentAuthorOrAdminMixin, DeleteView):
    model = Comment
    template_name = "tasks/comment_confirm_delete.html"

    def form_valid(self, form):
        notif.notify_comment_deleted(self.object, self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.task.get_absolute_url() + "#comments"


# Tags ──────────────────────────────────────────────────────


class TagListView(WorkspaceMemberMixin, ListView):
    model = Tag
    template_name = "tags/list.html"
    context_object_name = "tags"

    def get_queryset(self):
        workspace = self.get_workspace()
        return Tag.objects.filter(workspace=workspace).annotate(
            task_count=Count("tasks")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["workspace"] = self.get_workspace()
        return ctx


class TagCreateView(WorkspaceMemberMixin, CreateView):
    model = Tag
    template_name = "tags/form.html"

    def get_form_class(self):
        from .forms import TagForm
        return TagForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["workspace"] = self.get_workspace()
        return ctx

    def form_valid(self, form):
        tag = form.save(commit=False)
        tag.workspace = self.get_workspace()
        tag.save()
        messages.success(self.request, f"Тег «{tag.name}» створено.")
        return redirect(reverse("tag-list", kwargs={"workspace_pk": tag.workspace.pk}))


# Landing ───────────────────────────────────────────────────


class LandingView(TemplateView):
    template_name = "landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("workspace-list")
        return super().dispatch(request, *args, **kwargs)