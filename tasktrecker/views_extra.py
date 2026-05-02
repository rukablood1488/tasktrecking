from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages

from .models import Workspace, WorkspaceMember, Project, TaskList, Task, TaskActivity
from .mixins import WorkspaceMemberMixin, WorkspaceAdminMixin




class WorkspaceMemberListView(WorkspaceMemberMixin, ListView):
    
    model = WorkspaceMember
    template_name = "workspaces/members.html"
    context_object_name = "members"

    def get_queryset(self):
        workspace = self.get_workspace()
        return WorkspaceMember.objects.filter(
            workspace=workspace
        ).select_related("user").order_by("role", "joined_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["workspace"] = self.get_workspace()
        ctx["user_role"] = WorkspaceMember.objects.get(
            workspace=ctx["workspace"],
            user=self.request.user
        ).role
        return ctx


class WorkspaceMemberInviteView(WorkspaceAdminMixin, View):

    def post(self, request, workspace_pk):
        workspace = self.get_workspace()
        username = request.POST.get("username", "").strip()
        role = request.POST.get("role", WorkspaceMember.Role.MEMBER)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, f"Користувача «{username}» не знайдено.")
            return redirect(reverse("workspace-detail", kwargs={"pk": workspace_pk}))


        if WorkspaceMember.objects.filter(workspace=workspace, user=user).exists():
            messages.warning(request, f"«{username}» вже є учасником цього простору.")
            return redirect(reverse("workspace-detail", kwargs={"pk": workspace_pk}))


        valid_roles = [r[0] for r in WorkspaceMember.Role.choices]
        if role not in valid_roles:
            role = WorkspaceMember.Role.MEMBER

        WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role=role,
        )
        messages.success(request, f"«{username}» додано до простору з роллю «{role}».")
        return redirect(reverse("workspace-detail", kwargs={"pk": workspace_pk}))


class WorkspaceMemberRemoveView(WorkspaceAdminMixin, View):

    def post(self, request, workspace_pk, member_pk):
        workspace = self.get_workspace()
        member = get_object_or_404(
            WorkspaceMember,
            pk=member_pk,
            workspace=workspace
        )

        if member.role == WorkspaceMember.Role.OWNER:
            messages.error(request, "Власника простору не можна видалити.")
            return redirect(reverse("workspace-detail", kwargs={"pk": workspace_pk}))

        requester_role = WorkspaceMember.objects.get(
            workspace=workspace, user=request.user
        ).role
        if (member.role == WorkspaceMember.Role.ADMIN
                and requester_role != WorkspaceMember.Role.OWNER):
            messages.error(request, "Лише власник може видаляти адміністраторів.")
            return redirect(reverse("workspace-detail", kwargs={"pk": workspace_pk}))

        removed_username = member.user.username
        member.delete()
        messages.success(request, f"Учасника «{removed_username}» видалено з простору.")
        return redirect(reverse("workspace-detail", kwargs={"pk": workspace_pk}))






class TaskListCreateView(LoginRequiredMixin, View):

    def post(self, request, project_pk):
        project = get_object_or_404(
            Project,
            pk=project_pk,
            workspace__members=request.user 
        )
        name = request.POST.get("name", "").strip()

        if not name:
            messages.error(request, "Назва списку не може бути порожньою.")
            return redirect(reverse("project-detail", kwargs={"pk": project_pk}))

        last_position = TaskList.objects.filter(
            project=project
        ).order_by("-position").values_list("position", flat=True).first()
        new_position = (last_position or 0) + 1

        TaskList.objects.create(
            project=project,
            name=name,
            position=new_position,
        )
        messages.success(request, f"Список «{name}» створено.")
        return redirect(reverse("project-detail", kwargs={"pk": project_pk}))


class TaskListUpdateView(LoginRequiredMixin, UpdateView):
    
    model = TaskList
    fields = ["name", "description"]
    template_name = "projects/tasklist_form.html"

    def dispatch(self, request, *args, **kwargs):
        task_list = self.get_object()
        workspace = task_list.project.workspace
        is_member = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).exists()
        if not is_member:
            return HttpResponseForbidden("Немає доступу.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.project.pk})


class TaskListDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    
    model = TaskList
    template_name = "projects/tasklist_confirm_delete.html"

    def test_func(self):
        task_list = self.get_object()
        workspace = task_list.project.workspace
        return WorkspaceMember.objects.filter(
            workspace=workspace,
            user=self.request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Список «{self.object.name}» видалено.")
        return super().form_valid(form)






class TaskReorderView(LoginRequiredMixin, View):
    

    def post(self, request, pk):
        task = get_object_or_404(
            Task,
            pk=pk,
            task_list__project__workspace__members=request.user
        )

        new_list_pk = request.POST.get("list_pk")
        new_position = request.POST.get("position")

        try:
            new_position = int(new_position)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Невірна позиція."}, status=400)


        if new_list_pk and int(new_list_pk) != task.task_list_id:
            new_list = get_object_or_404(
                TaskList,
                pk=new_list_pk,
                project__workspace__members=request.user
            )
            task.task_list = new_list

        task.position = new_position
        task.save(update_fields=["task_list", "position", "updated_at"])

        return JsonResponse({
            "success": True,
            "task_id": task.pk,
            "list_id": task.task_list_id,
            "position": task.position,
        })


class TaskArchiveView(LoginRequiredMixin, View):
    

    def post(self, request, pk):
        task = get_object_or_404(
            Task,
            pk=pk,
            task_list__project__workspace__members=request.user
        )

        workspace = task.task_list.project.workspace
        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        is_creator = task.created_by == request.user

        if not (is_admin or is_creator):
            return HttpResponseForbidden("Недостатньо прав.")

        
        restore = request.POST.get("restore") == "1"
        task.is_archived = not restore
        task.save(update_fields=["is_archived", "updated_at"])

        TaskActivity.objects.create(
            task=task,
            user=request.user,
            activity_type=TaskActivity.ActivityType.ARCHIVED,
            new_value="false" if restore else "true",
        )

        action = "розархівовано" if restore else "архівовано"
        messages.success(request, f"Завдання «{task.title}» {action}.")

        
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "is_archived": task.is_archived,
            })

        return redirect(reverse("project-detail", kwargs={"pk": task.task_list.project.pk})