from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
 
 
class Workspace(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва")
    description = models.TextField(blank=True, verbose_name="Опис")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
        verbose_name="Власник"
    )
    members = models.ManyToManyField(
        User,
        through="WorkspaceMember",
        related_name="workspaces",
        verbose_name="Учасники"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name = "Робочий простір"
        verbose_name_plural = "Робочі простори"
        ordering = ["-created_at"]
 
    def __str__(self):
        return self.name
 
    def get_absolute_url(self):
        return reverse("workspace-detail", kwargs={"pk": self.pk})
 
 
class WorkspaceMember(models.Model):
 
    class Role(models.TextChoices):
        OWNER = "owner", "Власник"
        ADMIN = "admin", "Адміністратор"
        MEMBER = "member", "Учасник"
        GUEST = "guest", "Гість"
 
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name="Роль"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ("workspace", "user")
        verbose_name = "Учасник простору"
        verbose_name_plural = "Учасники простору"
 
    def __str__(self):
        return f"{self.user.username} — {self.workspace.name} ({self.get_role_display()})"
 
 
class Project(models.Model):
 
    class Color(models.TextChoices):
        RED = "#F75E5E", "Червоний"
        BLUE = "#4F8EF7", "Синій"
        GREEN = "#34C971", "Зелений"
        PURPLE = "#9B6BF2", "Фіолетовий"
        ORANGE = "#F7A134", "Помаранчевий"
        PINK = "#F76EBF", "Рожевий"
 
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="Робочий простір"
    )
    name = models.CharField(max_length=150, verbose_name="Назва")
    description = models.TextField(blank=True, verbose_name="Опис")
    color = models.CharField(
        max_length=7,
        choices=Color.choices,
        default=Color.BLUE,
        verbose_name="Колір"
    )
    icon = models.CharField(max_length=10, default=".", verbose_name="Іконка")
    is_archived = models.BooleanField(default=False, verbose_name="Архівований")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_projects",
        verbose_name="Створив"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекти"
        ordering = ["name"]
 
    def __str__(self):
        return f"{self.workspace.name} / {self.name}"
 
    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})
 
 
class TaskList(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="task_lists",
        verbose_name="Проект"
    )
    name = models.CharField(max_length=150, verbose_name="Назва")
    description = models.TextField(blank=True, verbose_name="Опис")
    position = models.PositiveIntegerField(default=0, verbose_name="Позиція")
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name = "Список завдань"
        verbose_name_plural = "Списки завдань"
        ordering = ["position", "created_at"]
 
    def __str__(self):
        return f"{self.project.name} / {self.name}"


class Tag(models.Model):

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="tags",
        verbose_name="Робочий простір"
    )
    name = models.CharField(max_length=50, verbose_name="Назва")
    color = models.CharField(max_length=7, default="#4F8EF7", verbose_name="Колір")
 
    class Meta:
        unique_together = ("workspace", "name")
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
 
    def __str__(self):
        return self.name


class Task(models.Model):
 
    class Status(models.TextChoices):
        TODO = "todo", "До виконання"
        IN_PROGRESS = "in_progress", "В процесі"
        IN_REVIEW = "in_review", "На перевірці"
        DONE = "done", "Виконано"
        CANCELLED = "cancelled", "Скасовано"
 
    class Priority(models.TextChoices):
        URGENT = "urgent", "Терміново"
        HIGH = "high", "Високий"
        NORMAL = "normal", "Нормальний"
        LOW = "low", "Низький"
        NO_PRIORITY = "no_priority", "Без пріоритету"
 

    task_list = models.ForeignKey(
        TaskList,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Список"
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subtasks",
        verbose_name="Батьківське завдання"
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="tasks",
        verbose_name="Теги"
    )
    assignees = models.ManyToManyField(
        User,
        blank=True,
        related_name="assigned_tasks",
        verbose_name="Виконавці"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tasks",
        verbose_name="Створив"
    )
 
    title = models.CharField(max_length=255, verbose_name="Назва")
    description = models.TextField(blank=True, verbose_name="Опис")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name="Статус"
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NO_PRIORITY,
        verbose_name="Пріоритет"
    )
 
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Термін виконання")
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата початку")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Виконано о")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Оціночний час (год)"
    )
    position = models.PositiveIntegerField(default=0, verbose_name="Позиція")
    is_archived = models.BooleanField(default=False, verbose_name="Архівовано")
 
    class Meta:
        verbose_name = "Завдання"
        verbose_name_plural = "Завдання"
        ordering = ["position", "-created_at"]
 
    def __str__(self):
        return self.title
 
    def get_absolute_url(self):
        return reverse("task-detail", kwargs={"pk": self.pk})
 
    @property
    def is_overdue(self):
        if self.due_date and self.status not in [self.Status.DONE, self.Status.CANCELLED]:
            return timezone.now() > self.due_date
        return False
 
    @property
    def subtask_count(self):
        return self.subtasks.count()
 
    @property
    def completed_subtask_count(self):
        return self.subtasks.filter(status=self.Status.DONE).count()
 
    def mark_complete(self):
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])


class Comment(models.Model):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Завдання"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="task_comments",
        verbose_name="Автор"
    )
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="Відповідь на"
    )
    content = models.TextField(verbose_name="Текст коментаря")
    is_edited = models.BooleanField(default=False, verbose_name="Відредаговано")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name = "Коментар"
        verbose_name_plural = "Коментарі"
        ordering = ["created_at"]
 
    def __str__(self):
        return f"Коментар {self.author.username} до «{self.task.title}»"
 
 
class TaskActivity(models.Model):
    """Журнал активності"""
 
    class ActivityType(models.TextChoices):
        CREATED = "created", "Створено"
        STATUS_CHANGED = "status_changed", "Змінено статус"
        PRIORITY_CHANGED = "priority_changed", "Змінено пріоритет"
        ASSIGNEE_ADDED = "assignee_added", "Додано виконавця"
        ASSIGNEE_REMOVED = "assignee_removed", "Видалено виконавця"
        DUE_DATE_CHANGED = "due_date_changed", "Змінено термін"
        COMMENTED = "commented", "Коментар"
        COMPLETED = "completed", "Виконано"
        ARCHIVED = "archived", "Архівовано"
 
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="Завдання"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="task_activities",
        verbose_name="Користувач"
    )
    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices,
        verbose_name="Тип активності"
    )
    old_value = models.CharField(max_length=255, blank=True, verbose_name="Попереднє значення")
    new_value = models.CharField(max_length=255, blank=True, verbose_name="Нове значення")
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name = "Активність завдання"
        verbose_name_plural = "Активності завдань"
        ordering = ["-created_at"]
 
    def __str__(self):
        return f"{self.get_activity_type_display()} — {self.task.title}"