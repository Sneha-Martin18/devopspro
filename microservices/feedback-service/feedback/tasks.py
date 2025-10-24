import logging
from datetime import datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_feedback_notification(self, feedback_id, action, recipient_email):
    """Send feedback notification via notification service"""
    try:
        from .models import Feedback

        feedback = Feedback.objects.get(id=feedback_id)

        # Prepare notification data
        notification_data = {
            "recipient_email": recipient_email,
            "template_code": f"FEEDBACK_{action}",
            "context": {
                "user_name": feedback.user_name
                if not feedback.is_anonymous
                else "Anonymous User",
                "feedback_title": feedback.title,
                "category": feedback.category.name,
                "rating": feedback.rating,
                "status": feedback.get_status_display(),
                "feedback_id": str(feedback.id),
                "target_name": feedback.target_name or "General",
                "created_at": feedback.created_at.strftime("%Y-%m-%d %H:%M"),
            },
            "channels": ["email", "in_app"],
            "priority": "high"
            if action in ["APPROVED", "REJECTED", "RESPONSE_ADDED"]
            else "medium",
        }

        # Send to notification service
        if recipient_email:  # Only send if not anonymous
            response = requests.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
                json=notification_data,
                timeout=30,
            )

            if response.status_code == 201:
                logger.info(
                    f"Feedback notification sent successfully for {feedback_id}"
                )
            else:
                logger.error(f"Failed to send feedback notification: {response.text}")
                raise Exception(f"Notification service returned {response.status_code}")
        else:
            logger.info(f"Skipped notification for anonymous feedback {feedback_id}")

    except Exception as exc:
        logger.error(f"Error sending feedback notification: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2**self.request.retries), exc=exc)
        raise


@shared_task
def process_pending_feedback():
    """Process pending feedback for auto-approval or escalation"""
    try:
        from .models import Feedback, FeedbackCategory

        # Auto-approve feedback for categories that don't require moderation
        auto_approve_categories = FeedbackCategory.objects.filter(
            requires_moderation=False, is_active=True
        )

        auto_approve_feedback = Feedback.objects.filter(
            status="SUBMITTED", category__in=auto_approve_categories
        )

        approved_count = 0
        for feedback in auto_approve_feedback:
            feedback.status = "APPROVED"
            feedback.moderator_id = "system"
            feedback.moderator_name = "Auto Approval System"
            feedback.moderated_at = timezone.now()
            feedback.save()

            # Send notification
            send_feedback_notification.delay(
                feedback.id,
                "APPROVED",
                feedback.user_email if not feedback.is_anonymous else None,
            )

            approved_count += 1

        # Escalate old pending feedback (older than 3 days)
        three_days_ago = timezone.now() - timedelta(days=3)
        old_pending = Feedback.objects.filter(
            status="SUBMITTED", created_at__lt=three_days_ago
        )

        escalated_count = 0
        for feedback in old_pending:
            feedback.priority = "HIGH"
            feedback.save()
            escalated_count += 1

            # Send escalation notification to moderators
            # This would integrate with user management to get moderator emails

        logger.info(
            f"Auto-approved {approved_count} feedback, escalated {escalated_count} old feedback"
        )

    except Exception as exc:
        logger.error(f"Error processing pending feedback: {str(exc)}")
        raise


@shared_task
def generate_feedback_reports():
    """Generate daily feedback reports and analytics"""
    try:
        from .models import Feedback, FeedbackAnalytics, FeedbackCategory

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Generate daily report
        daily_feedback = Feedback.objects.filter(created_at__date=yesterday)

        if daily_feedback.exists():
            # Calculate analytics
            total_feedback = daily_feedback.count()
            avg_rating = (
                daily_feedback.aggregate(avg_rating=Avg("rating"))["avg_rating"] or 0
            )

            # Sentiment distribution
            sentiment_dist = dict(
                daily_feedback.exclude(sentiment="")
                .values("sentiment")
                .annotate(count=Count("id"))
                .values_list("sentiment", "count")
            )

            # Category breakdown
            category_breakdown = dict(
                daily_feedback.values("category__name")
                .annotate(count=Count("id"))
                .values_list("category__name", "count")
            )

            # Rating distribution
            rating_dist = dict(
                daily_feedback.values("rating")
                .annotate(count=Count("id"))
                .values_list("rating", "count")
            )

            # Create analytics record
            analytics = FeedbackAnalytics.objects.create(
                report_type="DAILY",
                title=f"Daily Feedback Report - {yesterday}",
                start_date=yesterday,
                end_date=yesterday,
                total_feedback=total_feedback,
                average_rating=round(avg_rating, 2),
                sentiment_distribution=sentiment_dist,
                category_breakdown=category_breakdown,
                rating_distribution=rating_dist,
                generated_by="system",
            )

            logger.info(f"Generated daily feedback report for {yesterday}")

        # Generate weekly report on Mondays
        if today.weekday() == 0:  # Monday
            week_start = today - timedelta(days=7)
            week_end = today - timedelta(days=1)

            weekly_feedback = Feedback.objects.filter(
                created_at__date__range=[week_start, week_end]
            )

            if weekly_feedback.exists():
                # Similar analytics calculation for weekly
                total_feedback = weekly_feedback.count()
                avg_rating = (
                    weekly_feedback.aggregate(avg_rating=Avg("rating"))["avg_rating"]
                    or 0
                )

                analytics = FeedbackAnalytics.objects.create(
                    report_type="WEEKLY",
                    title=f"Weekly Feedback Report - {week_start} to {week_end}",
                    start_date=week_start,
                    end_date=week_end,
                    total_feedback=total_feedback,
                    average_rating=round(avg_rating, 2),
                    generated_by="system",
                )

                logger.info(
                    f"Generated weekly feedback report for {week_start} to {week_end}"
                )

    except Exception as exc:
        logger.error(f"Error generating feedback reports: {str(exc)}")
        raise


@shared_task
def cleanup_old_feedback():
    """Clean up old feedback data and logs"""
    try:
        from .models import Feedback, FeedbackAnalytics, FeedbackResponse

        # Delete draft feedback older than 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        old_drafts = Feedback.objects.filter(
            status="DRAFT", created_at__lt=thirty_days_ago
        )

        deleted_drafts = old_drafts.count()
        old_drafts.delete()

        # Archive old analytics (older than 1 year)
        one_year_ago = timezone.now() - timedelta(days=365)
        old_analytics = FeedbackAnalytics.objects.filter(generated_at__lt=one_year_ago)

        deleted_analytics = old_analytics.count()
        old_analytics.delete()

        logger.info(
            f"Cleaned up {deleted_drafts} old drafts and {deleted_analytics} old analytics"
        )

    except Exception as exc:
        logger.error(f"Error cleaning up old feedback data: {str(exc)}")
        raise


