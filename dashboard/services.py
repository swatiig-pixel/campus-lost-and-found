"""
Dashboard services — ORM aggregate queries for dashboards.
Demonstrates: COUNT, GROUP BY, annotate, select_related, prefetch_related,
aggregate functions, ordering, filtering.
"""
from django.db.models import Count, Q
from django.utils import timezone
import datetime

from lostfound.models import Item, Claim, Notification
from accounts.models import User


def get_student_dashboard_stats(user):
    """Aggregate stats for the student dashboard."""
    items = Item.objects.filter(user=user)
    claims = Claim.objects.filter(claimant=user)

    return {
        'total_items': items.count(),
        'lost_items': items.filter(report_type=Item.ReportType.LOST).count(),
        'found_items': items.filter(report_type=Item.ReportType.FOUND).count(),
        'pending_items': items.filter(verification_status=Item.VerificationStatus.PENDING).count(),
        'active_claims': claims.filter(status=Claim.Status.PENDING).count(),
        'approved_claims': claims.filter(status=Claim.Status.APPROVED).count(),
        'rejected_claims': claims.filter(status=Claim.Status.REJECTED).count(),
        'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
    }


def get_admin_dashboard_stats():
    """
    Aggregate statistics for admin dashboard.
    Uses ORM COUNT, GROUP BY (via annotate), aggregate functions.
    """
    items = Item.objects.all()
    claims = Claim.objects.all()
    users = User.objects.filter(role=User.Role.STUDENT)

    # Category breakdown — GROUP BY category
    category_stats = (
        Item.objects
        .values('category__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Monthly item reports (last 6 months)
    six_months_ago = timezone.now().date() - datetime.timedelta(days=180)
    monthly_stats = (
        Item.objects
        .filter(created_at__date__gte=six_months_ago)
        .extra(select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"})
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    # Students with most reports
    top_reporters = (
        User.objects
        .filter(role=User.Role.STUDENT)
        .annotate(item_count=Count('items'))
        .order_by('-item_count')[:5]
    )

    return {
        'total_students': users.count(),
        'total_items': items.count(),
        'lost_items': items.filter(report_type=Item.ReportType.LOST).count(),
        'found_items': items.filter(report_type=Item.ReportType.FOUND).count(),
        'pending_verification': items.filter(verification_status=Item.VerificationStatus.PENDING).count(),
        'approved_items': items.filter(verification_status=Item.VerificationStatus.APPROVED).count(),
        'rejected_items': items.filter(verification_status=Item.VerificationStatus.REJECTED).count(),
        'pending_claims': claims.filter(status=Claim.Status.PENDING).count(),
        'approved_claims': claims.filter(status=Claim.Status.APPROVED).count(),
        'rejected_claims': claims.filter(status=Claim.Status.REJECTED).count(),
        'returned_items': items.filter(status=Item.Status.RETURNED).count(),
        'unclaimed_items': items.filter(
            report_type=Item.ReportType.FOUND,
            verification_status=Item.VerificationStatus.APPROVED,
            status=Item.Status.ACTIVE
        ).count(),
        'category_stats': list(category_stats),
        'monthly_stats': list(monthly_stats),
        'top_reporters': top_reporters,
    }
