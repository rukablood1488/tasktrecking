from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
 
from .models import Workspace, WorkspaceMember, Task


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
    

class CommentAuthorOrAdminMixin(LoginRequiredMixin):
 
    def get_comment(self):
        from .models import Comment
        return get_object_or_404(Comment, pk=self.kwargs["pk"])
 
    def dispatch(self, request, *args, **kwargs):
        comment = self.get_comment()
        workspace = comment.task.task_list.project.workspace
 
        is_admin = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()
        is_author = comment.author == request.user
 
        if not (is_admin or is_author):
            return HttpResponseForbidden("Недостатньо прав для цієї дії.")
 
        return super().dispatch(request, *args, **kwargs)