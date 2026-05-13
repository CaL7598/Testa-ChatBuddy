"""
Smart Recommendation Engine for Testa studyBuddy
"""
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Q
from .models import (
    Recommendation, TopicMastery, QuestionAnswer, 
    Quiz, QuizAttempt, Flashcard, PDFDocument, UserAnalytics
)


class RecommendationEngine:
    """Generate personalized recommendations for users"""
    
    def __init__(self, user):
        self.user = user
    
    def generate_recommendations(self, limit=10):
        """Generate all types of recommendations"""
        recommendations = []
        
        # Weak topics
        recommendations.extend(self._recommend_weak_topics())
        
        # Quiz recommendations
        recommendations.extend(self._recommend_quizzes())
        
        # Flashcard reviews
        recommendations.extend(self._recommend_flashcard_review())
        
        # Document suggestions
        recommendations.extend(self._recommend_documents())
        
        # Next topics
        recommendations.extend(self._recommend_next_topics())
        
        # Sort by priority and return top recommendations
        recommendations.sort(key=lambda x: x.priority, reverse=True)
        return recommendations[:limit]
    
    def get_daily_focus(self):
        """Get the highest priority recommendation for daily focus"""
        recommendations = self.generate_recommendations(limit=1)
        if recommendations:
            return recommendations[0]
        return None
    
    def _recommend_weak_topics(self, priority=90):
        """Recommend topics with mastery < 60%"""
        weak_topics = TopicMastery.objects.filter(
            user=self.user,
            mastery_level__lt=60.0
        ).order_by('mastery_level', '-last_practiced')[:3]
        
        recommendations = []
        for topic in weak_topics:
            recommendations.append(
                Recommendation(
                    user=self.user,
                    recommendation_type='weak_area',
                    title=f"Improve {topic.topic}",
                    description=f"Your mastery level in {topic.course} - {topic.topic} is {topic.mastery_level:.1f}%. Consider practicing more.",
                    related_course=topic.course,
                    related_topic=topic.topic,
                    priority=priority
                )
            )
        return recommendations
    
    def _recommend_quizzes(self, priority=70):
        """Recommend quizzes for topics studied but not tested"""
        # Get topics with questions but no quiz attempts
        studied_topics = QuestionAnswer.objects.filter(
            user=self.user
        ).values('course', 'topic').distinct()
        
        recommendations = []
        for topic_data in studied_topics[:3]:
            course = topic_data['course']
            topic = topic_data['topic']
            
            # Check if user has taken quiz for this topic
            has_quiz = QuizAttempt.objects.filter(
                user=self.user,
                quiz__course=course,
                quiz__topic=topic
            ).exists()
            
            if not has_quiz and course and topic:
                recommendations.append(
                    Recommendation(
                        user=self.user,
                        recommendation_type='quiz',
                        title=f"Take Quiz: {topic}",
                        description=f"Test your knowledge of {topic} in {course} with a quiz.",
                        related_course=course,
                        related_topic=topic,
                        priority=priority
                    )
                )
        return recommendations
    
    def _recommend_flashcard_review(self, priority=60):
        """Recommend flashcards due for review (spaced repetition)"""
        # Find flashcards with low confidence or not reviewed recently
        due_flashcards = Flashcard.objects.filter(
            user=self.user
        ).filter(
            Q(confidence_level__lt=2) | 
            Q(last_reviewed__isnull=True) |
            Q(last_reviewed__lt=datetime.now() - timedelta(days=7))
        ).order_by('confidence_level', 'last_reviewed')[:3]
        
        recommendations = []
        for flashcard in due_flashcards:
            recommendations.append(
                Recommendation(
                    user=self.user,
                    recommendation_type='flashcard',
                    title=f"Review: {flashcard.front[:50]}",
                    description=f"Review this flashcard for {flashcard.course} - {flashcard.topic}.",
                    related_course=flashcard.course,
                    related_topic=flashcard.topic,
                    priority=priority
                )
            )
        return recommendations
    
    def _recommend_documents(self, priority=50):
        """Recommend unread documents"""
        # Get documents not uploaded by user
        read_documents = QuestionAnswer.objects.filter(
            user=self.user
        ).exclude(source_document__isnull=True).values_list(
            'source_document_id', flat=True
        ).distinct()
        
        recommendations = []
        unread_docs = PDFDocument.objects.exclude(
            id__in=read_documents
        ).order_by('-uploaded_at')[:3]
        
        for doc in unread_docs:
            recommendations.append(
                Recommendation(
                    user=self.user,
                    recommendation_type='document',
                    title=f"Read: {doc.title or doc.file.name}",
                    description=f"New document available for {doc.course or 'study'}.",
                    related_course=doc.course,
                    priority=priority
                )
            )
        return recommendations
    
    def _recommend_next_topics(self, priority=60):
        """Recommend next topics based on learning path"""
        # Get user's favorite course
        try:
            analytics = UserAnalytics.objects.get(user=self.user)
            favorite_course = analytics.favorite_course
        except UserAnalytics.DoesNotExist:
            favorite_course = None
        
        if not favorite_course:
            # Get most studied course
            most_studied = QuestionAnswer.objects.filter(
                user=self.user
            ).exclude(course='').values('course').annotate(
                count=Count('id')
            ).order_by('-count').first()
            
            if most_studied:
                favorite_course = most_studied['course']
        
        if favorite_course:
            # Get topics in this course not yet mastered
            studied_topics = TopicMastery.objects.filter(
                user=self.user,
                course=favorite_course
            ).values_list('topic', flat=True)
            
            all_topics = QuestionAnswer.objects.filter(
                course=favorite_course
            ).exclude(topic='').values('topic').distinct()
            
            next_topics = [t['topic'] for t in all_topics if t['topic'] not in studied_topics][:3]
            
            recommendations = []
            for topic in next_topics:
                recommendations.append(
                    Recommendation(
                        user=self.user,
                        recommendation_type='topic',
                        title=f"Explore: {topic}",
                        description=f"Continue learning {topic} in {favorite_course}.",
                        related_course=favorite_course,
                        related_topic=topic,
                        priority=priority
                    )
                )
            return recommendations
        
        return []
    
    def save_recommendations(self):
        """Save generated recommendations to database"""
        # Delete old incomplete recommendations
        Recommendation.objects.filter(
            user=self.user,
            is_completed=False
        ).delete()
        
        # Generate and save new recommendations
        recommendations = self.generate_recommendations(limit=20)
        for rec in recommendations:
            rec.save()
