from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Fine, FinePayment, Payment, StudentFee, Transaction
from .tasks import send_payment_confirmation, send_payment_reminder


@receiver(post_save, sender=StudentFee)
def student_fee_created(sender, instance, created, **kwargs):
    """Handle student fee creation"""
    if created:
        # Send notification about new fee assignment
        from .tasks import send_payment_reminder

        send_payment_reminder.delay(instance.id)

        # Create transaction record
        Transaction.objects.create(
            transaction_type="FEE_PAYMENT",
            amount=instance.final_amount,
            description=f"Fee assigned: {instance.fee_structure.name}",
            student_id=instance.student_id,
            student_name=instance.student_name,
            reference_type="student_fee",
            reference_id=str(instance.id),
            status="PENDING",
        )


@receiver(pre_save, sender=StudentFee)
def student_fee_status_changed(sender, instance, **kwargs):
    """Handle student fee status changes"""
    if instance.pk:
        try:
            old_instance = StudentFee.objects.get(pk=instance.pk)

            # Check if status changed to PAID
            if old_instance.status != "PAID" and instance.status == "PAID":
                # Update transaction status
                Transaction.objects.filter(
                    reference_type="student_fee",
                    reference_id=str(instance.id),
                    transaction_type="FEE_PAYMENT",
                ).update(status="COMPLETED", processed_at=timezone.now())

            # Check if fee became overdue
            if not old_instance.is_overdue and instance.is_overdue:
                # Send overdue notification
                send_payment_reminder.delay(instance.id)

        except StudentFee.DoesNotExist:
            pass


@receiver(post_save, sender=Payment)
def payment_created(sender, instance, created, **kwargs):
    """Handle payment creation"""
    if created:
        # Create transaction record
        Transaction.objects.create(
            transaction_type="FEE_PAYMENT",
            amount=instance.amount,
            description=f"Payment for {instance.student_fee.fee_structure.name}",
            student_id=instance.student_fee.student_id,
            student_name=instance.student_fee.student_name,
            reference_type="payment",
            reference_id=str(instance.id),
            payment_id=str(instance.id),
            status="PENDING",
        )


@receiver(pre_save, sender=Payment)
def payment_status_changed(sender, instance, **kwargs):
    """Handle payment status changes"""
    if instance.pk:
        try:
            old_instance = Payment.objects.get(pk=instance.pk)

            # Check if payment status changed to SUCCESS
            if old_instance.status != "SUCCESS" and instance.status == "SUCCESS":
                # Send payment confirmation
                send_payment_confirmation.delay(instance.id)

                # Update related transaction
                Transaction.objects.filter(payment_id=str(instance.id)).update(
                    status="COMPLETED", processed_at=timezone.now()
                )

            # Check if payment failed
            elif old_instance.status != "FAILED" and instance.status == "FAILED":
                # Update related transaction
                Transaction.objects.filter(payment_id=str(instance.id)).update(
                    status="FAILED", processed_at=timezone.now()
                )

        except Payment.DoesNotExist:
            pass


@receiver(post_save, sender=Fine)
def fine_created(sender, instance, created, **kwargs):
    """Handle fine creation"""
    if created:
        # Create transaction record
        Transaction.objects.create(
            transaction_type="FINE_PAYMENT",
            amount=instance.amount,
            description=f"Fine issued: {instance.title}",
            student_id=instance.student_id,
            student_name=instance.student_name,
            reference_type="fine",
            reference_id=str(instance.id),
            status="PENDING",
        )

        # Send fine notification
        from .tasks import send_payment_reminder

        # You might want to create a specific fine notification task
        # For now, we'll use the payment reminder task


@receiver(pre_save, sender=Fine)
def fine_status_changed(sender, instance, **kwargs):
    """Handle fine status changes"""
    if instance.pk:
        try:
            old_instance = Fine.objects.get(pk=instance.pk)

            # Check if fine status changed to PAID
            if old_instance.status != "PAID" and instance.status == "PAID":
                # Update transaction status
                Transaction.objects.filter(
                    reference_type="fine",
                    reference_id=str(instance.id),
                    transaction_type="FINE_PAYMENT",
                ).update(status="COMPLETED", processed_at=timezone.now())

            # Check if fine was waived
            elif old_instance.status != "WAIVED" and instance.status == "WAIVED":
                # Create waiver transaction
                Transaction.objects.create(
                    transaction_type="ADJUSTMENT",
                    amount=instance.amount,
                    description=f"Fine waived: {instance.title}",
                    student_id=instance.student_id,
                    student_name=instance.student_name,
                    reference_type="fine",
                    reference_id=str(instance.id),
                    status="COMPLETED",
                    processed_at=timezone.now(),
                    notes=f"Waived by {instance.waived_by}. Reason: {instance.waiver_reason}",
                )

        except Fine.DoesNotExist:
            pass


@receiver(post_save, sender=FinePayment)
def fine_payment_created(sender, instance, created, **kwargs):
    """Handle fine payment creation"""
    if created:
        # Create transaction record
        Transaction.objects.create(
            transaction_type="FINE_PAYMENT",
            amount=instance.amount,
            description=f"Fine payment for {instance.fine.title}",
            student_id=instance.fine.student_id,
            student_name=instance.fine.student_name,
            reference_type="fine_payment",
            reference_id=str(instance.id),
            status="COMPLETED" if instance.status == "SUCCESS" else "PENDING",
            processed_at=timezone.now() if instance.status == "SUCCESS" else None,
        )
