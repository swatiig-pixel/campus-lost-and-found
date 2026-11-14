from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST

from .models import Item, Claim, Message, Notification, Category
from .forms import ReportItemForm, ClaimForm, MessageForm, ItemSearchForm
from . import services


def _student_required(view_func):
    """Decorator: requires login AND student role."""
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.is_admin_user and not request.user.is_student:
            messages.error(request, 'Admin accounts cannot perform student actions.')
            return redirect('dashboard:admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped


def landing_page(request):
    """Public landing page with statistics."""
    stats = {
        'total_lost': Item.objects.filter(report_type=Item.ReportType.LOST,
                                          verification_status=Item.VerificationStatus.APPROVED).count(),
        'total_found': Item.objects.filter(report_type=Item.ReportType.FOUND,
                                           verification_status=Item.VerificationStatus.APPROVED).count(),
        'total_returned': Item.objects.filter(status=Item.Status.RETURNED).count(),
    }
    recent_items = Item.objects.filter(
        verification_status=Item.VerificationStatus.APPROVED
    ).select_related('category', 'user').order_by('-created_at')[:6]

    return render(request, 'landing.html', {'stats': stats, 'recent_items': recent_items})


def _get_item_queryset(report_type, search_form):
    """Build filtered queryset from search form."""
    qs = Item.objects.filter(
        report_type=report_type,
        verification_status=Item.VerificationStatus.APPROVED
    ).select_related('category', 'user')

    if search_form.is_valid():
        q = search_form.cleaned_data.get('q')
        category = search_form.cleaned_data.get('category')
        location = search_form.cleaned_data.get('location')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        sort = search_form.cleaned_data.get('sort') or '-created_at'

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))
        if category:
            qs = qs.filter(category=category)
        if location:
            qs = qs.filter(location__icontains=location)
        if date_from:
            qs = qs.filter(report_date__gte=date_from)
        if date_to:
            qs = qs.filter(report_date__lte=date_to)
        qs = qs.order_by(sort)
    else:
        qs = qs.order_by('-created_at')

    return qs


@login_required
def lost_items(request):
    form = ItemSearchForm(request.GET)
    qs = _get_item_queryset(Item.ReportType.LOST, form)
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'student/lost_items.html', {
        'page_obj': page, 'form': form, 'report_type': 'LOST',
        'categories': Category.objects.all(),
    })


@login_required
def found_items(request):
    form = ItemSearchForm(request.GET)
    qs = _get_item_queryset(Item.ReportType.FOUND, form)
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'student/found_items.html', {
        'page_obj': page, 'form': form, 'report_type': 'FOUND',
        'categories': Category.objects.all(),
    })


@login_required
def item_detail(request, pk):
    item = get_object_or_404(
        Item.objects.select_related('category', 'user').prefetch_related('status_history'),
        pk=pk
    )
    # Non-approved items are only visible to their owner or admins
    if item.verification_status != Item.VerificationStatus.APPROVED:
        if request.user != item.user and not request.user.is_admin_user:
            raise Http404

    # Check if current user already has a pending/approved claim
    existing_claim = None
    can_claim = False
    if request.user.is_authenticated and not request.user.is_admin_user:
        existing_claim = Claim.objects.filter(item=item, claimant=request.user).first()
        can_claim = (
            item.report_type == Item.ReportType.FOUND
            and item.verification_status == Item.VerificationStatus.APPROVED
            and item.status == Item.Status.ACTIVE
            and item.user != request.user
            and not existing_claim
        )

    return render(request, 'student/item_detail.html', {
        'item': item,
        'existing_claim': existing_claim,
        'can_claim': can_claim,
        'history': item.status_history.select_related('changed_by').all(),
    })


@_student_required
def report_lost(request):
    return _report_item(request, Item.ReportType.LOST)


@_student_required
def report_found(request):
    return _report_item(request, Item.ReportType.FOUND)