@shared_task
def process_feedback_analytics(
    report_type, start_date, end_date, categories, target_types, generated_by
):
    """Generate comprehensive feedback analytics report"""
    try:
        from .models import Feedback, FeedbackAnalytics, FeedbackResponse

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Base queryset
        feedback_qs = Feedback.objects.filter(
            created_at__date__range=[start_date, end_date]
        )

        # Apply filters
        if categories:
            feedback_qs = feedback_qs.filter(category__id__in=categories)

        if target_types:
            feedback_qs = feedback_qs.filter(target_type__in=target_types)

        # Calculate comprehensive analytics
        total_feedback = feedback_qs.count()

        if total_feedback == 0:
            logger.info("No feedback found for the specified criteria")
            return

        avg_rating = feedback_qs.aggregate(avg_rating=Avg("rating"))["avg_rating"] or 0

        # Sentiment distribution
        sentiment_dist = dict(
            feedback_qs.exclude(sentiment="")
            .values("sentiment")
            .annotate(count=Count("id"))
            .values_list("sentiment", "count")
        )

        # Category breakdown
        category_breakdown = dict(
            feedback_qs.values("category__name")
            .annotate(count=Count("id"), avg_rating=Avg("rating"))
            .values_list("category__name", "count")
        )

        # Rating distribution
        rating_dist = dict(
            feedback_qs.values("rating")
            .annotate(count=Count("id"))
            .values_list("rating", "count")
        )

        # Response rate calculation
        total_responses = FeedbackResponse.objects.filter(
            feedback__in=feedback_qs
        ).count()
        response_rate = (
            (total_responses / total_feedback * 100) if total_feedback > 0 else 0
        )

        # Generate insights
        insights = []

        # Rating insights
        if avg_rating >= 4:
            insights.append(
                "Overall satisfaction is high with average rating above 4.0"
            )
        elif avg_rating <= 2:
            insights.append(
                "Overall satisfaction is low with average rating below 2.0 - immediate attention needed"
            )

        # Sentiment insights
        if sentiment_dist.get("NEGATIVE", 0) > sentiment_dist.get("POSITIVE", 0):
            insights.append(
                "Negative sentiment dominates - review feedback for improvement areas"
            )

        # Response rate insights
        if response_rate < 50:
            insights.append(
                "Low response rate to feedback - consider improving response processes"
            )

        # Generate trends (simplified)
        trends = {
            "rating_trend": "stable",  # Would calculate actual trend
            "volume_trend": "increasing" if total_feedback > 100 else "stable",
            "sentiment_trend": "improving"
            if sentiment_dist.get("POSITIVE", 0) > sentiment_dist.get("NEGATIVE", 0)
            else "declining",
        }

        # Generate recommendations
        recommendations = []

        if avg_rating < 3:
            recommendations.append("Focus on addressing low-rated feedback categories")

        if response_rate < 70:
            recommendations.append("Improve feedback response time and quality")

        if sentiment_dist.get("NEGATIVE", 0) > total_feedback * 0.3:
            recommendations.append(
                "Implement action plans to address negative feedback trends"
            )

        # Create analytics record
        analytics = FeedbackAnalytics.objects.create(
            report_type=report_type,
            title=f"{report_type.title()} Feedback Analytics - {start_date} to {end_date}",
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            target_types=target_types,
            total_feedback=total_feedback,
            average_rating=round(avg_rating, 2),
            sentiment_distribution=sentiment_dist,
            category_breakdown=category_breakdown,
            rating_distribution=rating_dist,
            response_rate=round(response_rate, 2),
            insights=insights,
            trends=trends,
            recommendations=recommendations,
            generated_by=generated_by,
        )

        logger.info(f"Generated {report_type} analytics report: {analytics.id}")
        return str(analytics.id)

    except Exception as exc:
        logger.error(f"Error generating feedback analytics: {str(exc)}")
        raise


