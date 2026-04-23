from django.urls import path
from . import views


auth_patterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
]



workspace_patterns = [
    path("",
         views.WorkspaceListView.as_view(),
         name="workspace-list"),

    path("create/",
         views.WorkspaceCreateView.as_view(),
         name="workspace-create"),

    path("<int:pk>/",
         views.WorkspaceDetailView.as_view(),
         name="workspace-detail"),

    path("<int:pk>/edit/",
         views.WorkspaceUpdateView.as_view(),
         name="workspace-update"),

    path("<int:pk>/delete/",
         views.WorkspaceDeleteView.as_view(),
         name="workspace-delete"),


    path("<int:workspace_pk>/members/",
         views.WorkspaceMemberListView.as_view(),
         name="workspace-members"),

    path("<int:workspace_pk>/members/invite/",
         views.WorkspaceMemberInviteView.as_view(),
         name="workspace-invite"),

    path("<int:workspace_pk>/members/<int:member_pk>/remove/",
         views.WorkspaceMemberRemoveView.as_view(),
         name="workspace-member-remove"),

    
    path("<int:workspace_pk>/tags/",
         views.TagListView.as_view(),
         name="tag-list"),

    path("<int:workspace_pk>/tags/create/",
         views.TagCreateView.as_view(),
         name="tag-create"),
]



project_patterns = [
    path("<int:workspace_pk>/projects/create/",
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
         views.TaskListCreateView.as_view(),
         name="tasklist-create"),

    path("projects/lists/<int:pk>/edit/",
         views.TaskListUpdateView.as_view(),
         name="tasklist-update"),

    path("projects/lists/<int:pk>/delete/",
         views.TaskListDeleteView.as_view(),
         name="tasklist-delete"),
]



task_patterns = [
    path("",
         views.TaskListView.as_view(),
         name="task-list"),

    path("create/<int:list_pk>/",
         views.TaskCreateView.as_view(),
         name="task-create"),

    path("<int:pk>/",
         views.TaskDetailView.as_view(),
         name="task-detail"),

    path("<int:pk>/edit/",
         views.TaskUpdateView.as_view(),
         name="task-update"),

    path("<int:pk>/delete/",
         views.TaskDeleteView.as_view(),
         name="task-delete"),

    path("<int:pk>/status/",
         views.TaskStatusUpdateView.as_view(),
         name="task-status-update"),

    path("<int:pk>/reorder/",
         views.TaskReorderView.as_view(),
         name="task-reorder"),

    path("<int:pk>/archive/",
         views.TaskArchiveView.as_view(),
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



urlpatterns = (
    auth_patterns
    + workspace_patterns
    + project_patterns
    + task_patterns
    + comment_patterns
)