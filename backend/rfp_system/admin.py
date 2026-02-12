from django.contrib import admin
from .models import Document, DocumentChunk, RFP, Question, Answer, TaskStatus


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'file_type', 'processing_status', 'chunk_count', 'uploaded_at')
    list_filter = ('file_type', 'processing_status', 'processed')
    search_fields = ('filename',)
    readonly_fields = ('id', 'uploaded_at', 'chunk_count')


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('chromadb_id', 'document', 'chunk_index', 'created_at')
    list_filter = ('document',)
    search_fields = ('content', 'chromadb_id')
    readonly_fields = ('id', 'created_at')


@admin.register(RFP)
class RFPAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'uploaded_at')
    list_filter = ('status',)
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'uploaded_at')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_number', 'rfp', 'question_text_preview', 'created_at')
    list_filter = ('rfp',)
    search_fields = ('question_text', 'context')
    readonly_fields = ('id', 'created_at')

    def question_text_preview(self, obj):
        return obj.question_text[:100] + '...' if len(obj.question_text) > 100 else obj.question_text
    question_text_preview.short_description = 'Question'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question_preview', 'confidence_score', 'regenerated_count', 'cached', 'generated_at')
    list_filter = ('cached', 'generated_at')
    search_fields = ('answer_text', 'question__question_text')
    readonly_fields = ('id', 'generated_at')
    filter_horizontal = ('source_chunks',)

    def question_preview(self, obj):
        return str(obj.question)[:50] + '...'
    question_preview.short_description = 'Question'


@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'task_type', 'status', 'progress', 'created_at', 'completed_at')
    list_filter = ('task_type', 'status', 'created_at')
    search_fields = ('task_id', 'current_step', 'error')
    readonly_fields = ('id', 'task_id', 'created_at', 'started_at', 'completed_at')
    fieldsets = (
        ('Task Information', {
            'fields': ('id', 'task_id', 'task_type', 'status')
        }),
        ('Related Objects', {
            'fields': ('document', 'rfp')
        }),
        ('Progress', {
            'fields': ('progress', 'current_step', 'total_steps')
        }),
        ('Results', {
            'fields': ('result', 'error', 'traceback')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )
