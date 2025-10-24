import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q, Sum
from django.utils import timezone

from .models import (FeeStructure, FinancialReport, Fine, FinePayment, Invoice,
                     Payment, StudentFee, Transaction)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_payment_confirmation(self, payment_id):
    """Send payment confirmation email to student"""
    try:
        payment = Payment.objects.get(id=payment_id)

        # Prepare email content
        subject = f"Payment Confirmation - Receipt #{payment.receipt_number}"
        message = f"""
        Dear {payment.student_fee.student_name},
        
        Your payment has been successfully processed.
        
        Payment Details:
        - Receipt Number: {payment.receipt_number}
        - Amount: {payment.currency} {payment.amount}
        - Payment Method: {payment.get_payment_method_display()}
        - Payment Date: {payment.payment_date.strftime('%Y-%m-%d %H:%M:%S')}
        - Fee Type: {payment.student_fee.fee_structure.get_fee_type_display()}
        
        Thank you for your payment.
        
        Best regards,
        Finance Department
        """

        # Send via Notification Service
        notification_data = {
            "recipient_id": payment.student_fee.student_id,
            "recipient_email": payment.student_fee.student_email,
            "notification_type": "PAYMENT_CONFIRMATION",
            "title": subject,
            "message": message,
            "priority": "MEDIUM",
            "send_email": True,
            "metadata": {
                "payment_id": str(payment.id),
                "receipt_number": payment.receipt_number,
                "amount": str(payment.amount),
            },
        }

        # Call Notification Service API
        try:
            response = requests.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
                json=notification_data,
                timeout=30,
            )
            if response.status_code == 201:
                logger.info(f"Payment confirmation sent for payment {payment_id}")
            else:
                logger.error(f"Failed to send notification: {response.text}")
        except requests.RequestException as e:
            logger.error(f"Notification service error: {str(e)}")
            # Fallback to direct email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[payment.student_fee.student_email],
                fail_silently=False,
            )

        return f"Payment confirmation sent for payment {payment_id}"

    except Payment.DoesNotExist:
        logger.error(f"Payment {payment_id} not found")
        return f"Payment {payment_id} not found"
    except Exception as e:
        logger.error(f"Error sending payment confirmation: {str(e)}")
        raise self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def send_payment_reminder(self, student_fee_id):
    """Send payment reminder to student"""
    try:
        student_fee = StudentFee.objects.get(id=student_fee_id)

        if student_fee.status in ["PAID", "WAIVED", "CANCELLED"]:
            return f"No reminder needed for student fee {student_fee_id} - status: {student_fee.status}"

        # Calculate days overdue
        days_overdue = (timezone.now().date() - student_fee.due_date).days

        subject = f"Payment Reminder - {student_fee.fee_structure.name}"
        if days_overdue > 0:
            subject = f"Overdue Payment - {student_fee.fee_structure.name}"

        message = f"""
        Dear {student_fee.student_name},
        
        This is a reminder regarding your pending fee payment.
        
        Fee Details:
        - Fee Type: {student_fee.fee_structure.get_fee_type_display()}
        - Fee Name: {student_fee.fee_structure.name}
        - Amount Due: {student_fee.fee_structure.currency} {student_fee.balance_amount}
        - Due Date: {student_fee.due_date.strftime('%Y-%m-%d')}
        - Status: {student_fee.get_status_display()}
        
        {f"This payment is {days_overdue} days overdue." if days_overdue > 0 else "Please make the payment by the due date."}
        
        Please contact the finance department if you have any questions.
        
        Best regards,
        Finance Department
        """

        # Send via Notification Service
        notification_data = {
            "recipient_id": student_fee.student_id,
            "recipient_email": student_fee.student_email,
            "notification_type": "PAYMENT_REMINDER",
            "title": subject,
            "message": message,
            "priority": "HIGH" if days_overdue > 0 else "MEDIUM",
            "send_email": True,
            "metadata": {
                "student_fee_id": str(student_fee.id),
                "amount_due": str(student_fee.balance_amount),
                "days_overdue": days_overdue,
            },
        }

        # Call Notification Service API
        try:
            response = requests.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
                json=notification_data,
                timeout=30,
            )
            if response.status_code == 201:
                logger.info(f"Payment reminder sent for student fee {student_fee_id}")
            else:
                logger.error(f"Failed to send notification: {response.text}")
        except requests.RequestException as e:
            logger.error(f"Notification service error: {str(e)}")
            # Fallback to direct email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student_fee.student_email],
                fail_silently=False,
            )

        return f"Payment reminder sent for student fee {student_fee_id}"

    except StudentFee.DoesNotExist:
        logger.error(f"Student fee {student_fee_id} not found")
        return f"Student fee {student_fee_id} not found"
    except Exception as e:
        logger.error(f"Error sending payment reminder: {str(e)}")
        raise self.retry(countdown=60, exc=e)


