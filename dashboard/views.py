from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator

from lostfound.models import Item, Claim, Notification
from accounts.models import User
from . import services as dashboard_services


def _require_admin(view_func):
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin_user:
            messages.error(request, 'Access denied.')
            return redirect('dashboard:student_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped


@login_required
def student_dashboard(request):
    """Student dashboard with personal stats and recent activity."""
    if request.user.is_admin_user and not request.user.is_student:
        return redirect('dashboard:admin_dashboard')

    stats = dashboard_services.get_student_dashboard_stats(request.user)
    recent_items = Item.objects.filter(user=request.user).select_related('category').order_by('-created_at')[:5]
    recent_claims = Claim.objects.filter(claimant=request.user).select_related('item').order_by('-created_at')[:5]
    recent_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    return render(request, 'student/dashboard.html', {
        'stats': stats,
        'recent_items': recent_items,
        'recent_claims': recent_claims,
        'recent_notifications': recent_notifications,
    })


@_require_admin
def admin_dashboard(request):
    """Admin dashboard with system-wide statistics."""
    stats = dashboard_services.get_admin_dashboard_stats()
    recent_items = Item.objects.select_related('user', 'category').order_by('-created_at')[:8]
    pending_claims = Claim.objects.filter(
        status=Claim.Status.PENDING
    ).select_related('item', 'claimant').order_by('-created_at')[:8]

    return render(request, 'admin_panel/dashboard.html', {
        'stats': stats,
        'recent_items': recent_items,
        'pending_claims': pending_claims,
    })


@_require_admin
def admin_students(request):
    """Admin: list and manage students."""
    q = request.GET.get('q', '')
    department = request.GET.get('department', '')
    is_active = request.GET.get('is_active', '')

    students = User.objects.filter(role=User.Role.STUDENT).annotate(
        item_count=Count('items'),
        claim_count=Count('claims'),
    ).order_by('-date_joined')

    if q:
        students = students.filter(
            Q(username__icontains=q) | Q(full_name__icontains=q) |
            Q(email__icontains=q) | Q(usn__icontains=q)
        )
    if department:
        students = students.filter(department=department)
    if is_active in ('true', 'false'):
        students = students.filter(is_active=(is_active == 'true'))

    paginator = Paginator(students, 15)
    page = paginator.get_page(request.GET.get('page'))

    departments = User.objects.filter(role=User.Role.STUDENT).values_list(
        'department', flat=True
    ).distinct().exclude(department='').order_by('department')

    return render(request, 'admin_panel/students.html', {
        'page_obj': page,
        'q': q,
        'department': department,
        'is_active': is_active,
        'departments': departments,
    })


@_require_admin
def admin_toggle_student(request, pk):
    """Admin: activate or deactivate a student account."""
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    if request.method == 'POST':
        student.is_active = not student.is_active
        student.save(update_fields=['is_active'])
        action = 'activated' if student.is_active else 'deactivated'
        messages.success(request, f'Student account {student.username} has been {action}.')
    return redirect('dashboard:admin_students')


@_require_admin
def admin_student_detail(request, pk):
    """Admin: view a specific student's details and activity."""
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    items = Item.objects.filter(user=student).select_related('category').order_by('-created_at')
    claims = Claim.objects.filter(claimant=student).select_related('item').order_by('-created_at')
    return render(request, 'admin_panel/student_detail.html', {
        'student': student,
        'items': items,
        'claims': claims,
    })
