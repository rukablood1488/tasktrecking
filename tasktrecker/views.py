from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib import messages

from .models import Workspace, WorkspaceMember, Project, TaskList, Task, Comment, Tag, TaskActivity



#  Mixin`s ----------------------------------------------------------------------------------------------

class WorkspaceMemberMixin(LoginRequiredMixin):

    def get_workspace(self):
        return get_object_or_404(Workspace, pk=self.kwargs["workspace_pk"])

    def dispatch(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        is_member = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).exists()
        if not is_member:
            return HttpResponseForbidden("Ви не є учасником цього простору.")
        return super().dispatch(request, *args, **kwargs)


class WorkspaceAdminMixin(WorkspaceMemberMixin):

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if isinstance(response, HttpResponseForbidden):
            return response
        workspace = self.get_workspace()
        member = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        if not member:
            return HttpResponseForbidden("Потрібні права адміністратора.")
        return response


class TaskOwnerOrAdminMixin(LoginRequiredMixin):

    def get_task(self):
        return get_object_or_404(Task, pk=self.kwargs["pk"])

    def dispatch(self, request, *args, **kwargs):
        task = self.get_task()
        workspace = task.task_list.project.workspace
        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        is_creator = task.created_by == request.user
        if not (is_admin or is_creator):
            return HttpResponseForbidden("Недостатньо прав для цієї дії.")
        return super().dispatch(request, *args, **kwargs)



#  auth ---------------------------------------------------------------------------


class RegisterView(View):
    """Реєстрація нового користувача."""
    template_name = "auth/register.html"

    def get(self, request):
        from django.shortcuts import render
        form = UserCreationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        from django.shortcuts import render
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Ласкаво просимо, {user.username}!")
            return redirect("workspace-list")
        return render(request, self.template_name, {"form": form})


class CustomLoginView(LoginView):
    template_name = "auth/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("workspace-list")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("login")










class WorkspaceListView(LoginRequiredMixin, ListView):
    """Список усіх Workspace поточного користувача."""
    model = Workspace
    template_name = "workspaces/list.html"
    context_object_name = "workspaces"

    def get_queryset(self):
        return Workspace.objects.filter(
            members=self.request.user
        ).annotate(
            project_count=Count("projects", distinct=True),
            member_count=Count("members", distinct=True),
        ).order_by("-created_at")


class WorkspaceCreateView(LoginRequiredMixin, CreateView):
    model = Workspace
    template_name = "workspaces/form.html"
    fields = ["name", "description"]

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
        ctx["user_role"] = WorkspaceMember.objects.get(
            workspace=self.object, user=self.request.user
        ).role
        return ctx


class WorkspaceUpdateView(WorkspaceAdminMixin, UpdateView):
    model = Workspace
    template_name = "workspaces/form.html"
    fields = ["name", "description"]

    def get_workspace(self):
        self.kwargs.setdefault("workspace_pk", self.kwargs.get("pk"))
        return get_object_or_404(Workspace, pk=self.kwargs["pk"])


class WorkspaceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Workspace
    template_name = "workspaces/confirm_delete.html"
    success_url = reverse_lazy("workspace-list")

    def test_func(self):
        workspace = self.get_object()
        return workspace.owner == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Простір видалено.")
        return super().form_valid(form)









class ProjectCreateView(WorkspaceMemberMixin, CreateView):
    model = Project
    template_name = "projects/form.html"
    fields = ["name", "description", "color", "icon"]

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
    fields = ["name", "description", "color", "icon", "is_archived"]

    def get_workspace(self):
        project = get_object_or_404(Project, pk=self.kwargs["pk"])
        self.kwargs["workspace_pk"] = project.workspace.pk
        return project.workspace


class ProjectDeleteView(WorkspaceAdminMixin, DeleteView):
    model = Project
    template_name = "projects/confirm_delete.html"

    def get_workspace(self):
        project = get_object_or_404(Project, pk=self.kwargs["pk"])
        self.kwargs["workspace_pk"] = project.workspace.pk
        return project.workspace

    def get_success_url(self):
        return reverse("workspace-detail", kwargs={"pk": self.object.workspace.pk})