def _report_item(request, report_type):
    """Shared logic for reporting lost or found items."""
    if request.method == 'POST':
        form = ReportItemForm(request.POST, request.FILES)
        form.data = form.data.copy()
        form.data['report_type'] = report_type
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.report_type = report_type
            item.verification_status = Item.VerificationStatus.PENDING
            item.status = Item.Status.ACTIVE
            item.save()
            messages.success(request, f'Your {report_type.lower()} item report has been submitted! '
                                       f'It will be visible after admin verification.')
            return redirect('lostfound:item_detail', pk=item.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ReportItemForm(initial={'report_type': report_type})

    template = 'student/report_lost.html' if report_type == Item.ReportType.LOST else 'student/report_found.html'
    return render(request, template, {'form': form, 'report_type': report_type})


@login_required
def my_reports(request):
    """Student's own reported items."""
    items = Item.objects.filter(user=request.user).select_related('category').order_by('-created_at')
    return render(request, 'student/my_reports.html', {'items': items})


@login_required
def edit_report(request, pk):
    """Edit an item report — only allowed when PENDING verification."""
    item = get_object_or_404(Item, pk=pk, user=request.user)
    if item.verification_status != Item.VerificationStatus.PENDING:
        messages.error(request, 'You can only edit items that are pending verification.')
        return redirect('lostfound:my_reports')

    if request.method == 'POST':
        form = ReportItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item report updated successfully.')
            return redirect('lostfound:my_reports')
    else:
        form = ReportItemForm(instance=item)

    return render(request, 'student/edit_report.html', {'form': form, 'item': item})


@login_required
def delete_report(request, pk):
    """Delete an item report — only allowed when PENDING verification."""
    item = get_object_or_404(Item, pk=pk, user=request.user)
    if item.verification_status != Item.VerificationStatus.PENDING:
        messages.error(request, 'You can only delete items that are pending verification.')
        return redirect('lostfound:my_reports')

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item report deleted.')
        return redirect('lostfound:my_reports')

    return render(request, 'student/confirm_delete.html', {'item': item})


@_student_required
def submit_claim(request, item_pk):
    """Submit a claim for a found item."""
    item = get_object_or_404(Item, pk=item_pk,
                             report_type=Item.ReportType.FOUND,
                             verification_status=Item.VerificationStatus.APPROVED,
                             status=Item.Status.ACTIVE)

    # Cannot claim own item
    if item.user == request.user:
        messages.error(request, 'You cannot claim your own reported item.')
        return redirect('lostfound:item_detail', pk=item_pk)

    # Check for duplicate claim
    if Claim.objects.filter(item=item, claimant=request.user, status=Claim.Status.PENDING).exists():
        messages.warning(request, 'You already have a pending claim for this item.')
        return redirect('lostfound:my_claims')

    if request.method == 'POST':
        form = ClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.item = item
            claim.claimant = request.user
            claim.status = Claim.Status.PENDING
            claim.save()

            # Notify item reporter
            services.create_notification(
                user=item.user,
                message=f'{request.user.full_name or request.user.username} has submitted a claim for your found item "{item.name}".',
                notification_type=Notification.NotificationType.CLAIM_SUBMITTED,
                related_item=item,
                related_claim=claim,
            )

            messages.success(request, 'Your claim has been submitted! The admin will review it.')
            return redirect('lostfound:my_claims')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClaimForm()

    return render(request, 'student/submit_claim.html', {'form': form, 'item': item})


@login_required
def my_claims(request):
    """List all claims submitted by the current student."""
    claims = Claim.objects.filter(
        claimant=request.user
    ).select_related('item', 'item__category', 'reviewed_by').order_by('-created_at')
    return render(request, 'student/my_claims.html', {'claims': claims})


@login_required
def notifications_view(request):
    """List notifications for the current user."""
    # Handle AJAX unread count polling
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'unread_count': unread_count})

    notifs = Notification.objects.filter(
        user=request.user
    ).select_related('related_item', 'related_claim').order_by('-created_at')

    # Mark all as read
    unread_ids = notifs.filter(is_read=False).values_list('id', flat=True)
    if unread_ids:
        Notification.objects.filter(id__in=list(unread_ids)).update(is_read=True)

    paginator = Paginator(notifs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'student/notifications.html', {'page_obj': page})


@login_required
def messages_inbox(request):
    """Show all conversations for the current user."""
    from django.db.models import Max, Subquery, OuterRef

    # Get distinct conversations (item + other_user pairs)
    sent = Message.objects.filter(sender=request.user).values('item', 'receiver').distinct()
    received = Message.objects.filter(receiver=request.user).values('item', 'sender').distinct()

    # Build conversation list
    conversations = []
    seen = set()

    for msg_set, other_field in [(Message.objects.filter(sender=request.user), 'receiver'),
                                   (Message.objects.filter(receiver=request.user), 'sender')]:
        for msg in msg_set.select_related('item', 'sender', 'receiver').order_by('-created_at'):
            other_user = getattr(msg, other_field)
            key = (msg.item_id, min(request.user.id, other_user.id), max(request.user.id, other_user.id))
            if key not in seen:
                seen.add(key)
                conversations.append({
                    'item': msg.item,
                    'other_user': other_user,
                    'last_message': msg,
                    'unread_count': Message.objects.filter(
                        item=msg.item, sender=other_user, receiver=request.user, is_read=False
                    ).count(),
                })

    return render(request, 'student/messages_inbox.html', {'conversations': conversations})


