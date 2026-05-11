from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from .models import Workspace, WorkspaceMember, Task


def _no_permission(request, msg):
    messages.error(request, msg)
    referer = request.META.get("HTTP_REFERER")
    return redirect(referer) if referer else redirect("workspace-list")


class WorkspaceMemberMixin(LoginRequiredMixin):

    def get_workspace(self):
        workspace_pk = self.kwargs.get("workspace_pk") or self.kwargs.get("pk")
        return get_object_or_404(Workspace, pk=workspace_pk)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        workspace = self.get_workspace()
        is_member = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).exists()
        if not is_member:
            return _no_permission(request, "Ви не є учасником цього простору.")
        return super().dispatch(request, *args, **kwargs)


class WorkspaceAdminMixin(WorkspaceMemberMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        workspace = self.get_workspace()

        is_member = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).exists()
        if not is_member:
            return _no_permission(request, "Ви не є учасником цього простору.")

        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        if not is_admin:
            return _no_permission(request, "Потрібні права адміністратора.")

        return super(WorkspaceMemberMixin, self).dispatch(request, *args, **kwargs)


class TaskOwnerOrAdminMixin(LoginRequiredMixin):

    def get_task(self):
        return get_object_or_404(Task, pk=self.kwargs["pk"])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        task = self.get_task()
        workspace = task.task_list.project.workspace

        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        is_creator = task.created_by == request.user

        if not (is_admin or is_creator):
            return _no_permission(
                request, "Лише автор або адміністратор може змінювати це завдання."
            )
        return super().dispatch(request, *args, **kwargs)


class CommentAuthorOrAdminMixin(LoginRequiredMixin):

    def get_comment(self):
        from .models import Comment
        return get_object_or_404(Comment, pk=self.kwargs["pk"])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        comment = self.get_comment()
        workspace = comment.task.task_list.project.workspace

        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        is_author = comment.author == request.user

        if not (is_admin or is_author):
            return _no_permission(
                request, "Лише автор або адміністратор може змінювати цей коментар."
            )
        return super().dispatch(request, *args, **kwargs)