@shared_task
def process_overdue_payments():
    """Process overdue payments and apply late fees"""
    try:
        today = timezone.now().date()

        # Find overdue student fees
        overdue_fees = StudentFee.objects.filter(
            due_date__lt=today,
            status__in=["PENDING", "PARTIALLY_PAID"],
            is_overdue=False,
        )

        processed_count = 0
        for student_fee in overdue_fees:
            # Mark as overdue
            student_fee.is_overdue = True
            student_fee.status = "OVERDUE"

            # Apply late fee if applicable
            if student_fee.fee_structure.late_fee_applicable:
                late_fee_amount = Decimal("0.00")

                if student_fee.fee_structure.late_fee_amount > 0:
                    late_fee_amount = student_fee.fee_structure.late_fee_amount
                elif student_fee.fee_structure.late_fee_percentage > 0:
                    late_fee_amount = (
                        student_fee.original_amount
                        * student_fee.fee_structure.late_fee_percentage
                        / 100
                    )

                if late_fee_amount > 0:
                    student_fee.late_fee_amount = late_fee_amount
                    student_fee.final_amount += late_fee_amount
                    student_fee.balance_amount += late_fee_amount

            student_fee.save()

            # Send overdue notification
            send_payment_reminder.delay(student_fee.id)

            # Create transaction record
            Transaction.objects.create(
                transaction_type="ADJUSTMENT",
                amount=student_fee.late_fee_amount,
                description=f"Late fee applied for {student_fee.fee_structure.name}",
                student_id=student_fee.student_id,
                student_name=student_fee.student_name,
                reference_type="student_fee",
                reference_id=str(student_fee.id),
                status="COMPLETED",
                processed_at=timezone.now(),
                notes="Automatic late fee application",
            )

            processed_count += 1

        logger.info(f"Processed {processed_count} overdue payments")
        return f"Processed {processed_count} overdue payments"

    except Exception as e:
        logger.error(f"Error processing overdue payments: {str(e)}")
        raise


@shared_task
def send_payment_reminders():
    """Send payment reminders for upcoming and overdue fees"""
    try:
        today = timezone.now().date()
        reminder_date = today + timedelta(days=7)  # Remind 7 days before due date

        # Find fees due in 7 days
        upcoming_fees = StudentFee.objects.filter(
            due_date=reminder_date, status__in=["PENDING", "PARTIALLY_PAID"]
        )

        # Find overdue fees
        overdue_fees = StudentFee.objects.filter(
            due_date__lt=today,
            status__in=["OVERDUE", "PARTIALLY_PAID"],
            is_overdue=True,
        )

        reminder_count = 0

        # Send reminders for upcoming fees
        for student_fee in upcoming_fees:
            send_payment_reminder.delay(student_fee.id)
            reminder_count += 1

        # Send reminders for overdue fees (weekly)
        for student_fee in overdue_fees:
            days_overdue = (today - student_fee.due_date).days
            if days_overdue % 7 == 0:  # Send weekly reminders
                send_payment_reminder.delay(student_fee.id)
                reminder_count += 1

        logger.info(f"Sent {reminder_count} payment reminders")
        return f"Sent {reminder_count} payment reminders"

    except Exception as e:
        logger.error(f"Error sending payment reminders: {str(e)}")
        raise


@shared_task(bind=True, max_retries=3)
def generate_invoice_task(self, invoice_id, send_email=False):
    """Generate invoice PDF and optionally send via email"""
    try:
        invoice = Invoice.objects.get(id=invoice_id)

        # Generate PDF (this would use a PDF generation library like ReportLab)
        # For now, we'll just log the action
        logger.info(f"Generated PDF for invoice {invoice.invoice_number}")

        if send_email:
            subject = f"Invoice {invoice.invoice_number}"
            message = f"""
            Dear {invoice.student_name},
            
            Please find attached your invoice.
            
            Invoice Details:
            - Invoice Number: {invoice.invoice_number}
            - Invoice Date: {invoice.invoice_date}
            - Due Date: {invoice.due_date}
            - Total Amount: {invoice.total_amount}
            - Balance Due: {invoice.balance_amount}
            
            Please make the payment by the due date.
            
            Best regards,
            Finance Department
            """

            # Send via Notification Service
            notification_data = {
                "recipient_id": invoice.student_id,
                "recipient_email": invoice.student_email,
                "notification_type": "INVOICE",
                "title": subject,
                "message": message,
                "priority": "MEDIUM",
                "send_email": True,
                "metadata": {
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "total_amount": str(invoice.total_amount),
                },
            }

            try:
                response = requests.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
                    json=notification_data,
                    timeout=30,
                )
                if response.status_code == 201:
                    logger.info(f"Invoice {invoice.invoice_number} sent via email")
                else:
                    logger.error(
                        f"Failed to send invoice notification: {response.text}"
                    )
            except requests.RequestException as e:
                logger.error(f"Notification service error: {str(e)}")

        return f"Invoice {invoice.invoice_number} processed successfully"

    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found")
        return f"Invoice {invoice_id} not found"
    except Exception as e:
        logger.error(f"Error generating invoice: {str(e)}")
        raise self.retry(countdown=60, exc=e)


