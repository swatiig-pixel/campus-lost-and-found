from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .forms import StudentRegistrationForm, StudentLoginForm, StudentProfileForm


def register_view(request):
    """Student registration view."""
    if request.user.is_authenticated:
        return redirect('dashboard:student_dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.full_name or user.username}! Your account has been created.')
            return redirect('dashboard:student_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Login view — routes students to student dashboard, admins to admin dashboard."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.full_name or user.username}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return _redirect_by_role(user)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = StudentLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logout and redirect to landing page."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing')


@login_required
def profile_view(request):
    """View and edit student profile."""
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


def _redirect_by_role(user):
    """Route user to their appropriate dashboard."""
    if user.is_admin_user:
        return redirect('dashboard:admin_dashboard')
    return redirect('dashboard:student_dashboard')