@shared_task
def send_survey_reminders():
    """Send reminders for active surveys"""
    try:
        from .models import FeedbackSurvey

        # Get active surveys
        active_surveys = FeedbackSurvey.objects.filter(
            status="ACTIVE",
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now(),
        )

        for survey in active_surveys:
            # Check if reminder is due
            days_since_start = (timezone.now().date() - survey.start_date.date()).days

            if (
                days_since_start % survey.reminder_frequency == 0
                and days_since_start > 0
            ):
                # Send reminder to participants who haven't responded
                # This would integrate with user management and notification services

                notification_data = {
                    "template_code": "SURVEY_REMINDER",
                    "context": {
                        "survey_title": survey.title,
                        "survey_description": survey.description,
                        "end_date": survey.end_date.strftime("%Y-%m-%d"),
                        "days_remaining": survey.days_remaining,
                    },
                    "channels": ["email", "in_app"],
                    "priority": "medium",
                }

                # Send to notification service for each participant
                # Implementation would depend on user management service

                logger.info(f"Sent reminders for survey: {survey.title}")

    except Exception as exc:
        logger.error(f"Error sending survey reminders: {str(exc)}")
        raise


@shared_task
def sync_user_data():
    """Sync user data from User Management Service"""
    try:
        from .models import Feedback

        # Get unique user IDs from feedback
        user_ids = (
            Feedback.objects.exclude(is_anonymous=True)
            .values_list("user_id", flat=True)
            .distinct()
        )

        # Fetch user data from User Management Service
        response = requests.post(
            f"{settings.USER_MANAGEMENT_SERVICE_URL}/api/v1/users/bulk_info/",
            json={"user_ids": list(user_ids)},
            timeout=30,
        )

        if response.status_code == 200:
            users_data = response.json()

            # Update feedback with latest user data
            for user_data in users_data:
                Feedback.objects.filter(user_id=user_data["id"]).update(
                    user_name=f"{user_data['first_name']} {user_data['last_name']}",
                    user_email=user_data["email"],
                )

            logger.info(f"Synced data for {len(users_data)} users")
        else:
            logger.error(f"Failed to sync user data: {response.text}")

    except Exception as exc:
        logger.error(f"Error syncing user data: {str(exc)}")
        raise


@shared_task
def analyze_feedback_sentiment():
    """Analyze sentiment of feedback using basic keyword analysis"""
    try:
        from .models import Feedback

        # Get feedback without sentiment analysis
        unanalyzed_feedback = Feedback.objects.filter(
            sentiment="", status__in=["SUBMITTED", "APPROVED"]
        )

        # Simple keyword-based sentiment analysis
        positive_keywords = [
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "love",
            "perfect",
        ]
        negative_keywords = [
            "bad",
            "terrible",
            "awful",
            "horrible",
            "hate",
            "worst",
            "disappointing",
            "poor",
        ]

        analyzed_count = 0
        for feedback in unanalyzed_feedback:
            text = f"{feedback.title} {feedback.description}".lower()

            positive_score = sum(1 for word in positive_keywords if word in text)
            negative_score = sum(1 for word in negative_keywords if word in text)

            if positive_score > negative_score:
                sentiment = "POSITIVE"
            elif negative_score > positive_score:
                sentiment = "NEGATIVE"
            else:
                sentiment = "NEUTRAL"

            feedback.sentiment = sentiment
            feedback.save()
            analyzed_count += 1

        logger.info(f"Analyzed sentiment for {analyzed_count} feedback entries")

    except Exception as exc:
        logger.error(f"Error analyzing feedback sentiment: {str(exc)}")
        raise
