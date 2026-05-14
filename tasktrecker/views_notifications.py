from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse

from .models import Notification


class NotificationMarkReadView(LoginRequiredMixin, View):

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save(update_fields=["is_read"])

        if notif.url:
            return redirect(notif.url)
        referer = request.META.get("HTTP_REFERER")
        return redirect(referer or "workspace-list")


class NotificationMarkAllReadView(LoginRequiredMixin, View):

    def post(self, request):
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        referer = request.META.get("HTTP_REFERER")
        return redirect(referer or "workspace-list")