class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/list.html"
    context_object_name = "tasks"
    paginate_by = 25

    def get_queryset(self):
        qs = Task.objects.filter(
            task_list__project__workspace__members=self.request.user,
            is_archived=False,
            parent_task__isnull=True,
        ).select_related(
            "task_list__project", "created_by"
        ).prefetch_related("assignees", "tags")

        
        status = self.request.GET.get("status")
        priority = self.request.GET.get("priority")
        assignee = self.request.GET.get("assignee")
        due_date = self.request.GET.get("due_date")
        search = self.request.GET.get("q")
        project_id = self.request.GET.get("project")

        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if assignee:
            qs = qs.filter(assignees__id=assignee)
        if project_id:
            qs = qs.filter(task_list__project__id=project_id)
        if due_date == "overdue":
            qs = qs.filter(due_date__lt=timezone.now()).exclude(
                status__in=[Task.Status.DONE, Task.Status.CANCELLED]
            )
        elif due_date == "today":
            today = timezone.now().date()
            qs = qs.filter(due_date__date=today)
        elif due_date == "week":
            week_end = timezone.now() + timezone.timedelta(days=7)
            qs = qs.filter(due_date__lte=week_end, due_date__gte=timezone.now())
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Task.Status.choices
        ctx["priority_choices"] = Task.Priority.choices
        ctx["current_filters"] = self.request.GET
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
        ctx["subtasks"] = self.object.subtasks.all().select_related("created_by")
        ctx["activities"] = self.object.activities.select_related("user")[:20]
        ctx["status_choices"] = Task.Status.choices
        ctx["priority_choices"] = Task.Priority.choices
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    template_name = "tasks/form.html"
    fields = [
        "title", "description", "status", "priority",
        "due_date", "start_date", "estimated_hours",
        "assignees", "tags", "parent_task",
    ]

    def get_task_list(self):
        return get_object_or_404(TaskList, pk=self.kwargs["list_pk"])

    def form_valid(self, form):
        task = form.save(commit=False)
        task.task_list = self.get_task_list()
        task.created_by = self.request.user
        task.save()
        form.save_m2m()
        TaskActivity.objects.create(
            task=task,
            user=self.request.user,
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
    template_name = "tasks/form.html"
    fields = [
        "title", "description", "status", "priority",
        "due_date", "start_date", "estimated_hours",
        "assignees", "tags",
    ]

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


        if old_task.priority != task.priority:
            TaskActivity.objects.create(
                task=task, user=self.request.user,
                activity_type=TaskActivity.ActivityType.PRIORITY_CHANGED,
                old_value=old_task.get_priority_display(),
                new_value=task.get_priority_display(),
            )

        messages.success(self.request, "Завдання оновлено.")
        return response


class TaskDeleteView(TaskOwnerOrAdminMixin, DeleteView):
    model = Task
    template_name = "tasks/confirm_delete.html"

    def get_success_url(self):
        return reverse(
            "project-detail",
            kwargs={"pk": self.object.task_list.project.pk}
        )

    def form_valid(self, form):
        messages.success(self.request, f"Завдання «{self.object.title}» видалено.")
        return super().form_valid(form)


class TaskStatusUpdateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        task = get_object_or_404(
            Task,
            pk=pk,
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
        return JsonResponse({
            "success": True,
            "status": task.status,
            "status_display": task.get_status_display(),
        })









class CommentCreateView(LoginRequiredMixin, View):

    def post(self, request, task_pk):
        task = get_object_or_404(
            Task,
            pk=task_pk,
            task_list__project__workspace__members=request.user
        )
        content = request.POST.get("content", "").strip()
        parent_id = request.POST.get("parent_comment")

        if not content:
            messages.error(request, "Коментар не може бути порожнім.")
            return redirect(task.get_absolute_url())

        parent_comment = None
        if parent_id:
            parent_comment = get_object_or_404(Comment, pk=parent_id, task=task)

        Comment.objects.create(
            task=task,
            author=request.user,
            content=content,
            parent_comment=parent_comment,
        )
        TaskActivity.objects.create(
            task=task, user=request.user,
            activity_type=TaskActivity.ActivityType.COMMENTED,
        )
        messages.success(request, "Коментар додано.")
        return redirect(task.get_absolute_url() + "#comments")


class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    template_name = "tasks/comment_form.html"
    fields = ["content"]

    def test_func(self):
        comment = self.get_object()
        return comment.author == self.request.user

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.is_edited = True
        comment.save()
        return redirect(comment.task.get_absolute_url() + "#comments")


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = "tasks/comment_confirm_delete.html"

    def test_func(self):
        comment = self.get_object()
        workspace = comment.task.task_list.project.workspace
        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=self.request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        return comment.author == self.request.user or is_admin

    def get_success_url(self):
        return self.object.task.get_absolute_url() + "#comments"









class TagListView(WorkspaceMemberMixin, ListView):
    model = Tag
    template_name = "tags/list.html"
    context_object_name = "tags"

    def get_queryset(self):
        workspace = self.get_workspace()
        return Tag.objects.filter(workspace=workspace).annotate(
            task_count=Count("tasks")
        )


class TagCreateView(WorkspaceMemberMixin, CreateView):
    model = Tag
    template_name = "tags/form.html"
    fields = ["name", "color"]

    def form_valid(self, form):
        tag = form.save(commit=False)
        tag.workspace = self.get_workspace()
        tag.save()
        return redirect(reverse("tag-list", kwargs={"workspace_pk": tag.workspace.pk}))