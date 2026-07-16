from django.contrib import admin
from .models import Workflow, EtapeWorkflow


class EtapeWorkflowInline(admin.TabularInline):
    model = EtapeWorkflow
    extra = 0


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("nom", "service_associe")
    inlines = [EtapeWorkflowInline]