@shared_task
def generate_financial_reports():
    """Generate periodic financial reports"""
    try:
        today = timezone.now().date()

        # Generate monthly report
        start_of_month = today.replace(day=1)
        end_of_month = today

        # Calculate collections for the month
        monthly_collections = Payment.objects.filter(
            payment_date__date__range=[start_of_month, end_of_month], status="SUCCESS"
        ).aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")

        # Calculate outstanding amounts
        total_outstanding = StudentFee.objects.filter(balance_amount__gt=0).aggregate(
            Sum("balance_amount")
        )["balance_amount__sum"] or Decimal("0.00")

        # Calculate fine collections
        fine_collections = FinePayment.objects.filter(
            payment_date__date__range=[start_of_month, end_of_month], status="SUCCESS"
        ).aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")

        # Create monthly report
        report = FinancialReport.objects.create(
            report_type="MONTHLY",
            title=f'Monthly Financial Report - {today.strftime("%B %Y")}',
            start_date=start_of_month,
            end_date=end_of_month,
            total_collections=monthly_collections,
            total_outstanding=total_outstanding,
            total_fines=fine_collections,
            generated_by="system",
            report_data={
                "fee_collections": float(monthly_collections),
                "fine_collections": float(fine_collections),
                "outstanding_fees": float(total_outstanding),
                "collection_rate": float(
                    (monthly_collections / (monthly_collections + total_outstanding))
                    * 100
                )
                if (monthly_collections + total_outstanding) > 0
                else 0,
                "generated_date": today.isoformat(),
            },
        )

        logger.info(f"Generated monthly financial report: {report.title}")
        return f"Generated monthly financial report: {report.title}"

    except Exception as e:
        logger.error(f"Error generating financial reports: {str(e)}")
        raise


@shared_task
def cleanup_expired_transactions():
    """Clean up old transaction records and expired payment attempts"""
    try:
        # Delete old failed payment attempts (older than 30 days)
        cutoff_date = timezone.now() - timedelta(days=30)

        expired_payments = Payment.objects.filter(
            payment_date__lt=cutoff_date, status__in=["FAILED", "CANCELLED"]
        )

        deleted_count = expired_payments.count()
        expired_payments.delete()

        # Archive old completed transactions (older than 1 year)
        archive_date = timezone.now() - timedelta(days=365)

        old_transactions = Transaction.objects.filter(
            transaction_date__lt=archive_date, status="COMPLETED"
        )

        archived_count = old_transactions.count()
        # In a real implementation, you might move these to an archive table
        # For now, we'll just log the count

        logger.info(
            f"Cleaned up {deleted_count} expired payments, {archived_count} transactions ready for archiving"
        )
        return f"Cleaned up {deleted_count} expired payments, {archived_count} transactions ready for archiving"

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise


@shared_task
def sync_payment_gateway_status():
    """Sync payment status with payment gateways"""
    try:
        # Find pending payments that need status update
        pending_payments = Payment.objects.filter(
            status="PENDING",
            payment_date__gte=timezone.now()
            - timedelta(hours=24),  # Only check recent payments
        )

        updated_count = 0

        for payment in pending_payments:
            if payment.gateway_transaction_id:
                # This would integrate with actual payment gateway APIs
                # For now, simulate status check

                # Mock gateway response
                gateway_status = "SUCCESS"  # This would come from actual gateway API

                if gateway_status == "SUCCESS":
                    payment.status = "SUCCESS"
                    payment.processed_at = timezone.now()
                    payment.save()

                    # Update student fee
                    student_fee = payment.student_fee
                    student_fee.paid_amount += payment.amount
                    student_fee.payment_count += 1
                    student_fee.last_payment_date = payment.payment_date
                    student_fee.save()

                    # Send confirmation
                    send_payment_confirmation.delay(payment.id)

                    updated_count += 1

                elif gateway_status == "FAILED":
                    payment.status = "FAILED"
                    payment.save()
                    updated_count += 1

        logger.info(f"Updated status for {updated_count} payments")
        return f"Updated status for {updated_count} payments"

    except Exception as e:
        logger.error(f"Error syncing payment gateway status: {str(e)}")
        raise


