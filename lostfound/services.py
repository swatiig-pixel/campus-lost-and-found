"""
Business logic services for the lostfound app.
All database-critical operations use transaction.atomic() for data integrity.
"""
from django.db import transaction
from django.utils import timezone
from .models import Item, Claim, Notification, ItemStatusHistory


def create_notification(user, message, notification_type, related_item=None, related_claim=None):
    """Create a notification for a user."""
    Notification.objects.create(
        user=user,
        message=message,
        notification_type=notification_type,
        related_item=related_item,
        related_claim=related_claim,
    )


@transaction.atomic
def approve_item(item, admin_user):
    """
    Approve an item listing.
    Uses select_for_update() to prevent race conditions.
    Records status history.
    """
    item = Item.objects.select_for_update().get(pk=item.pk)
    if item.verification_status == Item.VerificationStatus.APPROVED:
        return False  # Already approved

    old_vstatus = item.verification_status
    item.verification_status = Item.VerificationStatus.APPROVED
    item.save(update_fields=['verification_status', 'updated_at'])

    ItemStatusHistory.objects.create(
        item=item,
        changed_by=admin_user,
        old_status=old_vstatus,
        new_status=item.verification_status,
        remarks='Item listing approved by admin.',
    )

    # Notify the reporter
    create_notification(
        user=item.user,
        message=f'Your {item.report_type.lower()} item report "{item.name}" has been approved and is now visible to others.',
        notification_type=Notification.NotificationType.ITEM_APPROVED,
        related_item=item,
    )
    return True


@transaction.atomic
def reject_item(item, admin_user, remarks=''):
    """Reject an item listing with optional remarks."""
    item = Item.objects.select_for_update().get(pk=item.pk)
    old_vstatus = item.verification_status
    item.verification_status = Item.VerificationStatus.REJECTED
    item.save(update_fields=['verification_status', 'updated_at'])

    ItemStatusHistory.objects.create(
        item=item,
        changed_by=admin_user,
        old_status=old_vstatus,
        new_status=item.verification_status,
        remarks=remarks or 'Item listing rejected by admin.',
    )

    create_notification(
        user=item.user,
        message=f'Your item report "{item.name}" was rejected. Reason: {remarks or "See admin remarks."}',
        notification_type=Notification.NotificationType.ITEM_REJECTED,
        related_item=item,
    )
    return True


@transaction.atomic
def approve_claim(claim, admin_user):
    """
    Approve a claim:
    1. Locks the claim and item rows.
    2. Updates claim status to APPROVED.
    3. Updates item status to CLAIMED.
    4. Rejects all other pending claims for the same item.
    5. Notifies both the claimant and the item reporter.
    """
    claim = Claim.objects.select_for_update().get(pk=claim.pk)
    item = Item.objects.select_for_update().get(pk=claim.item_id)

    if claim.status != Claim.Status.PENDING:
        return False, 'This claim is no longer pending.'

    # Approve this claim
    claim.status = Claim.Status.APPROVED
    claim.admin_remarks = claim.admin_remarks  # preserve existing
    claim.reviewed_by = admin_user
    claim.reviewed_at = timezone.now()
    claim.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

    # Update item lifecycle status
    old_item_status = item.status
    item.status = Item.Status.CLAIMED
    item.save(update_fields=['status', 'updated_at'])

    ItemStatusHistory.objects.create(
        item=item,
        changed_by=admin_user,
        old_status=old_item_status,
        new_status=item.status,
        remarks=f'Claim #{claim.pk} approved. Item marked as CLAIMED.',
    )

    # Reject all other pending claims for this item
    other_pending = Claim.objects.filter(
        item=item,
        status=Claim.Status.PENDING
    ).exclude(pk=claim.pk)

    for other_claim in other_pending:
        other_claim.status = Claim.Status.REJECTED
        other_claim.admin_remarks = 'Another claim for this item was approved.'
        other_claim.reviewed_by = admin_user
        other_claim.reviewed_at = timezone.now()
        other_claim.save(update_fields=['status', 'admin_remarks', 'reviewed_by', 'reviewed_at', 'updated_at'])

        create_notification(
            user=other_claim.claimant,
            message=f'Your claim for "{item.name}" was rejected because another claim was approved.',
            notification_type=Notification.NotificationType.CLAIM_REJECTED,
            related_item=item,
            related_claim=other_claim,
        )

    # Notify claimant
    create_notification(
        user=claim.claimant,
        message=f'Your claim for "{item.name}" has been APPROVED! Please coordinate with the finder to collect your item.',
        notification_type=Notification.NotificationType.CLAIM_APPROVED,
        related_item=item,
        related_claim=claim,
    )

    # Notify item reporter (finder)
    create_notification(
        user=item.user,
        message=f'A claim for your found item "{item.name}" has been approved. Please coordinate with the claimant.',
        notification_type=Notification.NotificationType.CLAIM_APPROVED,
        related_item=item,
        related_claim=claim,
    )

    return True, 'Claim approved successfully.'


@transaction.atomic
def reject_claim(claim, admin_user, remarks=''):
    """Reject a specific claim with optional admin remarks."""
    claim = Claim.objects.select_for_update().get(pk=claim.pk)

    if claim.status != Claim.Status.PENDING:
        return False, 'This claim is no longer pending.'

    claim.status = Claim.Status.REJECTED
    claim.admin_remarks = remarks
    claim.reviewed_by = admin_user
    claim.reviewed_at = timezone.now()
    claim.save(update_fields=['status', 'admin_remarks', 'reviewed_by', 'reviewed_at', 'updated_at'])

    create_notification(
        user=claim.claimant,
        message=f'Your claim for "{claim.item.name}" was rejected. {f"Reason: {remarks}" if remarks else ""}',
        notification_type=Notification.NotificationType.CLAIM_REJECTED,
        related_item=claim.item,
        related_claim=claim,
    )
    return True, 'Claim rejected.'


@transaction.atomic
def mark_item_returned(item, admin_user, remarks=''):
    """Mark an item as returned (final state after handover)."""
    item = Item.objects.select_for_update().get(pk=item.pk)
    old_status = item.status
    item.status = Item.Status.RETURNED
    item.save(update_fields=['status', 'updated_at'])

    ItemStatusHistory.objects.create(
        item=item,
        changed_by=admin_user,
        old_status=old_status,
        new_status=item.status,
        remarks=remarks or 'Item marked as returned by admin.',
    )

    # Notify the reporter
    create_notification(
        user=item.user,
        message=f'The item "{item.name}" has been marked as successfully returned.',
        notification_type=Notification.NotificationType.ITEM_RETURNED,
        related_item=item,
    )

    # Notify approved claimant if any
    approved_claim = Claim.objects.filter(item=item, status=Claim.Status.APPROVED).first()
    if approved_claim and approved_claim.claimant != item.user:
        create_notification(
            user=approved_claim.claimant,
            message=f'The item "{item.name}" has been officially marked as returned to you.',
            notification_type=Notification.NotificationType.ITEM_RETURNED,
            related_item=item,
            related_claim=approved_claim,
        )

    return True
