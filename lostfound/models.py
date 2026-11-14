from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'lostfound_category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):

    class ReportType(models.TextChoices):
        LOST = 'LOST', 'Lost'
        FOUND = 'FOUND', 'Found'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CLAIMED = 'CLAIMED', 'Claimed'
        RETURNED = 'RETURNED', 'Returned'
        CLOSED = 'CLOSED', 'Closed'

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='items',
        db_index=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='items',
        db_index=True
    )
    name = models.CharField(max_length=150)
    description = models.TextField()
    report_type = models.CharField(
        max_length=5,
        choices=ReportType.choices,
        db_index=True
    )
    location = models.CharField(max_length=200)
    report_date = models.DateField()
    image = models.ImageField(upload_to='items/', blank=True, null=True)

    # Lifecycle status: what has happened to this item
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    # Verification status: has admin approved this listing?
    verification_status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lostfound_item'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'verification_status'], name='idx_item_type_vstatus'),
            models.Index(fields=['status'], name='idx_item_status'),
            models.Index(fields=['report_date'], name='idx_item_date'),
        ]

    def __str__(self):
        return f"[{self.report_type}] {self.name}"

    @property
    def is_visible(self):
        """Item is visible to other students only when approved."""
        return self.verification_status == self.VerificationStatus.APPROVED


class Claim(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='claims',
        db_index=True
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claims',
        db_index=True
    )
    description = models.TextField(help_text='Describe why this item belongs to you.')
    identifying_details = models.TextField(
        help_text='Provide unique details that prove ownership (serial number, contents, specific marks, etc.)'
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    admin_remarks = models.TextField(blank=True, help_text='Admin notes on this claim.')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claims'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lostfound_claim'
        ordering = ['-created_at']
        # Prevent duplicate pending claims by the same student for the same item
        constraints = [
            models.UniqueConstraint(
                fields=['item', 'claimant'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_claim_per_student_item'
            )
        ]
        indexes = [
            models.Index(fields=['status'], name='idx_claim_status'),
        ]

    def __str__(self):
        return f"Claim #{self.pk} for {self.item.name} by {self.claimant.username}"


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        db_index=True
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
        db_index=True
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True
    )
    message_text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lostfound_message'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'receiver'], name='idx_message_participants'),
            models.Index(fields=['item'], name='idx_message_item'),
        ]

    def __str__(self):
        return f"Msg from {self.sender.username} to {self.receiver.username} re: {self.item.name}"


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        CLAIM_SUBMITTED = 'CLAIM_SUBMITTED', 'Claim Submitted'
        CLAIM_APPROVED = 'CLAIM_APPROVED', 'Claim Approved'
        CLAIM_REJECTED = 'CLAIM_REJECTED', 'Claim Rejected'
        ITEM_APPROVED = 'ITEM_APPROVED', 'Item Approved'
        ITEM_REJECTED = 'ITEM_REJECTED', 'Item Rejected'
        ITEM_RETURNED = 'ITEM_RETURNED', 'Item Returned'
        MESSAGE_RECEIVED = 'MESSAGE_RECEIVED', 'Message Received'
        GENERAL = 'GENERAL', 'General'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL
    )
    related_item = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_claim = models.ForeignKey(
        Claim,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lostfound_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read'], name='idx_notification_user_read'),
        ]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"


class ItemStatusHistory(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    old_status = models.CharField(max_length=10)
    new_status = models.CharField(max_length=10)
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lostfound_itemstatushistory'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.item.name}: {self.old_status} → {self.new_status}"
