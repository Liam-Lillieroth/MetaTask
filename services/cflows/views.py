from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    """CFlows homepage"""
    return HttpResponse("CFlows - Workflow Management System (To be implemented)")


def workflows_list(request):
    """List workflows"""
    return HttpResponse("Workflows list - To be implemented")


def create_workflow(request):
    """Create new workflow"""
    return HttpResponse("Create workflow - To be implemented")


def workflow_detail(request, pk):
    """Workflow detail view"""
    return HttpResponse(f"Workflow detail for {pk} - To be implemented")
