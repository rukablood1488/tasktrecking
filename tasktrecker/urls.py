from django.urls import path
from . import views
from . import views_extra
from . import views_notifications


auth_patterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
]


landing_pattern = [
    path("", views.LandingView.as_view(), name="landing"),
]


workspace_patterns = [
    path("workspaces/",
         views.WorkspaceListView.as_view(),
         name="workspace-list"),

    path("workspaces/create/",
         views.WorkspaceCreateView.as_view(),
         name="workspace-create"),

    path("workspaces/<int:pk>/",
         views.WorkspaceDetailView.as_view(),
         name="workspace-detail"),

    path("workspaces/<int:pk>/edit/",
         views.WorkspaceUpdateView.as_view(),
         name="workspace-update"),

    path("workspaces/<int:pk>/delete/",
         views.WorkspaceDeleteView.as_view(),
         name="workspace-delete"),

    
    path("workspaces/<int:workspace_pk>/members/",
         views_extra.WorkspaceMemberListView.as_view(),
         name="workspace-members"),

    path("workspaces/<int:workspace_pk>/members/invite/",
         views_extra.WorkspaceMemberInviteView.as_view(),
         name="workspace-invite"),

    path("workspaces/<int:workspace_pk>/members/<int:member_pk>/remove/",
         views_extra.WorkspaceMemberRemoveView.as_view(),
         name="workspace-member-remove"),

    
    path("workspaces/<int:workspace_pk>/tags/",
         views.TagListView.as_view(),
         name="tag-list"),

    path("workspaces/<int:workspace_pk>/tags/create/",
         views.TagCreateView.as_view(),
         name="tag-create"),
]



project_patterns = [
    path("workspaces/<int:workspace_pk>/projects/create/",
         views.ProjectCreateView.as_view(),
         name="project-create"),

    path("projects/<int:pk>/",
         views.ProjectDetailView.as_view(),
         name="project-detail"),

    path("projects/<int:pk>/edit/",
         views.ProjectUpdateView.as_view(),
         name="project-update"),

    path("projects/<int:pk>/delete/",
         views.ProjectDeleteView.as_view(),
         name="project-delete"),

    
    path("projects/<int:project_pk>/lists/create/",
         views_extra.TaskListCreateView.as_view(),
         name="tasklist-create"),

    path("projects/lists/<int:pk>/edit/",
         views_extra.TaskListUpdateView.as_view(),
         name="tasklist-update"),

    path("projects/lists/<int:pk>/delete/",
         views_extra.TaskListDeleteView.as_view(),
         name="tasklist-delete"),
]



task_patterns = [
    path("tasks/",
         views.TaskListView.as_view(),
         name="task-list"),

    path("tasks/create/<int:list_pk>/",
         views.TaskCreateView.as_view(),
         name="task-create"),

    path("tasks/<int:pk>/",
         views.TaskDetailView.as_view(),
         name="task-detail"),

    path("tasks/<int:pk>/edit/",
         views.TaskUpdateView.as_view(),
         name="task-update"),

    path("tasks/<int:pk>/delete/",
         views.TaskDeleteView.as_view(),
         name="task-delete"),

    path("tasks/<int:pk>/status/",
         views.TaskStatusUpdateView.as_view(),
         name="task-status-update"),

    path("tasks/<int:pk>/reorder/",
         views_extra.TaskReorderView.as_view(),
         name="task-reorder"),

    path("tasks/<int:pk>/archive/",
         views_extra.TaskArchiveView.as_view(),
         name="task-archive"),
]



comment_patterns = [
    path("tasks/<int:task_pk>/comments/add/",
         views.CommentCreateView.as_view(),
         name="comment-create"),

    path("comments/<int:pk>/edit/",
         views.CommentUpdateView.as_view(),
         name="comment-update"),

    path("comments/<int:pk>/delete/",
         views.CommentDeleteView.as_view(),
         name="comment-delete"),
]



notification_patterns = [
    path("notifications/<int:pk>/read/",
         views_notifications.NotificationMarkReadView.as_view(),
         name="notification-read"),

    path("notifications/read-all/",
         views_notifications.NotificationMarkAllReadView.as_view(),
         name="notification-read-all"),
]


urlpatterns = (
    auth_patterns
    + landing_pattern
    + workspace_patterns
    + project_patterns
    + task_patterns
    + comment_patterns
    + notification_patterns
)