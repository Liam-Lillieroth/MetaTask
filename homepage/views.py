from django.shortcuts import render, redirect
from django.http import JsonResponse


def index(request):
    """Homepage view - redirect logged in users to dashboard"""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    
    return render(request, 'homepage/index.html', {
        'title': 'MetaTask - Comprehensive Service Platform',
        'services': [
            {'name': 'CFlows', 'description': 'Workflow Management System'},
            {'name': 'Job Planning', 'description': 'Resource Allocation and Scheduling'},
        ]
    })


def services(request):
    """Services listing page"""
    return render(request, 'homepage/services.html', {
        'title': 'Available Services',
    })


def about(request):
    """About page"""
    return render(request, 'homepage/about.html', {
        'title': 'About MetaTask',
    })


def contact(request):
    """Contact page"""
    return render(request, 'homepage/contact.html', {
        'title': 'Contact Us',
    })


def privacy(request):
    """Privacy policy page"""
    return render(request, 'homepage/privacy.html', {
        'title': 'Privacy Policy',
    })


def terms(request):
    """Terms of service page"""
    return render(request, 'homepage/terms.html', {
        'title': 'Terms of Service',
    })
