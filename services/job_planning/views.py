from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    """Job Planning homepage"""
    return HttpResponse("Job Planning - Resource Allocation and Scheduling (To be implemented)")


def projects_list(request):
    """List projects"""
    return HttpResponse("Projects list - To be implemented")


def create_project(request):
    """Create new project"""
    return HttpResponse("Create project - To be implemented")


def project_detail(request, pk):
    """Project detail view"""
    return HttpResponse(f"Project detail for {pk} - To be implemented")