@shared_task(bind=True, max_retries=3)
def process_payment_gateway_callback(self, payment_data):
    """Process payment gateway callback/webhook"""
    try:
        gateway_transaction_id = payment_data.get("gateway_transaction_id")
        gateway_status = payment_data.get("status")

        if not gateway_transaction_id:
            logger.error("No gateway transaction ID in callback data")
            return "No gateway transaction ID provided"

        try:
            payment = Payment.objects.get(gateway_transaction_id=gateway_transaction_id)
        except Payment.DoesNotExist:
            logger.error(
                f"Payment not found for transaction ID: {gateway_transaction_id}"
            )
            return f"Payment not found for transaction ID: {gateway_transaction_id}"

        # Update payment status based on gateway response
        if gateway_status == "SUCCESS":
            payment.status = "SUCCESS"
            payment.processed_at = timezone.now()
            payment.gateway_response = payment_data
            payment.save()

            # Update student fee
            student_fee = payment.student_fee
            student_fee.paid_amount += payment.amount
            student_fee.payment_count += 1
            student_fee.last_payment_date = payment.payment_date
            student_fee.save()

            # Create transaction record
            Transaction.objects.create(
                transaction_type="FEE_PAYMENT",
                amount=payment.amount,
                description=f"Payment for {student_fee.fee_structure.name}",
                student_id=student_fee.student_id,
                student_name=student_fee.student_name,
                reference_type="student_fee",
                reference_id=str(student_fee.id),
                payment_id=str(payment.id),
                status="COMPLETED",
                processed_at=timezone.now(),
            )

            # Send confirmation
            send_payment_confirmation.delay(payment.id)

            logger.info(f"Payment {payment.id} processed successfully")
            return f"Payment {payment.id} processed successfully"

        elif gateway_status == "FAILED":
            payment.status = "FAILED"
            payment.gateway_response = payment_data
            payment.save()

            logger.info(f"Payment {payment.id} marked as failed")
            return f"Payment {payment.id} marked as failed"

        else:
            logger.warning(f"Unknown gateway status: {gateway_status}")
            return f"Unknown gateway status: {gateway_status}"

    except Exception as e:
        logger.error(f"Error processing payment callback: {str(e)}")
        raise self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def sync_user_data(self, user_data):
    """Sync user data from User Management Service"""
    try:
        user_id = user_data.get("user_id")
        user_name = user_data.get("name")
        user_email = user_data.get("email")

        if not user_id:
            logger.error("No user ID in sync data")
            return "No user ID provided"

        # Update student fees
        updated_fees = StudentFee.objects.filter(student_id=user_id).update(
            student_name=user_name, student_email=user_email
        )

        # Update fines
        updated_fines = Fine.objects.filter(student_id=user_id).update(
            student_name=user_name, student_email=user_email
        )

        # Update transactions
        updated_transactions = Transaction.objects.filter(student_id=user_id).update(
            student_name=user_name
        )

        # Update invoices
        updated_invoices = Invoice.objects.filter(student_id=user_id).update(
            student_name=user_name, student_email=user_email
        )

        logger.info(
            f"Synced user data for {user_id}: {updated_fees} fees, {updated_fines} fines, {updated_transactions} transactions, {updated_invoices} invoices"
        )
        return f"Synced user data for {user_id}"

    except Exception as e:
        logger.error(f"Error syncing user data: {str(e)}")
        raise self.retry(countdown=60, exc=e)


@shared_task
def generate_fee_collection_analytics():
    """Generate fee collection analytics and insights"""
    try:
        today = timezone.now().date()

        # Calculate various analytics
        analytics_data = {
            "total_fees_generated": float(
                StudentFee.objects.aggregate(Sum("final_amount"))["final_amount__sum"]
                or 0
            ),
            "total_collected": float(
                StudentFee.objects.aggregate(Sum("paid_amount"))["paid_amount__sum"]
                or 0
            ),
            "total_outstanding": float(
                StudentFee.objects.aggregate(Sum("balance_amount"))[
                    "balance_amount__sum"
                ]
                or 0
            ),
            "overdue_amount": float(
                StudentFee.objects.filter(is_overdue=True).aggregate(
                    Sum("balance_amount")
                )["balance_amount__sum"]
                or 0
            ),
            "collection_efficiency": 0,
            "generated_date": today.isoformat(),
        }

        # Calculate collection efficiency
        if analytics_data["total_fees_generated"] > 0:
            analytics_data["collection_efficiency"] = (
                analytics_data["total_collected"]
                / analytics_data["total_fees_generated"]
            ) * 100

        # Store analytics (you might want to create an Analytics model)
        logger.info(f"Generated fee collection analytics: {analytics_data}")
        return f"Generated fee collection analytics"

    except Exception as e:
        logger.error(f"Error generating analytics: {str(e)}")
        raise
