from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone

from .models import Workspace, WorkspaceMember, Project, TaskList, Task, Comment, Tag



class RegisterForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "your@email.com",
        })
    )
    first_name = forms.CharField(
        max_length=50,
        required=False,
        label="Ім'я",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ім'я"})
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        label="Прізвище",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Прізвище"})
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrap_fields = ["username", "password1", "password2"]
        for field_name in bootstrap_fields:
            self.fields[field_name].widget.attrs.update({"class": "form-control"})

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Цей email вже використовується.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save()
        return user


class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Логін",
        })
        self.fields["password"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Пароль",
        })





class WorkspaceForm(forms.ModelForm):

    class Meta:
        model = Workspace
        fields = ["name", "description"]
        labels = {
            "name": "Назва простору",
            "description": "Опис",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Назва вашого простору",
                "autofocus": True,
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Короткий опис (необов'язково)",
            }),
        }


class WorkspaceMemberInviteForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Логін користувача",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Введіть логін",
        })
    )
    role = forms.ChoiceField(
        choices=WorkspaceMember.Role.choices,
        initial=WorkspaceMember.Role.MEMBER,
        label="Роль",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, workspace, *args, **kwargs):
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data.get("username")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError("Користувача з таким логіном не знайдено.")

        if WorkspaceMember.objects.filter(workspace=self.workspace, user=user).exists():
            raise forms.ValidationError("Цей користувач вже є учасником простору.")

        return user





class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "color", "icon"]
        labels = {
            "name": "Назва проекту",
            "description": "Опис",
            "color": "Колір",
            "icon": "Іконка (emoji)",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Назва проекту",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
            "color": forms.Select(attrs={"class": "form-select"}),
            "icon": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "📁",
                "maxlength": "4",
            }),
        }


class TaskListForm(forms.ModelForm):
    """C/U колонки (TaskList)"""

    class Meta:
        model = TaskList
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Назва списку",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
            }),
        }





class TaskForm(forms.ModelForm):

    due_date = forms.DateTimeField(
        required=False,
        label="Термін виконання",
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    start_date = forms.DateTimeField(
        required=False,
        label="Дата початку",
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Task
        fields = [
            "title", "description", "status", "priority",
            "due_date", "start_date", "estimated_hours",
            "assignees", "tags", "parent_task",
        ]
        labels = {
            "title": "Назва завдання",
            "description": "Опис",
            "status": "Статус",
            "priority": "Пріоритет",
            "estimated_hours": "Оціночний час (год)",
            "assignees": "Виконавці",
            "tags": "Теги",
            "parent_task": "Батьківське завдання",
        }
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Назва завдання",
                "autofocus": True,
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Детальний опис...",
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "estimated_hours": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.5",
                "placeholder": "0.0",
            }),
            
            "assignees": forms.CheckboxSelectMultiple(),
            "tags": forms.CheckboxSelectMultiple(),
            "parent_task": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, task_list=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if task_list:
            workspace = task_list.project.workspace

            self.fields["assignees"].queryset = User.objects.filter(
                workspaces=workspace
            )

            self.fields["tags"].queryset = Tag.objects.filter(workspace=workspace)

            task_qs = Task.objects.filter(task_list__project=task_list.project)
            if self.instance.pk:
                task_qs = task_qs.exclude(pk=self.instance.pk)
            self.fields["parent_task"].queryset = task_qs

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        due_date = cleaned_data.get("due_date")

        if start_date and due_date and start_date > due_date:
            raise forms.ValidationError(
                "Дата початку не може бути пізніше терміну виконання."
            )
        return cleaned_data


class TaskFilterForm(forms.Form):
    STATUS_CHOICES = [("", "Всі статуси")] + Task.Status.choices
    PRIORITY_CHOICES = [("", "Всі пріоритети")] + Task.Priority.choices
    DUE_DATE_CHOICES = [
        ("", "Будь-який термін"),
        ("overdue", "Прострочені"),
        ("today", "Сьогодні"),
        ("week", "Наступні 7 днів"),
    ]

    q = forms.CharField(
        required=False,
        label="Пошук",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Пошук завдань...",
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        label="Статус",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    priority = forms.ChoiceField(
        required=False,
        choices=PRIORITY_CHOICES,
        label="Пріоритет",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    due_date = forms.ChoiceField(
        required=False,
        choices=DUE_DATE_CHOICES,
        label="Термін",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    assignee = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        label="Виконавець",
        empty_label="Всі виконавці",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, workspace=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields["assignee"].queryset = User.objects.filter(
                workspaces=workspace
            )





class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ["content"]
        labels = {"content": ""}
        widgets = {
            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Написати коментар...",
            })
        }





class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "color"]
        labels = {
            "name": "Назва тегу",
            "color": "Колір (HEX)",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "bug, feature, urgent...",
            }),
            "color": forms.TextInput(attrs={
                "class": "form-control form-control-color",
                "type": "color",
            }),
        }