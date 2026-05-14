from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {}

    qs = Notification.objects.filter(
        recipient=request.user
    ).select_related("actor").order_by("-created_at")

    return {
        "unread_count": qs.filter(is_read=False).count(),
        "recent_notifications": qs[:10],
    }
