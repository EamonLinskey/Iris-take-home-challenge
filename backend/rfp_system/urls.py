"""
URL routing for RFP system API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet,
    RFPViewSet,
    QuestionViewSet,
    AnswerViewSet,
    SearchViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'rfps', RFPViewSet, basename='rfp')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'answers', AnswerViewSet, basename='answer')

# URL patterns
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Custom search endpoint
    path('search/', SearchViewSet.as_view({'post': 'search'}), name='search'),
]
