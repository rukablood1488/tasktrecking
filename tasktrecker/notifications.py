from .models import Notification

def _create(recipient, actor, notif_type, text, url=""):
    # ПОВЕРТАЄМО ПЕРЕВІРКУ: не надсилати сповіщення самому собі
    if recipient == actor:
        return
    Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notif_type=notif_type,
        text=text,
        url=url,
    )

# ────────────────────────────────────────────────────────────
# Workspace 
# ────────────────────────────────────────────────────────────

def notify_added_to_workspace(user, actor, workspace):
    _create(
        recipient=user,
        actor=actor,
        notif_type=Notification.NotifType.ADDED_TO_WORKSPACE,
        text=f"«{actor.username}» додав вас до простору «{workspace.name}»",
        url=workspace.get_absolute_url(),
    )

def notify_member_added(workspace, new_user, actor):
    owner = workspace.owner
    if owner == actor:
        return
    _create(
        recipient=owner,
        actor=actor,
        notif_type=Notification.NotifType.MEMBER_ADDED,
        text=f"«{actor.username}» додав «{new_user.username}» до вашого простору «{workspace.name}»",
        url=workspace.get_absolute_url(),
    )

# ────────────────────────────────────────────────────────────
# Task Helpers (НОВА ЛОГІКА ДЛЯ ЗАВДАНЬ)
# ────────────────────────────────────────────────────────────

def _get_task_recipients(task):
    """
    Збирає унікальний список користувачів, яким треба надіслати сповіщення:
    це автор завдання + всі призначені виконавці.
    """
    recipients = set()
    if task.created_by:
        recipients.add(task.created_by)
    for assignee in task.assignees.all():
        recipients.add(assignee)
    return recipients

# ────────────────────────────────────────────────────────────
# Task
# ────────────────────────────────────────────────────────────

def notify_task_status_changed(task, actor, old_status, new_status):
    for recipient in _get_task_recipients(task):
        _create(
            recipient=recipient,
            actor=actor,
            notif_type=Notification.NotifType.TASK_STATUS_CHANGED,
            text=f"«{actor.username}» змінив статус завдання «{task.title}»: {old_status} → {new_status}",
            url=task.get_absolute_url(),
        )

def notify_task_edited(task, actor):
    for recipient in _get_task_recipients(task):
        _create(
            recipient=recipient,
            actor=actor,
            notif_type=Notification.NotifType.TASK_EDITED,
            text=f"«{actor.username}» відредагував завдання «{task.title}»",
            url=task.get_absolute_url(),
        )

def notify_task_deleted(task, actor):
    for recipient in _get_task_recipients(task):
        _create(
            recipient=recipient,
            actor=actor,
            notif_type=Notification.NotifType.TASK_DELETED,
            text=f"«{actor.username}» видалив завдання «{task.title}»",
            url="", 
        )

# ────────────────────────────────────────────────────────────
# Comment 
# ────────────────────────────────────────────────────────────

def notify_task_commented(task, comment, actor):
    for recipient in _get_task_recipients(task):
        _create(
            recipient=recipient,
            actor=actor,
            notif_type=Notification.NotifType.TASK_COMMENTED,
            text=f"«{actor.username}» прокоментував завдання «{task.title}»",
            url=task.get_absolute_url() + "#comments",
        )

def notify_comment_replied(parent_comment, actor, task):
    _create(
        recipient=parent_comment.author,
        actor=actor,
        notif_type=Notification.NotifType.COMMENT_REPLIED,
        text=f"«{actor.username}» відповів на ваш коментар у завданні «{task.title}»",
        url=task.get_absolute_url() + "#comments",
    )

def notify_comment_edited(comment, actor):
    for recipient in _get_task_recipients(comment.task):
        _create(
            recipient=recipient,
            actor=actor,
            notif_type=Notification.NotifType.COMMENT_EDITED,
            text=f"«{actor.username}» відредагував коментар до завдання «{comment.task.title}»",
            url=comment.task.get_absolute_url() + "#comments",
        )

def notify_comment_deleted(comment, actor):
    for recipient in _get_task_recipients(comment.task):
        _create(
            recipient=recipient,
            actor=actor,
            notif_type=Notification.NotifType.COMMENT_DELETED,
            text=f"«{actor.username}» видалив коментар до завдання «{comment.task.title}»",
            url=comment.task.get_absolute_url() + "#comments",
        )

# ────────────────────────────────────────────────────────────
# Project
# ────────────────────────────────────────────────────────────

def notify_project_edited(project, actor):
    if project.created_by:
        _create(
            recipient=project.created_by,
            actor=actor,
            notif_type=Notification.NotifType.PROJECT_EDITED,
            text=f"«{actor.username}» відредагував проект «{project.name}»",
            url=project.get_absolute_url(),
        )

def notify_project_deleted(project, actor):
    if project.created_by:
        _create(
            recipient=project.created_by,
            actor=actor,
            notif_type=Notification.NotifType.PROJECT_DELETED,
            text=f"«{actor.username}» видалив проект «{project.name}»",
            url="",
        )