@login_required
def message_conversation(request, item_pk, other_user_pk):
    """View and send messages in a conversation."""
    from accounts.models import User as UserModel
    item = get_object_or_404(Item, pk=item_pk)
    other_user = get_object_or_404(UserModel, pk=other_user_pk)

    # Authorization: only item reporter or approved claimant can message
    approved_claim = Claim.objects.filter(item=item, status=Claim.Status.APPROVED).first()
    authorized_users = [item.user]
    if approved_claim:
        authorized_users.append(approved_claim.claimant)

    if request.user not in authorized_users or other_user not in authorized_users:
        messages.error(request, 'You are not authorized to view this conversation.')
        return redirect('lostfound:messages_inbox')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = other_user
            msg.item = item
            msg.save()

            # Notify receiver
            services.create_notification(
                user=other_user,
                message=f'New message from {request.user.full_name or request.user.username} about "{item.name}".',
                notification_type=Notification.NotificationType.MESSAGE_RECEIVED,
                related_item=item,
            )

            return redirect('lostfound:message_conversation', item_pk=item_pk, other_user_pk=other_user_pk)
    else:
        form = MessageForm()

    # Mark received messages as read
    Message.objects.filter(item=item, sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    convo_messages = Message.objects.filter(
        item=item
    ).filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).select_related('sender', 'receiver').order_by('created_at')

    return render(request, 'student/message_conversation.html', {
        'convo_messages': convo_messages,
        'form': form,
        'item': item,
        'other_user': other_user,
    })


# ─── Admin Views ──────────────────────────────────────────────────────────────

def _admin_required(view_func):
    """Decorator: requires login AND admin/staff role."""
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin_user:
            messages.error(request, 'You do not have permission to access that page.')
            return redirect('dashboard:student_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped


@_admin_required
def admin_items(request):
    """Admin: view and filter all item reports."""
    report_type = request.GET.get('type', '')
    vstatus = request.GET.get('vstatus', '')
    q = request.GET.get('q', '')

    items = Item.objects.select_related('user', 'category').order_by('-created_at')
    if report_type:
        items = items.filter(report_type=report_type)
    if vstatus:
        items = items.filter(verification_status=vstatus)
    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))

    paginator = Paginator(items, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/items.html', {
        'page_obj': page, 'q': q, 'type': report_type, 'vstatus': vstatus,
    })


@_admin_required
def admin_item_action(request, pk):
    """Admin: approve, reject, or mark item returned."""
    item = get_object_or_404(Item, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')

        if action == 'approve':
            services.approve_item(item, request.user)
            messages.success(request, f'Item "{item.name}" has been approved.')
        elif action == 'reject':
            services.reject_item(item, request.user, remarks)
            messages.warning(request, f'Item "{item.name}" has been rejected.')
        elif action == 'returned':
            services.mark_item_returned(item, request.user, remarks)
            messages.success(request, f'Item "{item.name}" marked as returned.')
        else:
            messages.error(request, 'Unknown action.')
        return redirect('lostfound:admin_items')

    return render(request, 'admin_panel/item_detail.html', {'item': item})


@_admin_required
def admin_claims(request):
    """Admin: view all claims."""
    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')

    claims = Claim.objects.select_related(
        'item', 'claimant', 'reviewed_by'
    ).order_by('-created_at')

    if status_filter:
        claims = claims.filter(status=status_filter)
    if q:
        claims = claims.filter(
            Q(item__name__icontains=q) | Q(claimant__username__icontains=q) | Q(claimant__full_name__icontains=q)
        )

    paginator = Paginator(claims, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/claims.html', {
        'page_obj': page, 'status_filter': status_filter, 'q': q,
    })


@_admin_required
def admin_claim_detail(request, pk):
    """Admin: review and decide on a specific claim."""
    claim = get_object_or_404(
        Claim.objects.select_related('item', 'item__user', 'claimant', 'reviewed_by'),
        pk=pk
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('admin_remarks', '')

        if action == 'approve':
            success, msg = services.approve_claim(claim, request.user)
            if success:
                messages.success(request, f'Claim approved. {msg}')
            else:
                messages.error(request, msg)
        elif action == 'reject':
            success, msg = services.reject_claim(claim, request.user, remarks)
            if success:
                messages.warning(request, f'Claim rejected. {msg}')
            else:
                messages.error(request, msg)
        return redirect('lostfound:admin_claims')

    return render(request, 'admin_panel/claim_detail.html', {'claim': claim})
